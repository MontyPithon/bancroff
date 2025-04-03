from . import db

class ApprovalDocument(db.Model):
    __tablename__ = 'approval_documents'
    id = db.Column(db.Integer, primary_key=True)
    pdf_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
