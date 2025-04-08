from flask import Blueprint, request, send_file, flash, redirect, url_for, render_template, current_app, send_from_directory
import os
from datetime import datetime
from models import db, RequestApproval
import subprocess
import shutil

pdf_bp = Blueprint('pdf', __name__)

def setup_pdf_routes(app):
    """Register all PDF-related routes with the Flask application"""
    app.register_blueprint(pdf_bp)

@pdf_bp.route('/generate_pdf/<int:approval_id>', methods=['GET'])
def generate_pdf_route(approval_id):
    """
    Generate and download a PDF for the specified approval ID.
    Always generates a fresh PDF with the latest data.
    
    Args:
        approval_id (int): The ID of the approval record
    
    Returns:
        PDF file attachment or redirect with flash message
    """
    approval = RequestApproval.query.get_or_404(approval_id)
    request_obj = approval.request
    requester = request_obj.requester

    # Determine which PDF generation function to use based on request type
    request_type = request_obj.request_type.name.lower()
    
    # Import the specialized PDF generation functions
    from routes.approvals import generate_rcl_pdf, generate_withdrawal_pdf, generate_pdf_for_approval
    
    # Generate the appropriate PDF based on request type
    if request_type == 'rcl':
        pdf_filename, error = generate_rcl_pdf(request_obj.id)
    elif request_type == 'withdrawal':
        pdf_filename, error = generate_withdrawal_pdf(request_obj.id)
    else:
        # Fallback to generic approval PDF
        pdf_path, error = _generate_pdf_for_approval(
            approval_id=approval_id,
            request_type=request_type,
            full_name=requester.full_name or "Unknown",
            signature_path=requester.signature_path or "default_signature.png",
            comments=approval.comments or "No comments"
        )
        if not error:
            pdf_filename = os.path.basename(pdf_path)
        else:
            pdf_filename = None

    if error or not pdf_filename:
        flash(f"PDF generation failed: {error}", "danger")
        return redirect(url_for("my_requests"))

    # Copy the generated PDF to static directory
    static_pdf_dir = os.path.join(current_app.root_path, 'static', 'pdfs')
    try:
        os.makedirs(static_pdf_dir, exist_ok=True)
        pdf_dir = os.path.join(current_app.root_path, "pdf")
        source_pdf = os.path.join(pdf_dir, pdf_filename)
        static_pdf_path = os.path.join(static_pdf_dir, f'approval_{approval_id}.pdf')
        shutil.copy2(source_pdf, static_pdf_path)
        # Update the approval record with the static path
        approval.pdf_path = f'approval_{approval_id}.pdf'
        db.session.commit()
    except Exception as e:
        flash(f"Error saving PDF: {str(e)}", "danger")
        return redirect(url_for("my_requests"))

    return send_from_directory(static_pdf_dir, f'approval_{approval_id}.pdf', as_attachment=False)

def _generate_pdf_for_approval(approval_id, request_type, full_name, signature_path, comments):
    """
    Internal function to handle PDF generation logic
    
    Returns:
        tuple: (pdf_path, error_message)
    """
    try:
        # Process name components
        names = full_name.split(None, 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Set up file paths
        pdf_dir = os.path.join(current_app.root_path, "pdf")
        template_file = os.path.join(pdf_dir, f"{request_type}_template.tex")
        tex_output = os.path.join(pdf_dir, "document.tex")
        final_pdf = os.path.join(pdf_dir, f"approval_{approval_id}_{int(datetime.now().timestamp())}.pdf")

        # Read and process template
        with open(template_file, "r", encoding="utf-8") as f:
            tex = f.read() \
                .replace("{{firstName}}", first_name) \
                .replace("{{lastName}}", last_name) \
                .replace("{{approvalNote}}", comments) \
                .replace("{{date}}", current_date) \
                .replace("{{signatureFilename}}", signature_path)

        # Write processed template
        with open(tex_output, "w", encoding="utf-8") as f:
            f.write(tex)

        # Generate PDF
        subprocess.run(["make"], cwd=pdf_dir, check=True)
        
        # Verify and rename output
        pdf_file = os.path.join(pdf_dir, "document.pdf")
        if not os.path.exists(pdf_file):
            return None, "PDF was not created."

        os.rename(pdf_file, final_pdf)

        return final_pdf, None

    except Exception as e:
        current_app.logger.error(f"PDF generation failed: {str(e)}")
        return None, str(e)
