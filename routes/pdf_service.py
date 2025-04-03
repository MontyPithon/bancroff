# pdf_service.py
import subprocess
import os
from datetime import datetime
from flask import current_app
from models import db
from models.request import RequestApproval
from .latex_utils import latex_escape  # optional, if you want to escape LaTeX

def generate_pdf_for_approval(approval_id):
    """
    Fills a LaTeX template using data from RequestApproval + the parent Request + the user’s signature,
    runs `make` to generate the PDF, and stores or returns the path to the resulting file.
    """
    approval = RequestApproval.query.get(approval_id)
    if not approval:
        return None, "Approval record not found."

    request_obj = approval.request
    requester = request_obj.requester  # the user who created the request
    signature_path = requester.signature_path or "default_signature.png"

    # 1. Collect placeholders
    first_name, last_name = split_full_name(requester.full_name)
    approval_note = approval.comments or "No comments"
    current_date = datetime.now().strftime("%Y-%m-%d")

    # 2. Read LaTeX template
    template_path = os.path.join(current_app.root_path, "pdf", "approval_template.tex")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        return None, f"Error reading template: {e}"

    # 3. Replace placeholders (escape if needed)
    filled_template = (
        template_content
        .replace("{{firstName}}", first_name)
        .replace("{{lastName}}", last_name)
        .replace("{{approvalNote}}", approval_note)
        .replace("{{date}}", current_date)
        .replace("{{signatureFilename}}", signature_path)
    )

    # 4. Write out the filled LaTeX file
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        return None, f"Error writing filled LaTeX file: {e}"

    # 5. Run `make` to compile the PDF
    try:
        result = subprocess.run(["make"], cwd=pdf_dir)
        if result.returncode != 0:
            return None, "Error generating PDF (pdflatex failed)."
    except Exception as e:
        return None, f"Subprocess error: {e}"

    # 6. At this point, 'document.pdf' should be in the `pdf` folder
    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")

    # 7. (Optional) Store the PDF path in the approval or write to DB as binary
    # Here, we store the path in `approval.pdf_path` for tracking
    pdf_filename = f"approval_{approval.id}_{int(datetime.now().timestamp())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, pdf_filename)
    os.rename(generated_pdf_path, final_pdf_path)

    approval.pdf_path = pdf_filename
    db.session.commit()

    return final_pdf_path, None

def split_full_name(full_name):
    parts = full_name.split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""  # fallback if there's no last name
