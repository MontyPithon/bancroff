from flask import render_template, redirect, url_for, flash, request as flask_request, session, current_app
import subprocess
import os
from datetime import datetime
from models import db, User, RequestApproval, ApprovalStep, Request, RequestType
from utils.auth_helpers import active_required
from PIL import Image, ImageDraw, ImageFont

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
        
        # Add approval status information to each request
        for req in requests:
            # Get all approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == req.id
            ).order_by(ApprovalStep.step_order).all()
            
            # Add approval status to each request
            req.approval_status = []
            for approval in request_approvals:
                role_name = approval.step.approver_role.name if approval.step.approver_role else "Unknown"
                req.approval_status.append({
                    'role': role_name,
                    'step': approval.step.name,
                    'status': approval.status,
                    'approver': approval.approver.full_name if approval.approver else 'Pending'
                })
        
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
            
            # Find the current pending step or the last step if none are pending
            current_step = next((a for a in request_approvals if a.status == 'pending'), 
                                request_approvals[-1] if request_approvals else None)
            
            if current_step:
                can_approve = False
                
                # Check if we can approve
                if (current_step.status == 'pending' or req.status == 'submitted'):
                    if current_user.role.name == 'admin':
                        can_approve = True
                    elif current_step.step.approver_role and current_user.role.name == current_step.step.approver_role.name:
                        can_approve = True
                    elif current_user.role_id == current_step.step.approver_role_id:
                        can_approve = True
                
                # Collect info
                approver_role_info = {
                    'id': current_step.step.approver_role_id,
                    'name': current_step.step.approver_role.name if current_step.step.approver_role else "Unknown"
                }
                
                # Get the latest approval for this request
                latest_approval = RequestApproval.query.join(ApprovalStep).filter(
                    RequestApproval.request_id == req.id
                ).order_by(ApprovalStep.step_order.desc()).first()
                
                all_approvals.append({
                    'approval_id': current_step.id,
                    'request': req,
                    'request_type': req.request_type.name,
                    'requester': req.requester.full_name,
                    'submitted': req.created_at,
                    'step': current_step.step.name,
                    'status': req.status,
                    'can_approve': can_approve,
                    'latest_approval': latest_approval,
                    'pdf_path': current_step.pdf_path,
                    'approval_status': [{
                        'step': a.step.name,
                        'status': a.status,
                        'approver': a.approver.full_name if a.approver else 'Pending'
                    } for a in request_approvals],
                    'debug_info': {
                        'user_role_name': current_user.role.name,
                        'user_role_id': current_user.role_id,
                        'step_approver_role_name': approver_role_info['name'],
                        'step_approver_role_id': approver_role_info['id'],
                        'step_status': current_step.status
                    }
                })
        
        return render_template('pending_approvals.html', pending_approvals=all_approvals)

    @app.route('/request_approval/<int:approval_id>', methods=['GET', 'POST'])
    @active_required
    def request_approval(approval_id):
        """View and process approval for a specific request"""
        approval = RequestApproval.query.get_or_404(approval_id)
        current_user = User.query.filter_by(email=session['user'].get('preferred_username').lower()).first()
        
        # Check if user has permission to approve
        if not current_user or current_user.role.name.lower() not in ['admin', 'advisor', 'chair', 'dean']:
            flash('You do not have permission to approve requests.', 'danger')
            return redirect(url_for('index'))
        
        # Check if this is the current user's turn to approve
        if approval.status != 'pending':
            flash('This request has already been processed.', 'warning')
            return redirect(url_for('pending_approvals'))
        
        if flask_request.method == 'POST':
            action = flask_request.form.get('action')
            comments = flask_request.form.get('comments', '')
            
            if action == 'approve':
                # Check if approver has a signature
                if not current_user.signature_path:
                    flash('Please upload your signature before approving requests.', 'warning')
                    return redirect(url_for('upload_signature'))
                
                approval.status = 'approved'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                
                db.session.commit()
                
                # Generate PDF with all signatures up to this point
                request_type = approval.request.request_type.name.lower()
                if request_type == 'withdrawal':
                    pdf_filename, error = generate_withdrawal_pdf(approval.request.id)
                elif request_type == 'rcl':
                    pdf_filename, error = generate_rcl_pdf(approval.request.id)
                else:
                    pdf_path, error = generate_pdf_for_approval(approval.id)
                    if not error:
                        pdf_filename = os.path.basename(pdf_path)
                    else:
                        pdf_filename = None
                
                if error:
                    flash(f"PDF generation error: {error}", "danger")
                else:
                    flash("PDF generated successfully!", "success")
                
                # Check if this was the last approval step
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
                approval.rejected_at = db.func.current_timestamp()
                
                # Update request status
                approval.request.status = 'rejected'
                
                db.session.commit()
                flash('Request has been rejected.', 'warning')
                
            elif action == 'return':
                approval.status = 'returned'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.returned_at = db.func.current_timestamp()
                
                # Update request status
                approval.request.status = 'returned'
                
                db.session.commit()
                flash('Request has been returned for revision.', 'info')
            
            return redirect(url_for('pending_approvals'))
        
        # GET request - show the approval form
        return render_template('request_approval.html', approval=approval)

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
        
        if current_user.role.name not in ['admin', 'advisor', 'chair', 'dean']:
            flash('You do not have permission to view approval management.', 'warning')
            return redirect(url_for('index'))
        
        requests = Request.query.all()
        for req in requests:
            # get the approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == req.id
            ).order_by(ApprovalStep.step_order).all()
            
            req.approval_status = []
            for appr in request_approvals:
                req.approval_status.append({
                    'step': appr.step.name,
                    'status': appr.status,
                    'approver': appr.approver.full_name if appr.approver else 'Pending',
                    'comments': appr.comments
                })
        
        return render_template('approval_management.html', requests=requests)

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

        # Ensure the user owns this request
        if req.requester_id != current_user.id:
            flash('You do not have permission to modify this request.', 'danger')
            return redirect(url_for('my_requests'))

        if req.status != 'returned':
            flash('You can only resubmit a returned request.', 'warning')
            return redirect(url_for('my_requests'))

        req.status = 'pending'
        db.session.commit()

        flash('Request has been resubmitted for approval.', 'success')
        return redirect(url_for('my_requests'))


