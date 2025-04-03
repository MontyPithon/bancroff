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
                
                # process form data 
                form_data = {}
                form_data['iai'] = request.form.getlist('iai[]')
                form_data['reason'] = request.form.get('reason')
                form_data['letter_attached'] = 'letter_attached' in request.form
                form_data['track'] = request.form.get('track')

                if form_data['track'] == 'non_thesis':
                    form_data['non_thesis_hours'] = request.form.get('non_thesis_hours')
                elif form_data['track'] == 'thesis':
                    form_data['thesis_hours'] = request.form.get('thesis_hours')

                form_data['semester'] = request.form.get('semester')
                if form_data['semester'] == 'fall':
                    form_data['year'] = '20' + request.form.get('fall_year', '')
                elif form_data['semester'] == 'spring':
                    form_data['year'] = '20' + request.form.get('spring_year', '')
                
                # max 4 drops
                form_data['courses'] = []
                for i in range(1, 4):
                    course = request.form.get(f'course{i}')
                    if course:
                        form_data['courses'].append(course)

                form_data['remaining_hours'] = request.form.get('remaining_hours')
                form_data['ps_id'] = request.form.get('ps_id')
        
                form_data['signature_date'] = str(date.today())
                form_data['signature_path'] = signature.signature_image_path

                # create request
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
                
                # create entries in approval table set as pending
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
        
        if request.method == 'POST':
            try:
                user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=user_email).first()
                signature = get_user_signature(current_user.id)
                if not signature:
                    flash('Please upload a signature before submitting the form.', 'warning')
                    return redirect(url_for('upload_signature'))

                withdrawal_type = RequestType.query.filter_by(name='Withdrawal').first()
                if not withdrawal_type:
                    flash('Withdrawal form type not found in the database', 'danger')
                    return redirect(url_for('index'))
                if not current_user:
                    flash('User not found. Please log in again.', 'danger')
                    return redirect(url_for('login'))
                
                # Process form data
                form_data = {}
                form_data['myUHID'] = request.form.get('myUHID')
                form_data['college'] = request.form.get('college')
                form_data['planDegree'] = request.form.get('planDegree')
                form_data['address'] = request.form.get('address')
                form_data['phoneNumber'] = request.form.get('phoneNumber')
                form_data['termYear'] = request.form.get('termYear')
                form_data['reason'] = request.form.get('reason')
                form_data['lastDateAttended'] = request.form.get('lastDateAttended')
                form_data['financialAssistance'] = request.form.get('financialAssistance') == 'yes'
                form_data['studentHealthInsurance'] = request.form.get('studentHealthInsurance') == 'yes'
                form_data['campusHousing'] = request.form.get('campusHousing') == 'yes'
                form_data['visaStatus'] = request.form.get('visaStatus') == 'yes'
                form_data['giBillBenefits'] = request.form.get('giBillBenefits') == 'yes'
                form_data['withdrawalType'] = request.form.get('withdrawalType')
                form_data['coursesToWithdraw'] = request.form.get('coursesToWithdraw')
                form_data['additionalComments'] = request.form.get('additionalComments')
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
        return render_template('withdraw_form.html')

    @app.route('/available_forms')
    @active_required
    def available_forms():
        """Display all available request forms"""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        # Get all request types from the database
        form_types = RequestType.query.all()
        
        return render_template('available_forms.html', form_types=form_types)

    # ---------------------------------------------
    # NEW ROUTES FOR EMAIL ALIAS & VERIFICATION OF ENROLLMENT
    # ---------------------------------------------

    @app.route('/email_alias_form', methods=['GET', 'POST'])
    @active_required
    def email_alias_form():
        """Displays and processes the Email Alias form."""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        if request.method == 'POST':
            try:
                user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=user_email).first()
                if not current_user:
                    flash('User not found. Please log in again.', 'danger')
                    return redirect(url_for('login'))

                # If you require a signature for Email Alias too:
                signature = get_user_signature(current_user.id)
                if not signature:
                    flash('Please upload a signature before submitting the form.', 'warning')
                    return redirect(url_for('upload_signature'))

                # Retrieve the request type for Email Alias
                alias_type = RequestType.query.filter_by(name='Email Alias').first()
                if not alias_type:
                    flash('"Email Alias" request type not found. Please ensure you seeded it.', 'danger')
                    return redirect(url_for('my_requests'))

                # Process form data
                form_data = {}
                form_data['alias'] = request.form.get('alias')
                form_data['reason'] = request.form.get('reason', '')
                form_data['submissionDate'] = str(date.today())
                form_data['signature_path'] = signature.signature_image_path

                # Create a new Request object
                new_request = Request(
                    type_id=alias_type.id,
                    requester_id=current_user.id,
                    title='Email Alias Request',
                    form_data=form_data,
                    status='submitted'
                )
                db.session.add(new_request)
                db.session.commit()
                
                # If an approval workflow is defined for Email Alias, create approvals
                workflow = ApprovalWorkflow.query.filter_by(request_type_id=alias_type.id).first()
                if workflow:
                    for step in workflow.steps:
                        approval = RequestApproval(
                            request_id=new_request.id,
                            step_id=step.id,
                            status='pending'
                        )
                        db.session.add(approval)
                    db.session.commit()

                flash('Email Alias request submitted successfully!', 'success')
                return redirect(url_for('my_requests'))

            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while submitting the Email Alias form: {str(e)}', 'danger')
                return redirect(url_for('email_alias_form'))

        # GET request
        return render_template('email_alias_form.html')

    @app.route('/voe_form', methods=['GET', 'POST'])
    @active_required
    def voe_form():
        """Displays and processes the Verification of Enrollment form."""
        if not session.get("user"):
            return redirect(url_for("login"))
        
        if request.method == 'POST':
            try:
                user_email = session['user'].get('preferred_username').lower()
                current_user = User.query.filter_by(email=user_email).first()
                if not current_user:
                    flash('User not found. Please log in again.', 'danger')
                    return redirect(url_for('login'))

                # If signature is also required for this form:
                signature = get_user_signature(current_user.id)
                if not signature:
                    flash('Please upload a signature before submitting the form.', 'warning')
                    return redirect(url_for('upload_signature'))

                # Retrieve the request type for Verification of Enrollment
                voe_type = RequestType.query.filter_by(name='Verification of Enrollment').first()
                if not voe_type:
                    flash('"Verification of Enrollment" request type not found. Please ensure you seeded it.', 'danger')
                    return redirect(url_for('my_requests'))

                # Process form data
                form_data = {}
                form_data['semester'] = request.form.get('semester')
                form_data['studentID'] = request.form.get('studentID')
                form_data['extraInfo'] = request.form.get('extraInfo', '')
                form_data['submissionDate'] = str(date.today())
                form_data['signature_path'] = signature.signature_image_path

                # Create a new Request object
                new_request = Request(
                    type_id=voe_type.id,
                    requester_id=current_user.id,
                    title='Verification of Enrollment Request',
                    form_data=form_data,
                    status='submitted'
                )
                db.session.add(new_request)
                db.session.commit()

                # If an approval workflow is defined for VOE, create approvals
                workflow = ApprovalWorkflow.query.filter_by(request_type_id=voe_type.id).first()
                if workflow:
                    for step in workflow.steps:
                        approval = RequestApproval(
                            request_id=new_request.id,
                            step_id=step.id,
                            status='pending'
                        )
                        db.session.add(approval)
                    db.session.commit()

                flash('Verification of Enrollment form submitted successfully!', 'success')
                return redirect(url_for('my_requests'))

            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while submitting the VOE form: {str(e)}', 'danger')
                return redirect(url_for('voe_form'))
        
        # GET request
        return render_template('verification_of_enrollment_form.html')
