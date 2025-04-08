from flask import Blueprint, request, redirect, url_for, flash, current_app, send_from_directory
import subprocess
import os
import time
from datetime import datetime

pdf_routes = Blueprint('pdf_routes', __name__)

@pdf_routes.route('/generate_pdf', methods=['POST'])
def generate_pdf_route():
    """
    This route handles PDF generation from a filled form.
    It:
    1. Receives form data (e.g., name, email, message, and signature filename).
    2. Substitutes the data into a LaTeX template (form_template.tex) located in the pdf/ folder.
    3. Writes the filled template to document.tex.
    4. Calls 'make' (which runs pdflatex) to compile document.tex into document.pdf.
    5. Renames the generated document.pdf to a unique filename.
    6. Redirects to a download route.
    """
    # Extract data from the submitted form
    name = request.form.get('name', 'Unknown')
    email = request.form.get('email', 'unknown@example.com')
    message = request.form.get('message', 'No message provided.')
    signature = request.form.get('signature', 'default_signature.png')
    submission_date = datetime.now().strftime("%Y-%m-%d")
    
    # Prepare a data dictionary for substitution in the template
    data = {
        "name": name,
        "email": email,
        "message": message,
        "date": submission_date,
        "signature": signature  # This should point to an image file path
    }
    
    # Set the path to the pdf folder (assumed to be at current_app.root_path/pdf)
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "form_template.tex")
    
    # Read the LaTeX template
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        flash(f"Error reading LaTeX template: {e}", "danger")
        return redirect(url_for('index'))
    
    # Replace placeholders in the template
    filled_template = template_content
    for key, value in data.items():
        # Replace placeholders like {{name}} with their corresponding values
        filled_template = filled_template.replace("{{" + key + "}}", value)
    
    # Write the filled template into a temporary .tex file (document.tex)
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_template)
    except Exception as e:
        flash(f"Error writing LaTeX file: {e}", "danger")
        return redirect(url_for('index'))
    
    # Run 'make' to compile the PDF using the Makefile in the pdf folder
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            flash(f"pdflatex failed: {result.stderr}", "danger")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Subprocess error: {e}", "danger")
        return redirect(url_for('index'))
    
    # The Makefile should generate 'document.pdf'
    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        flash("Expected PDF was not generated.", "danger")
        return redirect(url_for('index'))
    
    # Rename the generated PDF for uniqueness (e.g., form_1625481634.pdf)
    new_filename = f"form_{int(time.time())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)
    
    flash("PDF generated successfully!", "success")
    # Redirect to the download route so the user can fetch the generated PDF
    return redirect(url_for('pdf_routes.download_pdf', filename=new_filename))


@pdf_routes.route('/download_pdf/<filename>', methods=['GET'])
def download_pdf(filename):
    """
    This route allows users to download the generated PDF.
    """
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    return send_from_directory(pdf_dir, filename, as_attachment=True)