# --------------------------------------------------------------------
# HELPER FUNCTIONS FOR PDF GENERATION
# --------------------------------------------------------------------

def generate_rcl_pdf(request_id):
    """
    Generate a PDF for an RCL request using a LaTeX template.
    Returns (pdf_filename, error_message).
    """
    from models import Request, RequestApproval, ApprovalStep
    req = Request.query.get(request_id)
    if not req:
        return None, "Request not found for RCL PDF generation."

    # Get all approvals for this request in order
    approvals = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order).all()

    if not approvals:
        return None, "No approval records found for RCL PDF generation."

    # Create necessary directories
    uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    # Get the latest form data
    form_data = req.form_data or {}
    
    # Extract RCL-specific fields with proper fallbacks
    full_name = req.requester.full_name if req.requester else "Unknown"
    ps_id = form_data.get("ps_id", "")
    semester = form_data.get("semester", "").title()  # Capitalize first letter
    year = form_data.get("year", "")
    
    # Get the formatted reason
    reason_text = []
    
    # Check for Initial Adjustment Issues (IAI)
    iai_list = form_data.get("iai", [])
    if iai_list:
        iai_text = "Initial Adjustment Issues: "
        if "english" in iai_list:
            iai_text += "English language difficulties"
        if "reading" in iai_list:
            iai_text += "Reading requirements difficulties"
        if "teaching" in iai_list:
            iai_text += "Unfamiliarity with American teaching methods"
        reason_text.append(iai_text)
    
    # Check for Improper Course Level Placement (ICLP)
    if form_data.get("reason") == "iclp":
        reason_text.append("Improper Course Level Placement: Difficulty with class(es) due to improper course level placement, which may include not having the prerequisites or insufficient background to complete the course at this time.")
    
    # Check for Medical Reason
    elif form_data.get("reason") == "medical":
        reason_text.append("Medical Reason: Valid medical reason with supporting documentation from a licensed medical professional.")
    
    # Check for Final Semester
    track = form_data.get("track")
    if track == "non_thesis":
        hours = form_data.get("non_thesis_hours", "")
        reason_text.append(f"Final Semester (Non-Thesis Track): Only {hours} hours needed to complete degree program.")
    elif track == "thesis":
        hours = form_data.get("thesis_hours", "")
        reason_text.append(f"Final Semester (Thesis Track): Working on thesis/dissertation with {hours} hours of thesis/dissertation credit.")
    
    reason = "\n\n".join(reason_text) if reason_text else "No reason specified"
    
    # Get courses and format them
    courses = form_data.get("courses", [])
    if not courses:
        # Fallback for old format
        for i in range(1, 4):
            course = form_data.get(f"course{i}")
            if course:
                courses.append(course)
    courses_str = "\n".join(f"• {course}" for course in courses) if courses else "None"
    
    # Get remaining hours
    remaining_hours = form_data.get("remaining_hours", "")
    
    # Get letter attachment status
    letter_attached = "Yes" if form_data.get("letter_attached") is True else "No"
    
    # Get signature date and path
    signature_date = form_data.get("signature_date", str(datetime.now().date()))
    signature_path = req.requester.signature_path if req.requester else None
    
    # Initialize approver information
    advisor_signature = ""
    advisor_name = "Not Yet Approved"
    advisor_date = ""
    advisor_comments = ""
    
    chair_signature = ""
    chair_name = "Not Yet Approved"
    chair_date = ""
    chair_comments = ""
    
    dean_signature = ""
    dean_name = "Not Yet Approved"
    dean_date = ""
    dean_comments = ""
    
    # Helper function to copy signature to PDF directory
    def copy_signature_to_pdf_dir(sig_path):
        if not sig_path:
            return
        src_path = os.path.join(uploads_dir, sig_path)
        if os.path.exists(src_path):
            try:
                import shutil
                shutil.copy2(src_path, os.path.join(pdf_dir, sig_path))
            except Exception as e:
                current_app.logger.warning(f"Could not copy signature file: {e}")
    
    # Process approvals to get signature information
    for approval in approvals:
        role = approval.step.approver_role.name if approval.step.approver_role else ""
        
        if role == 'advisor':
            if approval.status == 'approved' and approval.approver:
                advisor_signature = approval.approver.signature_path or ""
                advisor_name = approval.approver.full_name
                advisor_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                advisor_comments = approval.comments or ""
                copy_signature_to_pdf_dir(advisor_signature)
        
        elif role == 'chair':
            if approval.status == 'approved' and approval.approver:
                chair_signature = approval.approver.signature_path or ""
                chair_name = approval.approver.full_name
                chair_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                chair_comments = approval.comments or ""
                copy_signature_to_pdf_dir(chair_signature)
        
        elif role == 'dean':
            if approval.status == 'approved' and approval.approver:
                dean_signature = approval.approver.signature_path or ""
                dean_name = approval.approver.full_name
                dean_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                dean_comments = approval.comments or ""
                copy_signature_to_pdf_dir(dean_signature)

    # Copy student signature if it exists
    if signature_path:
        copy_signature_to_pdf_dir(signature_path)
        # Make sure we use a fully qualified path for LaTeX
        signature_path = "./".join(signature_path.rsplit("/", 1) if "/" in signature_path else ("", signature_path))
    else:
        signature_path = "non_existent_file.png"  # Use a non-existent file for IfFileExists to skip
        
    # Ensure signature paths are properly formatted for LaTeX IfFileExists command
    if advisor_signature and advisor_signature.strip():
        advisor_signature = "./".join(advisor_signature.rsplit("/", 1) if "/" in advisor_signature else ("", advisor_signature))
    else:
        advisor_signature = "non_existent_file.png"
        
    if chair_signature and chair_signature.strip():
        chair_signature = "./".join(chair_signature.rsplit("/", 1) if "/" in chair_signature else ("", chair_signature))
    else:
        chair_signature = "non_existent_file.png"
        
    if dean_signature and dean_signature.strip():
        dean_signature = "./".join(dean_signature.rsplit("/", 1) if "/" in dean_signature else ("", dean_signature))
    else:
        dean_signature = "non_existent_file.png"

    template_path = os.path.join(pdf_dir, "rcl_template.tex")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading RCL template: {e}"

    # Helper function to escape LaTeX special characters
    def escape_latex(text):
        if not isinstance(text, str):
            text = str(text)
        special_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
            '<': r'\textless{}',
            '>': r'\textgreater{}'
        }
        for char, escape in special_chars.items():
            text = text.replace(char, escape)
        return text

    # Fill template with escaped values
    filled_template = (template_content
        .replace("{{fullName}}", escape_latex(full_name))
        .replace("{{psId}}", escape_latex(ps_id))
        .replace("{{semester}}", escape_latex(semester))
        .replace("{{year}}", escape_latex(year))
        .replace("{{reason}}", escape_latex(reason))
        .replace("{{courses}}", escape_latex(courses_str))
        .replace("{{remainingHours}}", escape_latex(remaining_hours))
        .replace("{{letterAttached}}", escape_latex(letter_attached))
        .replace("{{signatureDate}}", escape_latex(signature_date))
        .replace("{{studentSignature}}", signature_path if signature_path else "")
        .replace("{{advisorSignature}}", advisor_signature if advisor_signature else "")
        .replace("{{advisorName}}", escape_latex(advisor_name))
        .replace("{{advisorDate}}", escape_latex(advisor_date))
        .replace("{{advisorComments}}", escape_latex(advisor_comments))
        .replace("{{chairSignature}}", chair_signature if chair_signature else "")
        .replace("{{chairName}}", escape_latex(chair_name))
        .replace("{{chairDate}}", escape_latex(chair_date))
        .replace("{{chairComments}}", escape_latex(chair_comments))
        .replace("{{deanSignature}}", dean_signature if dean_signature else "")
        .replace("{{deanName}}", escape_latex(dean_name))
        .replace("{{deanDate}}", escape_latex(dean_date))
        .replace("{{deanComments}}", escape_latex(dean_comments))
    )

    # Write filled template
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"

    # Run pdflatex
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            # Try to read the log file for more details
            log_path = os.path.join(pdf_dir, "document.log")
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
            
            error_message = f"pdflatex (Makefile) failed for RCL PDF.\n"
            error_message += f"Make error: {result.stderr}\n"
            error_message += f"Make output: {result.stdout}\n"
            if log_content:
                error_message += f"LaTeX log:\n{log_content}"
            return None, error_message
    except Exception as e:
        return None, f"Subprocess error: {e}"

    # Clean up copied signature files
    for sig_path in [signature_path, advisor_signature, chair_signature, dean_signature]:
        if sig_path and sig_path != "non_existent_file.png":
            try:
                os.remove(os.path.join(pdf_dir, sig_path))
            except Exception as e:
                print(f"Warning: Could not remove temporary signature file: {e}")

    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        return None, "document.pdf not found after RCL PDF generation."

    new_filename = f"rcl_{request_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)

    # Update all approval records with the new filename
    for approval in approvals:
        if approval.status == 'approved':
            approval.pdf_path = new_filename
    db.session.commit()

    # Get the latest approval to update specifically
    latest_approval = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order.desc()).first()
    
    if latest_approval:
        latest_approval.pdf_path = new_filename
        db.session.commit()

    # Also update the request's final document path
    req.final_document_path = new_filename
    db.session.commit()

    return new_filename, None

