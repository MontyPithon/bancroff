from flask import render_template, redirect, url_for, flash, request, session
from models import db, User, RequestType, Request, ApprovalWorkflow, RequestApproval
from utils.auth_helpers import active_required, get_user_signature
from datetime import date

def setup_form_routes(app):
    @app.route('/rcl_form', methods=['GET', 'POST'])
    @active_required
    def rcl_form():
        if not session.get("user"):
            return redirect(url_for("login"))
        
        if request.method == 'POST':
            try:
                user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=user_email).first()
                signature = get_user_signature(current_user.id)
                if not signature:
                    flash('Please upload a signature before submitting the form.', 'warning')
                    return redirect(url_for('upload_signature'))

                rcl_type = RequestType.query.filter_by(name='RCL').first()
                if not rcl_type:
                    flash('RCL form type not found in the database', 'danger')
                    return redirect(url_for('index'))            
                if not current_user:
                    flash('User not found. Please log in again.', 'danger')
                    return redirect(url_for('login'))
                
                # Process form data
                form_data = {}
                
                # Process Initial Adjustment Issues
                form_data['iai'] = request.form.getlist('iai[]')
                
                # Process reason (ICLP or medical)
                form_data['reason'] = request.form.get('reason')
                
                # Process letter attachment
                form_data['letter_attached'] = 'letter_attached' in request.form
                
                # Process semester and year
                form_data['semester'] = request.form.get('semester')
                if form_data['semester'] == 'fall':
                    form_data['year'] = '20' + request.form.get('fall_year', '')
                elif form_data['semester'] == 'spring':
                    form_data['year'] = '20' + request.form.get('spring_year', '')
                
                # Process courses
                form_data['courses'] = []
                for i in range(1, 4):
                    course = request.form.get(f'course{i}')
                    if course:
                        form_data['courses'].append(course)
                
                # Process remaining hours
                form_data['remaining_hours'] = request.form.get('remaining_hours')
                
                # Process PS ID
                form_data['ps_id'] = request.form.get('ps_id')
                
                # Add signature info
                form_data['signature_date'] = str(date.today())
                form_data['signature_path'] = signature.signature_image_path
                
                # Format reason for PDF
                reason_text = []
                if form_data['iai']:
                    reason_text.append("Initial Adjustment Issues: " + ", ".join(form_data['iai']))
                if form_data['reason'] == 'iclp':
                    reason_text.append("Improper Course Level Placement")
                elif form_data['reason'] == 'medical':
                    reason_text.append("Medical Reason")
                form_data['formatted_reason'] = "\n".join(reason_text)
                
                # Create request
                semester_info = f"{form_data['semester']} {form_data['year']}"
                new_request = Request(
                    type_id=rcl_type.id,
                    requester_id=current_user.id,
                    title=f"RCL Request - {semester_info}",
                    form_data=form_data,
                    status='submitted' 
                )
                db.session.add(new_request)
                db.session.commit()
                
                # Create entries in approval table set as pending
                workflow = ApprovalWorkflow.query.filter_by(request_type_id=rcl_type.id).first()
                if workflow:
                    for step in workflow.steps:
                        approval = RequestApproval(
                            request_id=new_request.id,
                            step_id=step.id,
                            status='pending'
                        )
                        db.session.add(approval)
                    db.session.commit()
                    flash('RCL Form submitted successfully and sent for approval!', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while submitting the RCL form: {str(e)}', 'danger')
                return redirect(url_for('rcl_form'))
        
        # GET request
        return render_template('rcl_form.html')

    @app.route('/withdrawal_form', methods=['GET', 'POST'])
    @active_required
    def withdrawal_form():
        if not session.get("user"):
            return redirect(url_for("login"))
        
        # Get user's signature for both GET and POST requests
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        signature = get_user_signature(current_user.id)
        
        if request.method == 'POST':
            try:
                if not signature:
                    flash('Please upload a signature before submitting the form.', 'warning')
                    return redirect(url_for('upload_signature'))

                withdrawal_type = RequestType.query.filter_by(name='Withdrawal').first()
                if not withdrawal_type:
                    flash('Withdrawal form type not found in the database', 'danger')
                    return redirect(url_for('index'))
                
                # Process form data
                form_data = {}
                form_data['myUHID'] = request.form.get('myUHID', '')
                form_data['college'] = request.form.get('college', '')
                form_data['planDegree'] = request.form.get('planDegree', '')
                form_data['address'] = request.form.get('address', '')
                form_data['phoneNumber'] = request.form.get('phoneNumber', '')
                form_data['termYear'] = request.form.get('termYear', '')
                form_data['reason'] = request.form.get('reason', '')
                form_data['lastDateAttended'] = request.form.get('lastDateAttended', '')
                form_data['financialAssistance'] = request.form.get('financialAssistance') == 'yes'
                form_data['studentHealthInsurance'] = request.form.get('studentHealthInsurance') == 'yes'
                form_data['campusHousing'] = request.form.get('campusHousing') == 'yes'
                form_data['visaStatus'] = request.form.get('visaStatus') == 'yes'
                form_data['giBillBenefits'] = request.form.get('giBillBenefits') == 'yes'
                form_data['withdrawalType'] = request.form.get('withdrawalType', '')
                form_data['coursesToWithdraw'] = request.form.get('coursesToWithdraw', '')
                form_data['additionalComments'] = request.form.get('additionalComments', '')
                form_data['signature_path'] = signature.signature_image_path
                form_data['submissionDate'] = str(date.today())
                    
                # create request
                new_request = Request(
                    type_id=withdrawal_type.id,
                    requester_id=current_user.id,
                    title=f"Withdrawal Request - {form_data['termYear']}",
                    form_data=form_data,
                    status='submitted'
                )
                db.session.add(new_request)
                db.session.commit()
                
                # create entries in approval table set as pending
                workflow = ApprovalWorkflow.query.filter_by(request_type_id=withdrawal_type.id).first()
                if workflow:
                    for step in workflow.steps:
                        approval = RequestApproval(
                            request_id=new_request.id,
                            step_id=step.id,
                            status='pending'
                        )
                        db.session.add(approval)
                    
                    db.session.commit()
                    flash('Withdrawal Form submitted successfully and sent for approval!', 'success')
                return redirect(url_for('my_requests'))
                
            except Exception as e:
                db.session.rollback()
                print(f"ERROR processing withdrawal form: {str(e)}")
                import traceback
                traceback.print_exc()
                flash(f'An error occurred while submitting the withdrawal form: {str(e)}', 'danger')
                return redirect(url_for('withdrawal_form'))
        
        # GET request
        return render_template('withdraw_form.html', signature=signature)

    @app.route('/available_forms')
    @active_required
    def available_forms():
        """Display all available request forms"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        # Get all request types from the database
        form_types = RequestType.query.filter(RequestType.name.in_(['RCL', 'Withdrawal'])).all()
        
        return render_template('available_forms.html', form_types=form_types)

    @app.route('/delete_request/<int:request_id>', methods=['POST'])
    @active_required
    def delete_request(request_id):
        """Delete a request and its associated approvals."""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        user_email = session['user'].get('preferred_username').lower()
        current_user = User.query.filter_by(email=user_email).first()
        
        if not current_user:
            flash('User not found. Please log in again.', 'danger')
            return redirect(url_for('login'))
        
        request_obj = Request.query.get_or_404(request_id)
        
        # Check if the user owns this request or is an admin
        if request_obj.requester_id != current_user.id and current_user.role.name != 'admin':
            flash('You do not have permission to delete this request.', 'danger')
            return redirect(url_for('my_requests'))
        
        # Check if the request is in a state that allows deletion
        if request_obj.status not in ['draft', 'returned', 'rejected']:
            flash('Only draft, returned, or rejected requests can be deleted.', 'warning')
            return redirect(url_for('my_requests'))
        
        try:
            # Delete associated approvals first
            RequestApproval.query.filter_by(request_id=request_id).delete()
            
            # Delete the request
            db.session.delete(request_obj)
            db.session.commit()
            
            flash('Request deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting request: {str(e)}', 'danger')
        
        return redirect(url_for('my_requests'))
