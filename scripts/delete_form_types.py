from app import create_app
from models import db, RequestType, Request, ApprovalWorkflow, RequestApproval, ApprovalStep

def delete_form_types():
    """Delete Email Alias and VOE form types and their associated data"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the request types
            email_alias_type = RequestType.query.filter_by(name='Email Alias').first()
            voe_type = RequestType.query.filter_by(name='Verification of Enrollment').first()
            
            for request_type in [email_alias_type, voe_type]:
                if request_type:
                    # Get all requests of this type
                    requests = Request.query.filter_by(type_id=request_type.id).all()
                    
                    # Get workflow for this type
                    workflow = ApprovalWorkflow.query.filter_by(request_type_id=request_type.id).first()
                    
                    if workflow:
                        # Delete all approval steps
                        ApprovalStep.query.filter_by(workflow_id=workflow.id).delete()
                        
                        # Delete the workflow
                        db.session.delete(workflow)
                    
                    # For each request
                    for request in requests:
                        # Delete associated approvals
                        RequestApproval.query.filter_by(request_id=request.id).delete()
                        
                        # Delete the request
                        db.session.delete(request)
                    
                    # Delete the request type
                    db.session.delete(request_type)
            
            # Commit all changes
            db.session.commit()
            print("Successfully deleted Email Alias and VOE form types and their associated data")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    delete_form_types() 