def generate_withdrawal_pdf(request_id):
    """
    Generate a PDF for a withdrawal request using a LaTeX template.
    Returns (pdf_filename, error_message).
    """
    from models import Request, RequestApproval, ApprovalStep
    req = Request.query.get(request_id)
    if not req:
        return None, "Request not found for withdrawal PDF generation."

    # Get all approvals for this request in order
    approvals = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order).all()

    if not approvals:
        return None, "No approval records found for withdrawal PDF generation."

    # Create necessary directories
    uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    # Get the latest form data
    form_data = req.form_data or {}
    
    # Extract withdrawal-specific fields with proper fallbacks
    full_name = req.requester.full_name if req.requester else "Unknown"
    
    # Get student information
    ps_id = form_data.get("myUHID", "")
    college = form_data.get("college", "")
    plan_degree = form_data.get("planDegree", "")
    address = form_data.get("address", "")
    phone = form_data.get("phoneNumber", "")
    
    # Get withdrawal details
    term_year = form_data.get("termYear", "")
    reason = form_data.get("reason", "")
    last_date_attended = form_data.get("lastDateAttended", "")
    financial_assistance = "Yes" if form_data.get("financialAssistance") else "No"
    student_health_insurance = "Yes" if form_data.get("studentHealthInsurance") else "No"
    campus_housing = "Yes" if form_data.get("campusHousing") else "No"
    visa_status = "Yes" if form_data.get("visaStatus") else "No"
    gi_bill_benefits = "Yes" if form_data.get("giBillBenefits") else "No"
    
    # Get withdrawal type
    withdrawal_type = form_data.get("withdrawalType", "")
    
    # Get courses
    courses = form_data.get("coursesToWithdraw", "None")
    
    # Get additional comments
    additional_comments = form_data.get("additionalComments", "")
    
    # Get student signature info
    signature_date = form_data.get("signature_date", str(datetime.now().date()))
    signature_path = form_data.get("signature_path")

    # Initialize approver information
    advisor_signature = ""
    advisor_name = "Pending"
    advisor_date = ""
    advisor_comments = ""
    
    chair_signature = ""
    chair_name = "Pending"
    chair_date = ""
    chair_comments = ""
    
    dean_signature = ""
    dean_name = "Pending"
    dean_date = ""
    dean_comments = ""

    # Helper function to copy signature to PDF directory
    def copy_signature_to_pdf_dir(sig_path):
        if sig_path:
            src_path = os.path.join(uploads_dir, sig_path)
            if os.path.exists(src_path):
                try:
                    import shutil
                    dest_path = os.path.join(pdf_dir, sig_path)
                    shutil.copy2(src_path, dest_path)
                    return sig_path
                except Exception as e:
                    print(f"Warning: Could not copy signature file: {e}")
        return None

    # Process each approval to get signatures up to the current step
    current_step = None
    for approval in approvals:
        role = approval.step.approver_role.name if approval.step.approver_role else ""
        
        if role == 'advisor':
            if approval.status == 'approved' and approval.approver:
                advisor_signature = approval.approver.signature_path or ""
                advisor_name = approval.approver.full_name
                advisor_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                advisor_comments = approval.comments or ""
                copy_signature_to_pdf_dir(advisor_signature)
            current_step = 'advisor'
        
        elif role == 'chair':
            if approval.status == 'approved' and approval.approver:
                chair_signature = approval.approver.signature_path or ""
                chair_name = approval.approver.full_name
                chair_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                chair_comments = approval.comments or ""
                copy_signature_to_pdf_dir(chair_signature)
            current_step = 'chair'
        
        elif role == 'dean':
            if approval.status == 'approved' and approval.approver:
                dean_signature = approval.approver.signature_path or ""
                dean_name = approval.approver.full_name
                dean_date = approval.approved_at.strftime("%Y-%m-%d") if approval.approved_at else ""
                dean_comments = approval.comments or ""
                copy_signature_to_pdf_dir(dean_signature)
            current_step = 'dean'

    # Copy student signature if it exists
    if signature_path:
        copy_signature_to_pdf_dir(signature_path)
        # Make sure we use a fully qualified path for LaTeX
        signature_path = "./".join(signature_path.rsplit("/", 1) if "/" in signature_path else ("", signature_path))
    else:
        signature_path = "non_existent_file.png"  # Use a non-existent file for IfFileExists to skip
        
    # Ensure signature paths are properly formatted for LaTeX IfFileExists command
    if advisor_signature and advisor_signature.strip():
        advisor_signature = "./".join(advisor_signature.rsplit("/", 1) if "/" in advisor_signature else ("", advisor_signature))
    else:
        advisor_signature = "non_existent_file.png"
        
    if chair_signature and chair_signature.strip():
        chair_signature = "./".join(chair_signature.rsplit("/", 1) if "/" in chair_signature else ("", chair_signature))
    else:
        chair_signature = "non_existent_file.png"
        
    if dean_signature and dean_signature.strip():
        dean_signature = "./".join(dean_signature.rsplit("/", 1) if "/" in dean_signature else ("", dean_signature))
    else:
        dean_signature = "non_existent_file.png"

    template_path = os.path.join(pdf_dir, "withdrawal_template.tex")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading withdrawal template: {e}"

    # Helper function to escape LaTeX special characters
    def escape_latex(text):
        if not isinstance(text, str):
            text = str(text)
        special_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
            '<': r'\textless{}',
            '>': r'\textgreater{}'
        }
        for char, escape in special_chars.items():
            text = text.replace(char, escape)
        return text

    # Fill template with escaped values
    filled_template = (template_content
        .replace("{{fullName}}", escape_latex(full_name))
        .replace("{{psId}}", escape_latex(ps_id))
        .replace("{{college}}", escape_latex(college))
        .replace("{{planDegree}}", escape_latex(plan_degree))
        .replace("{{address}}", escape_latex(address))
        .replace("{{phone}}", escape_latex(phone))
        .replace("{{termYear}}", escape_latex(term_year))
        .replace("{{reason}}", escape_latex(reason))
        .replace("{{courses}}", escape_latex(courses))
        .replace("{{withdrawalType}}", escape_latex(withdrawal_type))
        .replace("{{lastDateAttended}}", escape_latex(last_date_attended))
        .replace("{{financialAssistance}}", escape_latex(financial_assistance))
        .replace("{{studentHealthInsurance}}", escape_latex(student_health_insurance))
        .replace("{{campusHousing}}", escape_latex(campus_housing))
        .replace("{{visaStatus}}", escape_latex(visa_status))
        .replace("{{giBillBenefits}}", escape_latex(gi_bill_benefits))
        .replace("{{additionalComments}}", escape_latex(additional_comments))
        .replace("{{signatureDate}}", escape_latex(signature_date))
        .replace("{{studentSignature}}", signature_path if signature_path else "")
        .replace("{{advisorSignature}}", advisor_signature if advisor_signature else "")
        .replace("{{advisorName}}", escape_latex(advisor_name))
        .replace("{{advisorDate}}", escape_latex(advisor_date))
        .replace("{{advisorComments}}", escape_latex(advisor_comments))
        .replace("{{chairSignature}}", chair_signature if chair_signature else "")
        .replace("{{chairName}}", escape_latex(chair_name))
        .replace("{{chairDate}}", escape_latex(chair_date))
        .replace("{{chairComments}}", escape_latex(chair_comments))
        .replace("{{deanSignature}}", dean_signature if dean_signature else "")
        .replace("{{deanName}}", escape_latex(dean_name))
        .replace("{{deanDate}}", escape_latex(dean_date))
        .replace("{{deanComments}}", escape_latex(dean_comments))
    )

    # Write filled template
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"

    # Run pdflatex
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            # Try to read the log file for more details
            log_path = os.path.join(pdf_dir, "document.log")
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
            
            error_message = f"pdflatex (Makefile) failed for withdrawal PDF.\n"
            error_message += f"Make error: {result.stderr}\n"
            error_message += f"Make output: {result.stdout}\n"
            if log_content:
                error_message += f"LaTeX log:\n{log_content}"
            return None, error_message
    except Exception as e:
        return None, f"Subprocess error: {e}"

    # Clean up copied signature files
    for sig_path in [signature_path, advisor_signature, chair_signature, dean_signature]:
        if sig_path:
            try:
                os.remove(os.path.join(pdf_dir, sig_path))
            except Exception as e:
                print(f"Warning: Could not remove temporary signature file: {e}")

    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        return None, "document.pdf not found after withdrawal PDF generation."

    new_filename = f"withdrawal_{request_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)

    # Update all approval records with the new filename
    for approval in approvals:
        if approval.status == 'approved':
            approval.pdf_path = new_filename
    db.session.commit()

    # Get the latest approval to update specifically
    latest_approval = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order.desc()).first()
    
    if latest_approval:
        latest_approval.pdf_path = new_filename
        db.session.commit()

    # Also update the request's final document path
    req.final_document_path = new_filename
    db.session.commit()

    return new_filename, None


