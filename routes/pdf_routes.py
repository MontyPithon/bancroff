from flask import Blueprint, flash, redirect, url_for, request, session
import subprocess
from datetime import datetime
from models import db, User  # Adjust import as needed, e.g., from .models import db, User

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
    
    # 5. Load the LaTeX template (pdf/approval_template.tex)
    template_path = "pdf/approval_template.tex"
    try:
        with open(template_path, "r") as f:
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
    
    # 7. Write the filled content to pdf/document.tex
    output_tex = "pdf/document.tex"
    try:
        with open(output_tex, "w") as f:
            f.write(filled_template)
    except Exception as e:
        flash(f"Error writing LaTeX file: {e}", "danger")
        return redirect(url_for("index"))
    
    # 8. Call 'make' in the 'pdf' folder to generate document.pdf
    result = subprocess.run(["make"], cwd="pdf")
    if result.returncode != 0:
        flash("Error generating PDF.", "danger")
        return redirect(url_for("index"))
    
    # Optional: You could store the PDF in the database, or serve it to the user here.
    flash("PDF generated successfully!", "success")
    return redirect(url_for("index"))

def register_pdf_routes(app):
    """Attach the pdf_routes blueprint to the Flask app."""
    app.register_blueprint(pdf_routes)
