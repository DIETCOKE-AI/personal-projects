from datetime import datetime
from extensions import db


class SimilarRecord(db.Model):
    __tablename__ = 'similar_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    history_id = db.Column(db.Integer, db.ForeignKey('history_data.id'), nullable=False)  # 关联历史记录ID
    subclass_id = db.Column(db.Integer, db.ForeignKey('herb_subclasses.id'), nullable=False)  # 关联小类ID
    confidence = db.Column(db.Float, nullable=False)  # 置信度（0-1之间）
    created_by = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'), nullable=False)  # 创建人ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # 创建时间

    # 关联关系
    history_data = db.relationship('HistoryData', backref='similar_items')  # 关联主历史记录
    subclass = db.relationship('HerbSubClass')  # 关联药材小类
    creator = db.relationship('SysUser', backref=db.backref('similar_records_created', lazy='dynamic'))  # 关联创建用户

    def __init__(self, history_id, subclass_id, confidence, created_by):
        self.history_id = history_id
        self.subclass_id = subclass_id
        self.confidence = confidence
        self.created_by = created_by

    def to_dict(self, include_relations=True):
        """支持可选的关系数据加载"""
        data = {
            'id': self.id,
            'history_id': self.history_id,
            'subclass_id': self.subclass_id,
            'confidence': round(self.confidence, 4),  # 保留4位小数
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_relations:
            data.update({
                'subclass_name': self.subclass.subclass_name if self.subclass else None,
                'main_class_id': self.subclass.class_id if self.subclass else None,
                'creator_name': self.creator.username if self.creator else None,
                'original_image': self.history_record.image_path if self.history_record else None
            })
        return data

    def __repr__(self):
        return f'<SimilarRecord {self.id} for History:{self.history_id} (Confidence: {self.confidence:.2f})>'
