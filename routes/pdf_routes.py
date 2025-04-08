# routes/pdf_routes.py

from flask import Blueprint, current_app, send_from_directory, flash, redirect, url_for
import subprocess
import os
import time
from datetime import datetime

# Create a blueprint for pdf-related routes
pdf_bp = Blueprint('pdf_bp', __name__)

@pdf_bp.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """
    Example generic PDF generation route.
    You can adjust this based on your specific needs.
    This example assumes you have a template in the pdf folder named form_template.tex.
    """
    # Dummy implementation (replace with your actual logic)
    # For example, read form data from request.form, fill in the template,
    # run pdflatex via subprocess, and rename the output PDF.
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    template_path = os.path.join(pdf_dir, "form_template.tex")
    
    # Read template
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        flash(f"Error reading template: {e}", "danger")
        return redirect(url_for('index'))
    
    # Replace a placeholder example:
    filled_content = template_content.replace("{{name}}", "John Doe")
    
    # Write to document.tex file
    tex_path = os.path.join(pdf_dir, "document.tex")
    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(filled_content)
    except Exception as e:
        flash(f"Error writing .tex file: {e}", "danger")
        return redirect(url_for('index'))
    
    # Run Makefile (which should compile document.tex to document.pdf)
    try:
        result = subprocess.run(["make"], cwd=pdf_dir, capture_output=True, text=True)
        if result.returncode != 0:
            flash(f"pdflatex error: {result.stderr}", "danger")
            return redirect(url_for('index'))
    except Exception as e:
        flash(f"Subprocess error: {e}", "danger")
        return redirect(url_for('index'))
    
    # Rename generated document.pdf for uniqueness
    generated_pdf_path = os.path.join(pdf_dir, "document.pdf")
    if not os.path.exists(generated_pdf_path):
        flash("Expected PDF was not generated.", "danger")
        return redirect(url_for('index'))
    
    new_filename = f"generated_{int(time.time())}.pdf"
    final_pdf_path = os.path.join(pdf_dir, new_filename)
    os.rename(generated_pdf_path, final_pdf_path)
    
    flash("PDF generated successfully!", "success")
    return redirect(url_for('pdf_bp.download_pdf', filename=new_filename))

@pdf_bp.route('/download_pdf/<filename>', methods=['GET'])
def download_pdf(filename):
    pdf_dir = os.path.join(current_app.root_path, "pdf")
    return send_from_directory(pdf_dir, filename, as_attachment=True)

def register_pdf_routes(app):
    from flask import current_app
    # Create and register your PDF Blueprint here.
    pdf_bp = Blueprint('pdf_bp', __name__)

    @pdf_bp.route('/generate_pdf', methods=['POST'])
    def generate_pdf():
        # ... [Your PDF generation logic here]
        # For now, this is just a placeholder route.
        return "PDF generated", 200

    @pdf_bp.route('/download_pdf/<filename>', methods=['GET'])
    def download_pdf(filename):
        from flask import send_from_directory
        pdf_dir = os.path.join(current_app.root_path, "pdf")
        return send_from_directory(pdf_dir, filename, as_attachment=True)

    app.register_blueprint(pdf_bp)

