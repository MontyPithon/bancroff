from flask import Blueprint, flash, redirect, url_for, request, session, current_app, send_from_directory, abort
import subprocess
import os
from datetime import datetime
from models import db, User, Request, RequestApproval, ApprovalStep  # Adjust import as needed

pdf_routes = Blueprint('pdf_routes', __name__)

@pdf_routes.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """
    Generates a PDF from a form submission using a LaTeX template and Makefile.
    Expects 'approval_note' in the form data, plus session data for the user's name.
    """
    # 1. Extract the approval note from the form data
    approval_note = request.form.get('approval_note', 'No approval note provided.')
    
    # 2. Retrieve user info from session (e.g., 'name' and a 'preferred_username')
    user_info = session.get("user", {})
    full_name = user_info.get("name", "Unknown User")
    names = full_name.split(" ", 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    
    # 3. Get system date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 4. Retrieve signature image path from the database
    user_db = User.query.filter_by(email=user_info.get("preferred_username", "").lower()).first()
    signature_path = user_db.signature_path if user_db and user_db.signature_path else "default_signature.png"
    
    # 5. Load the LaTeX template (pdf/approval_template.tex) using absolute paths
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "approval_template.tex")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        flash(f"Error reading LaTeX template: {e}", "danger")
        return redirect(url_for("index"))
    
    # 6. Replace placeholders with actual data
    filled_template = (template
                       .replace("{{firstName}}", first_name)
                       .replace("{{lastName}}", last_name)
                       .replace("{{approvalNote}}", approval_note)
                       .replace("{{date}}", current_date)
                       .replace("{{signatureFilename}}", signature_path))
    
    # 7. Write the filled content to pdf/document.tex using absolute paths
    output_tex = os.path.join(pdf_dir, "document.tex")
    try:
        with open(output_tex, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        flash(f"Error writing LaTeX file: {e}", "danger")
        return redirect(url_for("index"))
    
    # 8. Call 'make' in the 'pdf' folder to generate document.pdf
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            flash(f"Error generating PDF: {result.stderr}", "danger")
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error executing make command: {e}", "danger")
        return redirect(url_for("index"))
    
    # Optional: You could store the PDF in the database, or serve it to the user here.
    flash("PDF generated successfully!", "success")
    return redirect(url_for("index"))

@pdf_routes.route('/view_pdf/<int:request_id>')
def view_pdf(request_id):
    """Route to view a PDF file for a specific request."""
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Fetch the request and its latest approval
    req = Request.query.get_or_404(request_id)
    
    # Find the most recent approval that has a PDF
    approvals = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order.desc()).all()
    
    # Find the first approval that has a PDF path
    approval_with_pdf = next((a for a in approvals if a.pdf_path), None)
    
    if not approval_with_pdf or not approval_with_pdf.pdf_path:
        flash("No PDF has been generated for this request yet.", "warning")
        return redirect(url_for("pending_approvals"))
    
    pdf_filename = approval_with_pdf.pdf_path
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    
    # Serve the PDF inline for viewing
    try:
        return send_from_directory(pdf_dir, pdf_filename, as_attachment=False)
    except FileNotFoundError:
        flash("PDF file could not be found.", "danger")
        return redirect(url_for("pending_approvals"))

@pdf_routes.route('/download_pdf/<int:request_id>')
def download_pdf(request_id):
    """Route to download a PDF file for a specific request."""
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # Fetch the request and its latest approval
    req = Request.query.get_or_404(request_id)
    
    # Find the most recent approval that has a PDF
    approvals = RequestApproval.query.join(ApprovalStep).filter(
        RequestApproval.request_id == request_id
    ).order_by(ApprovalStep.step_order.desc()).all()
    
    # Find the first approval that has a PDF path
    approval_with_pdf = next((a for a in approvals if a.pdf_path), None)
    
    if not approval_with_pdf or not approval_with_pdf.pdf_path:
        flash("No PDF has been generated for this request yet.", "warning")
        return redirect(url_for("pending_approvals"))
    
    pdf_filename = approval_with_pdf.pdf_path
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    
    # Add request info to the filename for better identification when downloaded
    download_filename = f"request_{request_id}_{pdf_filename}"
    
    # Serve the PDF as an attachment for download
    try:
        return send_from_directory(pdf_dir, pdf_filename, as_attachment=True, download_name=download_filename)
    except FileNotFoundError:
        flash("PDF file could not be found.", "danger")
        return redirect(url_for("pending_approvals"))

def register_pdf_routes(app):
    """Attach the pdf_routes blueprint to the Flask app."""
    app.register_blueprint(pdf_routes)
