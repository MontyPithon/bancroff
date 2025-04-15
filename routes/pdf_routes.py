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
    try:
        approval = RequestApproval.query.get_or_404(approval_id)
        request_obj = approval.request
        requester = request_obj.requester

        # Determine which PDF generation function to use based on request type
        request_type = request_obj.request_type.name.lower()
        current_app.logger.info(f"Generating PDF for {request_type} request ID {request_obj.id}")
        
        # Import the specialized PDF generation functions
        from routes.approvals import generate_rcl_pdf, generate_withdrawal_pdf, generate_pdf_for_approval
        
        # Generate the appropriate PDF based on request type
        if request_type == 'rcl':
            current_app.logger.info(f"Calling generate_rcl_pdf for request {request_obj.id}")
            pdf_filename, error = generate_rcl_pdf(request_obj.id)
        elif request_type == 'withdrawal':
            current_app.logger.info(f"Calling generate_withdrawal_pdf for request {request_obj.id}")
            pdf_filename, error = generate_withdrawal_pdf(request_obj.id)
        else:
            # Fallback to generic approval PDF
            current_app.logger.info(f"Calling generate_pdf_for_approval for approval {approval_id}")
            pdf_path, error = generate_pdf_for_approval(approval_id)
            if not error:
                pdf_filename = os.path.basename(pdf_path)
            else:
                pdf_filename = None

        if error or not pdf_filename:
            current_app.logger.error(f"PDF generation failed for approval {approval_id}: {error}")
            flash(f"PDF generation failed: {error}", "danger")
            return redirect(url_for("pending_approvals"))

        # Refresh approval object to get the latest pdf_path after generation
        db.session.refresh(approval)
        
        # Check both approval.pdf_path and pdf_filename to find the correct file
        target_filename = approval.pdf_path or pdf_filename
        current_app.logger.info(f"Using target filename: {target_filename}")
        
        # Ensure static PDF directory exists
        static_pdf_dir = os.path.join(current_app.root_path, 'static', 'pdfs')
        os.makedirs(static_pdf_dir, exist_ok=True)

        # Copy the generated PDF from the pdf directory to static directory
        pdf_dir = os.path.join(current_app.root_path, "pdf")
        source_pdf = os.path.join(pdf_dir, target_filename)
        current_app.logger.info(f"Looking for PDF at: {source_pdf}")
        
        if not os.path.exists(source_pdf):
            current_app.logger.error(f"Generated PDF not found at {source_pdf}")
            
            # Look for the file in different locations
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            current_app.logger.info(f"Available PDFs in directory: {pdf_files}")
            
            if pdf_files:
                # Use the most recently created PDF as a fallback
                pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(pdf_dir, x)), reverse=True)
                target_filename = pdf_files[0]
                source_pdf = os.path.join(pdf_dir, target_filename)
                current_app.logger.info(f"Using most recent PDF instead: {target_filename}")
            else:
                flash(f"Generated PDF not found. Please try again.", "danger")
                return redirect(url_for("pending_approvals"))
            
        static_pdf_path = os.path.join(static_pdf_dir, target_filename)
        shutil.copy2(source_pdf, static_pdf_path)
        current_app.logger.info(f"Copied PDF to: {static_pdf_path}")
        
        # Ensure the approval record has the correct path
        if approval.pdf_path != target_filename:
            approval.pdf_path = target_filename
            db.session.commit()
            current_app.logger.info(f"Updated approval record with path: {target_filename}")
        
        # Return the PDF file directly
        return send_from_directory(
            static_pdf_dir,
            target_filename,
            as_attachment=False,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in generate_pdf_route for approval {approval_id}: {str(e)}")
        flash(f"Error serving PDF: {str(e)}", "danger")
        return redirect(url_for("pending_approvals"))

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
