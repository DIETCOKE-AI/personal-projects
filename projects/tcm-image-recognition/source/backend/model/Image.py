from datetime import datetime

from extensions import db


class Image(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    chinese_name = db.Column(db.String(255), nullable=False)  # Using snake_case for Python
    latin_name = db.Column(db.String(255), nullable=False)
    standard = db.Column(db.String(255), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    uploaded_by = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship (if you want to access the user who uploaded the image)
    uploader = db.relationship('SysUser', backref='images')

    def __init__(self, filename, url, chinese_name, latin_name, standard, confidence, uploaded_by, uploaded_at=None):
        self.filename = filename
        self.url = url
        self.chinese_name = chinese_name
        self.latin_name = latin_name
        self.standard = standard
        self.confidence = confidence
        self.uploaded_by = uploaded_by
        self.uploaded_at = uploaded_at if uploaded_at else datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'url': self.url,
            'chinese_name': self.chinese_name,
            'latin_name': self.latin_name,
            'standard': self.standard,
            'confidence': self.confidence,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Image {self.filename}>'
