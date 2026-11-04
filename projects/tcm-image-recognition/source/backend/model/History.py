from datetime import datetime
from extensions import db

class HistoryData(db.Model):
    __tablename__ = 'history_data'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_name = db.Column(db.String(500), nullable=False)  # 图片名称
    image_path = db.Column(db.String(500), nullable=False)  # 图片路径
    subclass_id = db.Column(db.Integer, db.ForeignKey('herb_subclasses.id'), nullable=False)  # 关联小类ID
    confidence = db.Column(db.Float, nullable=False)  # 置信度
    created_by = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'), nullable=True)  # 创建人ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 创建时间

    # 关联关系
    subclass = db.relationship('HerbSubClass', backref='history_data')  # 关联小类
    creator = db.relationship('SysUser', backref=db.backref('created_history', lazy='dynamic'))  # 关联用户

    def __init__(self, image_name, image_path, subclass_id, confidence, created_by):
        self.image_name = image_name
        self.image_path = image_path
        self.subclass_id = subclass_id
        self.confidence = confidence
        self.created_by = created_by
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            'id': self.id,
            'image_name': self.image_name,
            'image_path': self.image_path,
            'subclass_id': self.subclass_id,
            'subclass_name': self.subclass.subclass_name if self.subclass else None,
            'confidence': self.confidence,
            'created_by': self.created_by,
            'creator_name': self.creator.nick_name if self.creator else None,  # 使用SysUser的nick_name字段
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<HistoryData {self.id}: {self.image_name} (Confidence: {self.confidence:.2f})>'
