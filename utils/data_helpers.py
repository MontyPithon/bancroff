from faker import Faker
from models import db, User, Role, Permission, RolePermission
from models import RequestType, ApprovalWorkflow, ApprovalStep

def add_fake_data(num_users=5):
    fake = Faker()
    try:
        roles = [
            Role(name='admin', description='Administrator role with full permissions'),
            Role(name='basic_user', description='Regular user role with limited permissions')
        ]
        db.session.add_all(roles)
        db.session.commit()

        permissions = [
            Permission(name='read', description='Read permission'),
            Permission(name='write', description='Write permission'),
            Permission(name='delete', description='Delete permission')
        ]
        db.session.add_all(permissions)
        db.session.commit()
        
        role_permissions = [
            RolePermission(role_id=1, permission_id=1),
            RolePermission(role_id=1, permission_id=2),
            RolePermission(role_id=1, permission_id=3),
            RolePermission(role_id=2, permission_id=1)
        ]
        db.session.add_all(role_permissions)
        db.session.commit()

        for _ in range(num_users):
            fake_user = User(
                email=fake.email(),
                full_name=fake.name(),
                status=fake.random_element(['active', 'deactivated']),
                provider_user_id=fake.uuid4(),
                provider=fake.random_element(['Google', 'Microsoft', 'Yahoo', 'Apple']),
                role_id=2
            )
            db.session.add(fake_user)
        
        db.session.commit()
        print("Fake data added successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.session.rollback()

def add_rcl_data(rcl_form_schema):
    """Add RCL (Reduced Course Load) related data to the database"""
    try:
        # Create RCL request type if it doesn't exist
        rcl_type = RequestType.query.filter_by(name='RCL').first()
        if not rcl_type:
            rcl_type = RequestType(
                name='RCL',
                description='Reduced Course Load request for graduate students',
                form_schema=rcl_form_schema,
                template_doc_path=None
            )
            db.session.add(rcl_type)
            db.session.commit()
            print("RCL request type added")
        
        # Create necessary roles for approval workflow if they don't exist
        advisor_role = Role.query.filter_by(name='advisor').first()
        if not advisor_role:
            advisor_role = Role(
                name='advisor',
                description='Academic Advisor role'
            )
            db.session.add(advisor_role)
        
        chair_role = Role.query.filter_by(name='chair').first()
        if not chair_role:
            chair_role = Role(
                name='chair',
                description='Department Chair role'
            )
            db.session.add(chair_role)
        
        dean_role = Role.query.filter_by(name='dean').first()
        if not dean_role:
            dean_role = Role(
                name='dean',
                description='College Dean role'
            )
            db.session.add(dean_role)
        
        db.session.commit()
        print("RCL roles added")
        
        # Create approval workflow for RCL requests if it doesn't exist
        workflow = ApprovalWorkflow.query.filter_by(
            request_type_id=rcl_type.id, 
            name='RCL Approval'
        ).first()
        
        if not workflow:
            workflow = ApprovalWorkflow(
                request_type_id=rcl_type.id,
                name='RCL Approval',
                description='Approval workflow for Reduced Course Load requests'
            )
            db.session.add(workflow)
            db.session.commit()
            
            # Create approval steps
            steps = [
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=1,
                    approver_role_id=advisor_role.id,
                    name='Academic Advisor Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=2,
                    approver_role_id=chair_role.id,
                    name='Department Chair Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=3,
                    approver_role_id=dean_role.id,
                    name='College Dean Approval'
                )
            ]
            db.session.add_all(steps)
            db.session.commit()
            print("RCL approval workflow and steps added")
        
    except Exception as e:
        print(f"An error occurred while adding RCL data: {e}")
        db.session.rollback()

def add_withdrawal_form_data(withdrawal_form_schema):
    """Add Withdrawal form related data to the database"""
    try:
        # Create Withdrawal request type if it doesn't exist
        withdrawal_type = RequestType.query.filter_by(name='Withdrawal').first()
        if not withdrawal_type:
            withdrawal_type = RequestType(
                name='Withdrawal',
                description='Medical/Administrative Term Withdrawal request',
                form_schema=withdrawal_form_schema,
                template_doc_path=None
            )
            db.session.add(withdrawal_type)
            db.session.commit()
            print("Withdrawal request type added")
        
        # Get or create necessary roles for approval workflow
        advisor_role = Role.query.filter_by(name='advisor').first()
        if not advisor_role:
            advisor_role = Role(
                name='advisor',
                description='Academic Advisor role'
            )
            db.session.add(advisor_role)
        
        chair_role = Role.query.filter_by(name='chair').first()
        if not chair_role:
            chair_role = Role(
                name='chair',
                description='Department Chair role'
            )
            db.session.add(chair_role)
        
        dean_role = Role.query.filter_by(name='dean').first()
        if not dean_role:
            dean_role = Role(
                name='dean',
                description='College Dean role'
            )
            db.session.add(dean_role)
        
        db.session.commit()
        print("Withdrawal roles added/confirmed")
        
        # Create approval workflow for Withdrawal requests if it doesn't exist
        workflow = ApprovalWorkflow.query.filter_by(
            request_type_id=withdrawal_type.id, 
            name='Withdrawal Approval'
        ).first()
        
        if not workflow:
            workflow = ApprovalWorkflow(
                request_type_id=withdrawal_type.id,
                name='Withdrawal Approval',
                description='Approval workflow for Medical/Administrative Term Withdrawal requests'
            )
            db.session.add(workflow)
            db.session.commit()
            
            # Create approval steps - same process for both withdrawal types
            steps = [
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=1,
                    approver_role_id=advisor_role.id,
                    name='Academic Advisor Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=2,
                    approver_role_id=chair_role.id,
                    name='Department Chair Approval'
                ),
                ApprovalStep(
                    workflow_id=workflow.id,
                    step_order=3,
                    approver_role_id=dean_role.id,
                    name='College Dean Final Approval'
                )
            ]
            db.session.add_all(steps)
            db.session.commit()
            print("Withdrawal approval workflow and steps added")
        
    except Exception as e:
        print(f"An error occurred while adding Withdrawal form data: {e}")
        db.session.rollback()

def add_email_alias_voe_data():
    """
    Add two new request types to the database:
      1. Email Alias
      2. Verification of Enrollment

    For now, we won't define a new workflow with steps, but you can do so if needed.
    """
    try:
        # Check if 'Email Alias' already exists
        email_alias_type = RequestType.query.filter_by(name='Email Alias').first()
        if not email_alias_type:
            email_alias_type = RequestType(
                name='Email Alias',
                description='Request to set up or change a university email alias',
                form_schema=None,  # or a JSON schema if you have one
                template_doc_path=None
            )
            db.session.add(email_alias_type)
            db.session.commit()
            print("Email Alias request type added")

        # Check if 'Verification of Enrollment' already exists
        voe_type = RequestType.query.filter_by(name='Verification of Enrollment').first()
        if not voe_type:
            voe_type = RequestType(
                name='Verification of Enrollment',
                description='Request for official enrollment verification',
                form_schema=None,  # or a JSON schema if needed
                template_doc_path=None
            )
            db.session.add(voe_type)
            db.session.commit()
            print("Verification of Enrollment request type added")


    except Exception as e:
        print(f"An error occurred while adding Email Alias & VOE data: {e}")
        db.session.rollback()

def initialize_database(rcl_form_schema, withdrawal_form_schema):
    """Initialize the database with necessary data"""
    add_fake_data()
    add_rcl_data(rcl_form_schema)
    add_withdrawal_form_data(withdrawal_form_schema)
    add_email_alias_voe_data()  # <-- call your new function here
