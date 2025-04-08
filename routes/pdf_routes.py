from flask import Blueprint, request, send_file, flash, redirect, url_for, render_template, current_app
import os
from datetime import datetime
from models import db, RequestApproval
import subprocess

pdf_bp = Blueprint('pdf', __name__)

def register_pdf_routes(app):
    app.register_blueprint(pdf_bp)

@pdf_bp.route('/generate_pdf/<int:approval_id>', methods=['GET'])
def generate_pdf_route(approval_id):
    """
    Route to generate a PDF for a given approval.
    """
    approval = RequestApproval.query.get(approval_id)
    if not approval:
        flash("Approval record not found.", "danger")
        return redirect(url_for("my_requests"))

    pdf_path, error = generate_pdf_for_approval(approval_id)
    if error:
        flash(f"PDF generation failed: {error}", "danger")
        return redirect(url_for("my_requests"))

    flash("PDF generated successfully!", "success")
    return send_file(pdf_path, as_attachment=True)

def generate_pdf_for_approval(approval_id):
    approval = RequestApproval.query.get(approval_id)
    if not approval:
        return None, "Approval not found."

    request_obj = approval.request
    requester = request_obj.requester

    signature_path = requester.signature_path or "default_signature.png"
    full_name = requester.full_name or "Unknown"
    names = full_name.split(None, 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    comments = approval.comments or "No comments"
    current_date = datetime.now().strftime("%Y-%m-%d")

    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_file = os.path.join(pdf_dir, f"{request_obj.request_type.name.lower()}_template.tex")

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            tex = f.read()
    except Exception as e:
        return None, f"Error reading {request_obj.request_type.name} template: {e}"

    tex = tex.replace("{{firstName}}", first_name)
    tex = tex.replace("{{lastName}}", last_name)
    tex = tex.replace("{{approvalNote}}", comments)
    tex = tex.replace("{{date}}", current_date)
    tex = tex.replace("{{signatureFilename}}", signature_path)

    tex_output = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_output, "w", encoding="utf-8") as f:
            f.write(tex)
    except Exception as e:
        return None, f"Error writing LaTeX file: {e}"

    try:
        subprocess.run(["make"], cwd=pdf_dir, check=True)
    except Exception as e:
        return None, f"Error generating PDF with LaTeX: {e}"

    pdf_file = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(pdf_file):
        return None, "PDF was not created."

    final_path = os.path.join(pdf_dir, f"approval_{approval_id}_{int(datetime.now().timestamp())}.pdf")
    os.rename(pdf_file, final_path)

    approval.pdf_path = os.path.basename(final_path)
    db.session.commit()

    return final_path, None
