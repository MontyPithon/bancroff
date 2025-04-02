from flask import render_template, redirect, url_for, flash, request, session
from models import db, User, RequestApproval, ApprovalStep, Request
from utils.auth_helpers import active_required

def setup_approval_routes(app):
    @app.route('/my_requests')
    @active_required
    def my_requests():
        if not session.get("user"):
            return redirect(url_for("login"))
            
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()   
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
         
        requests = current_user.requests
        return render_template('my_requests.html', requests=requests)

    @app.route('/pending_approvals')
    @active_required
    def pending_approvals():
        if not session.get("user"):
            return redirect(url_for("login"))
            
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
            
        if current_user.role.name == 'basic_user':
            flash('You do not have an assigned role for approvals.', 'warning')
            return redirect(url_for('index'))
        
        # Get all requests with their approval statuses
        requests = Request.query.all()
        pending_approvals = []
        
        for request in requests:
            # Get all approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == request.id
            ).order_by(ApprovalStep.step_order).all()
            
            # Find the current pending step
            current_pending = next((a for a in request_approvals if a.status == 'pending'), None)
            
            if current_pending:
                pending_approvals.append({
                    'approval_id': current_pending.id,
                    'request': request,
                    'request_type': request.request_type.name,
                    'requester': request.requester.full_name,
                    'submitted': request.created_at,
                    'step': current_pending.step.name,
                    'approval_status': [{
                        'step': a.step.name,
                        'status': a.status,
                        'approver': a.approver.full_name if a.approver else 'Pending'
                    } for a in request_approvals]
                })
        
        return render_template('pending_approvals.html', pending_approvals=pending_approvals)

    @app.route('/request_approval/<int:approval_id>', methods=['GET', 'POST'])
    @active_required
    def request_approval(approval_id):
        """View and process approval for a specific request"""
        if not session.get("user"):
            return redirect(url_for("login"))
            
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        approval = RequestApproval.query.get(approval_id)
        if not approval:
            flash('Approval request not found.', 'danger')
            return redirect(url_for('pending_approvals'))
            
        if current_user.role_id != approval.step.approver_role_id:
            flash('You do not have permission to approve this request.', 'danger')
            return redirect(url_for('pending_approvals'))
            
        if approval.status != 'pending':
            flash('This request has already been processed.', 'warning')
            return redirect(url_for('pending_approvals'))
        
        if request.method == 'POST':
            action = request.form.get('action')
            comments = request.form.get('comments', '')
            
            if action == 'approve':
                approval.status = 'approved'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                
                # check if this was the last approval step to mark the request as approved
                request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                    RequestApproval.request_id == approval.request_id).order_by(ApprovalStep.step_order).all()
                    
                next_pending = False
                for next_approval in request_approvals:
                    if next_approval.status == 'pending':
                        next_pending = True
                        break
                        
                if not next_pending:
                    approval.request.status = 'approved'
                    flash('Request has been fully approved!', 'success')
                else:
                    flash('Request approved and moved to next approval step!', 'success')
                
                db.session.commit()

            elif action == 'reject':
                approval.status = 'rejected'
                approval.comments = comments
                approval.approver_id = current_user.id
                approval.approved_at = db.func.current_timestamp()
                approval.request.status = 'rejected'
                db.session.commit()
                flash('Request has been rejected.', 'warning')
            
            return redirect(url_for('pending_approvals'))
        
        # GET request
        request_data = approval.request
        form_data = request_data.form_data
        return render_template('request_approval.html', approval=approval, request=request_data, form_data=form_data)

    @app.route('/approval_management')
    @active_required
    def approval_management():
        """View all requests and their approval statuses"""
        if not session.get("user"):
            return redirect(url_for("login"))
            
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
            
        # Check if user has an approval role
        if current_user.role.name not in ['admin', 'advisor', 'chair', 'dean']:
            flash('You do not have permission to view approval management.', 'warning')
            return redirect(url_for('index'))
        
        # Get all requests with their approval statuses
        requests = Request.query.all()
        for request in requests:
            # Get all approval steps for this request
            request_approvals = RequestApproval.query.join(ApprovalStep).filter(
                RequestApproval.request_id == request.id
            ).order_by(ApprovalStep.step_order).all()
            
            # Add approval status information to the request
            request.approval_status = []
            for approval in request_approvals:
                request.approval_status.append({
                    'step': approval.step.name,
                    'status': approval.status,
                    'approver': approval.approver.full_name if approval.approver else 'Pending',
                    'comments': approval.comments
                })
        
        return render_template('approval_management.html', requests=requests) 