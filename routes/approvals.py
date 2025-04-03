from flask import render_template, redirect, url_for, flash, request as flask_request, session, current_app
import subprocess
import os
from datetime import datetime
from models import db, User, RequestApproval, ApprovalStep, Request, RequestType
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
                
                all_approvals.append({
                    'approval_id': current_step.id,
                    'request': req,
                    'request_type': req.request_type.name,
                    'requester': req.requester.full_name,
                    'submitted': req.created_at,
                    'step': current_step.step.name,
                    'status': req.status,
                    'can_approve': can_approve,
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
        
        # Check role vs. step requirement
        approver_role = approval.step.approver_role
        can_approve = False
        if current_user.role.name == 'admin':
            can_approve = True
        elif approver_role and current_user.role.name == approver_role.name:
            can_approve = True
        elif current_user.role_id == approval.step.approver_role_id:
            can_approve = True
            
        if not can_approve:
            role_required = approver_role.name if approver_role else "Unknown"
            flash(f'You do not have permission to approve this request. Required role: {role_required}', 'danger')
            return redirect(url_for('pending_approvals'))
        
        if approval.status != 'pending' and approval.request.status != 'submitted':
            flash('This request has already been processed or is not in an approvable status.', 'warning')
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
                
                # Decide which PDF generation function to call based on request type
                req_obj = approval.request
                req_type = req_obj.request_type.name
                
                if req_type == 'RCL':
                    pdf_path, error = generate_rcl_pdf(req_obj.id)
                elif req_type == 'Withdrawal':
                    pdf_path, error = generate_withdrawal_pdf(req_obj.id)
                else:
                    # Fallback to the generic approach
                    pdf_path, error = generate_pdf_for_approval(approval.id)
                
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
                approval.approved_at = db.func.current_timestamp()
                approval.request.status = 'rejected'
                db.session.commit()
                flash('Request has been rejected.', 'warning')

            elif action == 'return':
                approval.status = 'returned'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                approval.request.status = 'returned'
                db.session.commit()
                
                flash('Request has been returned to the requester for more information.', 'info')
            
            return redirect(url_for('pending_approvals'))
        
        # GET request
        request_data = approval.request
        form_data = request_data.form_data
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
    Generate a PDF specifically for an RCL request by using a specialized LaTeX template.
    Returns (pdf_filename, error_message).
    """
    from models import Request
    req = Request.query.get(request_id)
    if not req:
        return None, "Request not found for RCL PDF generation."

    form_data = req.form_data or {}
    # Extract RCL-specific fields
    full_name = req.requester.full_name if req.requester else "Unknown"
    ps_id = form_data.get("ps_id", "")
    semester = form_data.get("semester", "")
    year = form_data.get("year", "")
    track = form_data.get("track", "")
    reason = form_data.get("reason", "")
    courses_list = form_data.get("courses", [])
    courses_str = ", ".join(courses_list) if courses_list else "None"
    non_thesis_hours = form_data.get("non_thesis_hours", "")
    thesis_hours = form_data.get("thesis_hours", "")
    letter_attached = "Yes" if form_data.get("letter_attached") else "No"
    remaining_hours = form_data.get("remaining_hours", "")
    signature_date = form_data.get("signature_date", str(datetime.now().date()))
    signature_path = form_data.get("signature_path", "default_signature.png")

    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "rcl_template.tex")  # Make sure you have 'rcl_template.tex' in pdf/

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading RCL template: {e}"

    # Fill placeholders
    filled_template = (template_content
        .replace("{{fullName}}", full_name)
        .replace("{{ps_id}}", ps_id)
        .replace("{{semester}}", semester)
        .replace("{{year}}", year)
        .replace("{{track}}", track)
        .replace("{{reason}}", reason)
        .replace("{{courses}}", courses_str)
        .replace("{{non_thesis_hours}}", non_thesis_hours)
        .replace("{{thesis_hours}}", thesis_hours)
        .replace("{{letter_attached}}", letter_attached)
        .replace("{{remaining_hours}}", remaining_hours)
        .replace("{{signature_date}}", signature_date)
        .replace("{{signature_path}}", signature_path)
    )

    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"

    # Run 'make'
    try:
        result = subprocess.run(["make"], cwd=pdf_dir)
        if result.returncode != 0:
            return None, "pdflatex (Makefile) failed for RCL PDF."
    except Exception as e:
        return None, f"Subprocess error: {e}"

    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        return None, "document.pdf not found after RCL PDF generation."

    new_filename = f"rcl_{request_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)

    # Optionally store path in your DB
    req.final_document_path = new_filename
    db.session.commit()

    return new_filename, None

def generate_withdrawal_pdf(request_id):
    """
    Generate a PDF specifically for a Withdrawal request by using a specialized LaTeX template.
    Returns (pdf_filename, error_message).
    """
    from models import Request
    req = Request.query.get(request_id)
    if not req:
        return None, "Request not found for Withdrawal PDF generation."

    form_data = req.form_data or {}
    full_name = req.requester.full_name if req.requester else "Unknown"
    myUHID = form_data.get('myUHID', '')
    college = form_data.get('college', '')
    planDegree = form_data.get('planDegree', '')
    address = form_data.get('address', '')
    phoneNumber = form_data.get('phoneNumber', '')
    termYear = form_data.get('termYear', '')
    reason = form_data.get('reason', '')
    lastDateAttended = form_data.get('lastDateAttended', '')
    financialAssistance = "Yes" if form_data.get('financialAssistance') else "No"
    studentHealthInsurance = "Yes" if form_data.get('studentHealthInsurance') else "No"
    campusHousing = "Yes" if form_data.get('campusHousing') else "No"
    visaStatus = "Yes" if form_data.get('visaStatus') else "No"
    giBillBenefits = "Yes" if form_data.get('giBillBenefits') else "No"
    withdrawalType = form_data.get('withdrawalType', '')
    coursesToWithdraw = form_data.get('coursesToWithdraw', '')
    additionalComments = form_data.get('additionalComments', '')
    signature_path = form_data.get('signature_path', 'default_signature.png')
    submissionDate = form_data.get('submissionDate', str(datetime.now().date()))

    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "withdrawal_template.tex")  # Must exist in pdf/

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading Withdrawal template: {e}"

    # Fill placeholders
    filled_template = (template_content
        .replace("{{fullName}}", full_name)
        .replace("{{myUHID}}", myUHID)
        .replace("{{college}}", college)
        .replace("{{planDegree}}", planDegree)
        .replace("{{address}}", address)
        .replace("{{phoneNumber}}", phoneNumber)
        .replace("{{termYear}}", termYear)
        .replace("{{reason}}", reason)
        .replace("{{lastDateAttended}}", lastDateAttended)
        .replace("{{financialAssistance}}", financialAssistance)
        .replace("{{studentHealthInsurance}}", studentHealthInsurance)
        .replace("{{campusHousing}}", campusHousing)
        .replace("{{visaStatus}}", visaStatus)
        .replace("{{giBillBenefits}}", giBillBenefits)
        .replace("{{withdrawalType}}", withdrawalType)
        .replace("{{coursesToWithdraw}}", coursesToWithdraw)
        .replace("{{additionalComments}}", additionalComments)
        .replace("{{signature_path}}", signature_path)
        .replace("{{submissionDate}}", submissionDate)
    )

    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"

    # Run 'make'
    try:
        result = subprocess.run(["make"], cwd=pdf_dir)
        if result.returncode != 0:
            return None, "pdflatex (Makefile) failed for Withdrawal PDF."
    except Exception as e:
        return None, f"Subprocess error: {e}"

    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        return None, "document.pdf not found after Withdrawal PDF generation."

    new_filename = f"withdrawal_{request_id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)

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
    
    signature_path = requester.signature_path if requester.signature_path else "default_signature.png"
    
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
        .replace("{{signatureFilename}}", signature_path)
    )
    
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"
    
    try:
        result = subprocess.run(["make"], cwd=pdf_dir)
        if result.returncode != 0:
            return None, "Error: pdflatex (via Makefile) failed to generate PDF."
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
