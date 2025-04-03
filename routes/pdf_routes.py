from flask import Blueprint, flash, redirect, url_for, request, session
import subprocess
from datetime import datetime
from models import ApprovalDocument, User, db

pdf_routes = Blueprint('pdf_routes', __name__)

@pdf_routes.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """
    Generate a PDF from an approval form submission and store it in the database.
    Expects a form field 'approval_note'. Uses session user data to populate the template.
    """
    # 1. Extract the approval note from the form data.
    approval_note = request.form.get('approval_note', 'No approval note provided.')
    
    # 2. Retrieve user information from the session.
    user_info = session.get("user", {})
    full_name = user_info.get("name", "Unknown User")
    names = full_name.split(" ", 1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""
    
    # 3. Get the current date.
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 4. Retrieve the signature image path from the database.
    user_db = User.query.filter_by(email=user_info.get("preferred_username", "").lower()).first()
    signature_path = user_db.signature_path if user_db and user_db.signature_path else "default_signature.png"
    
    # 5. Load the LaTeX template from the pdf folder.
    template_path = "pdf/approval_template.tex"
    try:
        with open(template_path, "r") as f:
            template = f.read()
    except Exception as e:
        flash("Error reading LaTeX template: " + str(e), "danger")
        return redirect(url_for("index"))
    
    # 6. Replace placeholders in the template with actual data.
    filled_template = (
        template.replace("{{firstName}}", first_name)
                .replace("{{lastName}}", last_name)
                .replace("{{approvalNote}}", approval_note)
                .replace("{{date}}", current_date)
                .replace("{{signatureFilename}}", signature_path)
    )
    
    # 7. Save the filled template as document.tex in the pdf folder.
    output_tex_path = "pdf/document.tex"
    try:
        with open(output_tex_path, "w") as f:
            f.write(filled_template)
    except Exception as e:
        flash("Error writing LaTeX file: " + str(e), "danger")
        return redirect(url_for("index"))
    
    # 8. Execute the Makefile to compile document.tex into a PDF.
    result = subprocess.run(["make"], cwd="pdf")
    if result.returncode != 0:
        flash("Error generating PDF.", "danger")
        return redirect(url_for("index"))
    
    # 9. Read the generated PDF file in binary mode.
    pdf_file_path = "pdf/document.pdf"
    try:
        with open(pdf_file_path, "rb") as f:
            pdf_data = f.read()
    except Exception as e:
        flash("Error reading generated PDF: " + str(e), "danger")
        return redirect(url_for("index"))
    
    # 10. Save the PDF data to the database.
    try:
        new_doc = ApprovalDocument(pdf_data=pdf_data)
        db.session.add(new_doc)
        db.session.commit()
        flash("PDF generated and saved successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error saving PDF to database: " + str(e), "danger")
    
    return redirect(url_for("index"))

def register_pdf_routes(app):
    """Register the PDF generation routes with the Flask application."""
    app.register_blueprint(pdf_routes)