def generate_pdf_for_approval(approval_id):
    """
    (Generic fallback) Helper function for approvals that don't match RCL or Withdrawal,
    or if you want a generic template for other forms.
    """
    approval = RequestApproval.query.get(approval_id)
    if not approval:
        return None, "Approval record not found."
    
    request_obj = approval.request
    requester = request_obj.requester  # who submitted the request
    
    # Create necessary directories
    uploads_dir = os.path.join(current_app.root_path, "uploads")
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)

    # Create default signature PNG if it doesn't exist
    signature_path = "default_signature.png"
    default_sig = os.path.join(uploads_dir, signature_path)
    if not os.path.exists(default_sig):
        try:
            # Create a new image with white background
            img = Image.new('RGB', (400, 100), color='white')
            d = ImageDraw.Draw(img)
            # Try to use a system font, fallback to default if not found
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except:
                font = ImageFont.load_default()
            # Draw placeholder text
            d.text((10, 30), "Default Signature", font=font, fill='black')
            img.save(default_sig, 'PNG')
        except Exception as e:
            print(f"Warning: Could not create PNG signature: {e}")
            # Create a minimal valid PNG file as fallback
            with open(default_sig, 'wb') as f:
                # Minimal valid PNG file (1x1 transparent pixel)
                f.write(bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63000000000000ffff00000500000007'))
    
    full_name = requester.full_name or "Unknown User"
    names = full_name.split(None, 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    approval_note = approval.comments or "No comments"
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "approval_template.tex")
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading LaTeX template: {e}"
    
    filled_template = (
        template_content
        .replace("{{firstName}}", first_name)
        .replace("{{lastName}}", last_name)
        .replace("{{approvalNote}}", approval_note)
        .replace("{{date}}", current_date)
        .replace("{{signatureFilename}}", signature_path)  # Don't escape the signature path
    )
    
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"
    
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"Error: pdflatex (via Makefile) failed to generate PDF. Error: {result.stderr}"
    except Exception as e:
        return None, f"Subprocess error: {e}"
    
    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        return None, "Expected PDF was not generated."
    
    new_filename = f"approval_{approval_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)
    
    approval.pdf_path = new_filename
    db.session.commit()
    
    return final_pdf_path, None
