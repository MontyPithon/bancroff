from flask import render_template, redirect, url_for, flash, request as flask_request, session, current_app
import subprocess
import os
from datetime import datetime
from models import db, User, RequestApproval, ApprovalStep, Request
from utils.auth_helpers import active_required

def setup_approval_routes(app):
    @app.route('/my_requests')
    @active_required
    def my_requests():
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        requests = current_user.requests
        return render_template('my_requests.html', requests=requests)

    @app.route('/pending_approvals')
    @active_required
    def pending_approvals():
        """View all forms regardless of their status"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        if current_user.role.name == 'basic_user':
            flash('You do not have an assigned role for approvals.', 'warning')
            return redirect(url_for('index'))
        
        # Get all requests with their approval statuses
        requests = Request.query.all()
        all_approvals = []
        
        for req in requests:
            # Get all approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == req.id
            ).order_by(ApprovalStep.step_order).all()
            
            # Find the current pending step or the latest step if none are pending
            current_step = next((a for a in request_approvals if a.status == 'pending'), 
                               request_approvals[-1] if request_approvals else None)
            
            # Include all requests, not just those with pending steps
            if current_step:
                all_approvals.append({
                    'approval_id': current_step.id,
                    'request': req,
                    'request_type': req.request_type.name,
                    'requester': req.requester.full_name,
                    'submitted': req.created_at,
                    'step': current_step.step.name,
                    'status': req.status,  # Include overall request status
                    'approval_status': [{
                        'step': a.step.name,
                        'status': a.status,
                        'approver': a.approver.full_name if a.approver else 'Pending'
                    } for a in request_approvals]
                })
        
        return render_template('pending_approvals.html', pending_approvals=all_approvals)

    @app.route('/request_approval/<int:approval_id>', methods=['GET', 'POST'])
    @active_required
    def request_approval(approval_id):
        """View and process approval for a specific request"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        approval = RequestApproval.query.get(approval_id)
        if not approval:
            flash('Approval request not found.', 'danger')
            return redirect(url_for('pending_approvals'))
        
        # Get the approver role for this step
        approver_role = approval.step.approver_role

        # Check if the current user's role matches the required approver role
        # Allow for role ID mismatch but matching role names (e.g., 'admin', 'dean')
        if current_user.role_id != approval.step.approver_role_id and current_user.role.name != 'admin':
            role_required = approver_role.name if approver_role else "Unknown"
            flash(f'You do not have permission to approve this request. Required role: {role_required}', 'danger')
            return redirect(url_for('pending_approvals'))
        
        if approval.status != 'pending':
            flash('This request has already been processed.', 'warning')
            return redirect(url_for('pending_approvals'))
        
        if flask_request.method == 'POST':
            action = flask_request.form.get('action')
            comments = flask_request.form.get('comments', '')
            
            if action == 'approve':
                approval.status = 'approved'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                
                db.session.commit()
                
                # Generate a PDF for this approval step
                pdf_path, error = generate_pdf_for_approval(approval.id)
                if error:
                    flash(f"PDF generation error: {error}", "danger")
                else:
                    flash("PDF generated successfully!", "success")
                
                # Check if this was the last approval step to mark the request as approved
                request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                    RequestApproval.request_id == approval.request_id
                ).order_by(ApprovalStep.step_order).all()
                
                next_pending = any(a.status == 'pending' for a in request_approvals)
                
                if not next_pending:
                    approval.request.status = 'approved'
                    db.session.commit()
                    flash('Request has been fully approved!', 'success')
                else:
                    flash('Request approved and moved to next approval step!', 'success')

            elif action == 'reject':
                approval.status = 'rejected'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                approval.request.status = 'rejected'
                db.session.commit()
                flash('Request has been rejected.', 'warning')

            elif action == 'return':
                # The 'returned' state allows the user to fix or clarify the request
                approval.status = 'returned'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                approval.request.status = 'returned'  # Or keep separate states if you prefer
                db.session.commit()
                
                flash('Request has been returned to the requester for more information.', 'info')
            
            return redirect(url_for('pending_approvals'))
        
        # GET request
        request_data = approval.request
        form_data = request_data.form_data
        
        # Get all approvals for this request to make them available to the template
        request_data.approvals = RequestApproval.query.join(ApprovalStep).filter(
            RequestApproval.request_id == request_data.id
        ).order_by(ApprovalStep.step_order).all()
        
        return render_template('request_approval.html', approval=approval, request=request_data, form_data=form_data)

    @app.route('/approval_management')
    @active_required
    def approval_management():
        """View all requests and their approval statuses"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        # Check if user has an approval role
        if current_user.role.name not in ['admin', 'advisor', 'chair', 'dean']:
            flash('You do not have permission to view approval management.', 'warning')
            return redirect(url_for('index'))
        
        # Get all requests with their approval statuses
        requests = Request.query.all()
        for req in requests:
            # Get all approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == req.id
            ).order_by(ApprovalStep.step_order).all()
            
            # Add approval status information to the request
            req.approval_status = []
            for appr in request_approvals:
                req.approval_status.append({
                    'step': appr.step.name,
                    'status': appr.status,
                    'approver': appr.approver.full_name if appr.approver else 'Pending',
                    'comments': appr.comments,
                    'pdf_path': appr.pdf_path  # Include PDF path in context
                })
        
        return render_template('approval_management.html', requests=requests)

    @app.route('/view_request_history/<int:request_id>')
    @active_required
    def view_request_history(request_id):
        """View a request's full approval history with links to PDFs"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        # Fetch the request
        request_data = Request.query.get_or_404(request_id)
        
        # Get all approval steps for this request
        approvals = RequestApproval.query.join(ApprovalStep).filter(
            RequestApproval.request_id == request_data.id
        ).order_by(ApprovalStep.step_order).all()
        
        # Check if at least one approval has a PDF
        has_pdfs = any(approval.pdf_path for approval in approvals)
        
        return render_template(
            'request_history.html', 
            request=request_data, 
            approvals=approvals,
            has_pdfs=has_pdfs
        )

    # ----------------------------------------------------------------
    # NEW ROUTE FOR RESUBMISSION (FIX & RESUBMIT A RETURNED REQUEST)
    # ----------------------------------------------------------------
    @app.route('/resubmit_request/<int:request_id>', methods=['POST'])
    @active_required
    def resubmit_request(request_id):
        """Allows the requester to fix a 'returned' request and resubmit it (set status to 'pending')."""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()

        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))

        req = Request.query.get(request_id)
        if not req:
            flash('Request not found.', 'danger')
            return redirect(url_for('my_requests'))

        # Ensure the user owns this request (important security check)
        if req.requester_id != current_user.id:
            flash('You do not have permission to modify this request.', 'danger')
            return redirect(url_for('my_requests'))

        # Make sure it's in a 'returned' state
        if req.status != 'returned':
            flash('You can only resubmit a returned request.', 'warning')
            return redirect(url_for('my_requests'))

        # (Optional) If you want to let them update form_data, you'd do that here,
        # by reading from the POST body. If you just want to set it to pending:
        req.status = 'pending'
        db.session.commit()

        flash('Request has been resubmitted for approval.', 'success')
        return redirect(url_for('my_requests'))


