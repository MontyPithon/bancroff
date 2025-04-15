# pdf_service.py
import subprocess
import os
from datetime import datetime
from flask import current_app
from models import db, RequestApproval, User, ApprovalStep
from .latex_utils import latex_escape

def get_approver_signature(approval):
    """Get the signature path for an approver."""
    if not approval or not approval.approver:
        return None
    return approval.approver.signature_path

def generate_pdf_for_approval(approval_id):
    """
    Generates a PDF with all signatures up to the current approval step.
    """
    try:
        approval = RequestApproval.query.get(approval_id)
        if not approval:
            return None, "Approval record not found."

        request_obj = approval.request
        requester = request_obj.requester

        # Get all approvals for this request up to current step
        approvals = RequestApproval.query.join(ApprovalStep).filter(
            RequestApproval.request_id == request_obj.id,
            ApprovalStep.step_order <= approval.step.step_order
        ).order_by(ApprovalStep.step_order).all()

        # Create necessary directories
        uploads_dir = os.path.join(current_app.root_path, "static", "uploads")
        pdf_dir = os.path.join(current_app.root_path, "pdf")
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(pdf_dir, exist_ok=True)

        # Collect signatures and details
        signatures = {
            'student': {
                'path': requester.signature_path,
                'name': requester.full_name,
                'date': request_obj.created_at.strftime("%Y-%m-%d")
            },
            'advisor': None,
            'chair': None,
            'dean': None
        }

        # Map approvals to their roles and collect signatures
        for app in approvals:
            if app.status != 'approved' or not app.approver:
                continue
                
            role = app.approver.role.name.lower()
            if role in ['advisor', 'chair', 'dean']:
                signatures[role] = {
                    'path': app.approver.signature_path,
                    'name': app.approver.full_name,
                    'date': app.approved_at.strftime("%Y-%m-%d") if app.approved_at else datetime.now().strftime("%Y-%m-%d")
                }

        # Read LaTeX template
        template_path = os.path.join(pdf_dir, "approval_template.tex")
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except Exception as e:
            return None, f"Error reading template: {e}"

        # Replace placeholders
        filled_template = (
            template_content
            .replace("{{requestId}}", str(request_obj.id))
            .replace("{{requestType}}", request_obj.request_type.name)
            .replace("{{requesterName}}", latex_escape(requester.full_name))
            .replace("{{studentSignature}}", signatures['student']['path'] or "default_signature.png")
            .replace("{{studentSignatureDate}}", signatures['student']['date'])
            .replace("{{advisorSignature}}", signatures['advisor']['path'] if signatures['advisor'] else "")
            .replace("{{advisorName}}", latex_escape(signatures['advisor']['name']) if signatures['advisor'] else "")
            .replace("{{advisorSignatureDate}}", signatures['advisor']['date'] if signatures['advisor'] else "")
            .replace("{{chairSignature}}", signatures['chair']['path'] if signatures['chair'] else "")
            .replace("{{chairName}}", latex_escape(signatures['chair']['name']) if signatures['chair'] else "")
            .replace("{{chairSignatureDate}}", signatures['chair']['date'] if signatures['chair'] else "")
            .replace("{{deanSignature}}", signatures['dean']['path'] if signatures['dean'] else "")
            .replace("{{deanName}}", latex_escape(signatures['dean']['name']) if signatures['dean'] else "")
            .replace("{{deanSignatureDate}}", signatures['dean']['date'] if signatures['dean'] else "")
            .replace("{{approvalNote}}", latex_escape(approval.comments or "No comments"))
            .replace("{{date}}", datetime.now().strftime("%Y-%m-%d"))
        )

        # Write filled template
        tex_path = os.path.join(pdf_dir, "document.tex")
        try:
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(filled_template)
        except Exception as e:
            return None, f"Error writing filled LaTeX file: {e}"

        # Copy signatures to PDF directory for LaTeX to find them
        for role, sig_data in signatures.items():
            if sig_data and sig_data['path']:
                src_path = os.path.join(uploads_dir, sig_data['path'])
                if os.path.exists(src_path):
                    try:
                        import shutil
                        shutil.copy2(src_path, os.path.join(pdf_dir, sig_data['path']))
                    except Exception as e:
                        current_app.logger.error(f"Warning: Could not copy signature for {role}: {e}")

        # Run make to compile PDF
        try:
            result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
            if result.returncode != 0:
                error_msg = f"Error generating PDF (pdflatex failed). Error: {result.stderr}"
                current_app.logger.error(error_msg)
                return None, error_msg
        except Exception as e:
            error_msg = f"Subprocess error: {e}"
            current_app.logger.error(error_msg)
            return None, error_msg

        # Clean up copied signatures
        for role, sig_data in signatures.items():
            if sig_data and sig_data['path']:
                try:
                    os.remove(os.path.join(pdf_dir, sig_data['path']))
                except Exception as e:
                    current_app.logger.error(f"Warning: Could not remove temporary signature file for {role}: {e}")

        # Rename and store the generated PDF
        generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
        if not os.path.exists(generated_pdf_path):
            return None, "Generated PDF not found"

        pdf_filename = f"approval_{approval.id}_{int(datetime.now().timestamp())}.pdf"
        final_pdf_path = os.path.join(pdf_dir, pdf_filename)
        os.rename(generated_pdf_path, final_pdf_path)

        # Update approval record
        approval.pdf_path = pdf_filename
        db.session.commit()

        return final_pdf_path, None

    except Exception as e:
        error_msg = f"Unexpected error in generate_pdf_for_approval: {str(e)}"
        current_app.logger.error(error_msg)
        return None, error_msg

def split_full_name(full_name):
    parts = full_name.split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""  # fallback if there's no last name
