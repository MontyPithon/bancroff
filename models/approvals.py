# routes/approvals.py

from flask import Blueprint, render_template, redirect, url_for, flash, request as flask_request, session
from models.request import Request, db
from models.user import User
# If you have roles or other logic, import as needed
# from models.user import Role

approvals_bp = Blueprint('approvals_bp', __name__)

@approvals_bp.route('/requests_dashboard')
def requests_dashboard():
    """
    Displays a list of all requests with their statuses.
    """
    all_requests = Request.query.all()
    return render_template('requests_dashboard.html', requests=all_requests)

@approvals_bp.route('/submit_request/<int:request_id>', methods=['POST'])
def submit_request(request_id):
    """
    Moves a request from 'draft' to 'pending'.
    """
    req = Request.query.get(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for('approvals_bp.requests_dashboard'))

    if req.status == 'draft':
        req.status = 'pending'
        db.session.commit()
        flash(f"Request {req.id} submitted successfully!", "success")
    else:
        flash(f"Cannot submit request {req.id} because it's not in 'draft' state.", "warning")

    return redirect(url_for('approvals_bp.requests_dashboard'))

@approvals_bp.route('/approve_request/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    """
    Moves a request from 'pending' to 'approved'.
    """
    req = Request.query.get(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for('approvals_bp.requests_dashboard'))

    if req.status == 'pending':
        req.status = 'approved'
        db.session.commit()
        flash(f"Request {req.id} approved!", "success")

        # OPTIONAL: Hook your PDF generation here if needed
        # e.g., generate_pdf_for_request(req) 
        # or redirect to a route that does:
        # return redirect(url_for('pdf_routes.generate_pdf', request_id=req.id))
    else:
        flash(f"Cannot approve request {req.id} because it's not in 'pending' state.", "warning")

    return redirect(url_for('approvals_bp.requests_dashboard'))

@approvals_bp.route('/return_request/<int:request_id>', methods=['POST'])
def return_request(request_id):
    """
    Moves a request from 'pending' to 'returned'.
    """
    req = Request.query.get(request_id)
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for('approvals_bp.requests_dashboard'))

    if req.status == 'pending':
        req.status = 'returned'
        db.session.commit()
        flash(f"Request {req.id} returned to requester.", "success")
    else:
        flash(f"Cannot return request {req.id} because it's not in 'pending' state.", "warning")

    return redirect(url_for('approvals_bp.requests_dashboard'))

def setup_approval_routes(app):
    """
    Register the approvals blueprint with the provided Flask app.
    """
    app.register_blueprint(approvals_bp, url_prefix='/approvals')
