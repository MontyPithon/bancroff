from .user import db, User, Role

class RequestType(db.Model):
    __tablename__ = 'request_types'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    form_schema = db.Column(db.JSON, nullable=True)
    template_doc_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    requests = db.relationship('Request', backref='request_type', lazy=True)
    workflows = db.relationship('ApprovalWorkflow', backref='request_type', lazy=True)

class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id = db.Column(db.Integer, db.ForeignKey('request_types.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    form_data = db.Column(db.JSON)
    status = db.Column(db.String(50), default='draft')
    final_document_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())
    requester = db.relationship('User', backref='requests')
    approvals = db.relationship('RequestApproval', backref='request', lazy=True)

    @property
    def latest_approval(self):
        """Get the most recent approval for this request."""
        from sqlalchemy import desc
        return (RequestApproval.query
                .join(ApprovalStep)
                .filter(RequestApproval.request_id == self.id)
                .order_by(desc(ApprovalStep.step_order))
                .first())

class ApprovalWorkflow(db.Model):
    __tablename__ = 'approval_workflows'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_type_id = db.Column(db.Integer, db.ForeignKey('request_types.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    steps = db.relationship('ApprovalStep', backref='workflow', lazy=True, order_by='ApprovalStep.step_order')

class ApprovalStep(db.Model):
    __tablename__ = 'approval_steps'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('approval_workflows.id'), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    approver_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    approver_role = db.relationship('Role')
    approvals = db.relationship('RequestApproval', backref='step', lazy=True)

class RequestApproval(db.Model):
    __tablename__ = 'request_approvals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey('approval_steps.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')
    comments = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    pdf_path = db.Column(db.String(255), nullable=True) 
    approver = db.relationship('User', backref='approvals') 