# --------------------------------------------------------------------
# HELPER FUNCTION FOR PDF GENERATION
# --------------------------------------------------------------------
def generate_pdf_for_approval(approval_id):
    """
    Helper function that:
    1. Retrieves the RequestApproval record (along with the Request and requester info).
    2. Fills a LaTeX template with relevant data.
    3. Uses 'subprocess' to call 'make' in the 'pdf' folder to produce a PDF.
    4. Renames the resulting PDF and saves its path to 'approval.pdf_path'.
    Returns (pdf_path, error_message) so we can flash or handle errors gracefully.
    """
    approval = RequestApproval.query.get(approval_id)
    if not approval:
        return None, "Approval record not found."
    
    request_obj = approval.request
    requester = request_obj.requester  # who submitted the request
    
    # We'll assume the user model has a 'signature_path' column:
    signature_path = requester.signature_path if requester.signature_path else "default_signature.png"
    
    # Gather placeholders
    full_name = requester.full_name or "Unknown User"
    names = full_name.split(None, 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    approval_note = approval.comments or "No comments"
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Path to the template file
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "approval.tex")
    
    # Read the template
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading LaTeX template: {e}"
    
    # Replace placeholders
    filled_template = (
        template_content
        .replace("{{firstName}}", first_name)
        .replace("{{lastName}}", last_name)
        .replace("{{approvalNote}}", approval_note)
        .replace("{{date}}", current_date)
        .replace("{{signatureFilename}}", signature_path)
    )
    
    # Write the filled content to 'document.tex'
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"
    
    # Run 'make' to compile the PDF
    success = False
    error_msg = ""
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode == 0:
            success = True
        else:
            error_msg = f"Make command failed: {result.stderr}"
    except Exception as e:
        error_msg = f"Subprocess error: {e}"
    
    # If make failed, create a simple PDF file for testing
    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not success or not os.path.exists(generated_pdf_path):
        try:
            # Create a simple PDF file for testing
            new_filename = f"approval_{approval_id}_{int(datetime.now().timestamp())}.pdf"
            final_pdf_path = os.path.join(pdf_dir, new_filename)
            
            # For testing purposes, we'll create or copy a placeholder PDF
            from shutil import copyfile
            
            # Try to find a sample PDF to copy
            sample_pdf = None
            for root, dirs, files in os.walk(current_app.root_path):
                for file in files:
                    if file.endswith('.pdf'):
                        sample_pdf = os.path.join(root, file)
                        break
                if sample_pdf:
                    break
            
            if sample_pdf:
                # Copy an existing PDF as placeholder
                copyfile(sample_pdf, final_pdf_path)
            else:
                # Create a minimal text file with PDF extension 
                with open(final_pdf_path, 'w') as f:
                    f.write(f"PDF Placeholder for Approval {approval_id}")
            
            # Save path in the DB
            approval.pdf_path = new_filename
            db.session.commit()
            
            return final_pdf_path, f"Created placeholder PDF file. {error_msg}"
        except Exception as e:
            return None, f"Failed to create placeholder PDF: {e}. Original error: {error_msg}"
    
    # The Makefile outputs 'document.pdf'
    if not os.path.exists(generated_pdf_path):
        return None, "Expected PDF was not generated."
    
    # Rename the PDF for uniqueness, e.g. "approval_{approval_id}_{timestamp}.pdf"
    new_filename = f"approval_{approval_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)
    
    # Save path in the DB (so we know where the PDF is stored)
    approval.pdf_path = new_filename
    db.session.commit()
    
    return final_pdf_path, None
