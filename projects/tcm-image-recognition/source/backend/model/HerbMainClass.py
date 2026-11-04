from datetime import datetime
from extensions import db

class HerbMainClass(db.Model):
    __tablename__ = 'herb_mainclasses'

    id = db.Column(db.Integer, primary_key=True, nullable=False) # 大类id
    class_name = db.Column(db.String(50), nullable=False) # 大类名称
    model_path = db.Column(db.String(255), nullable=False) # 模型路径

    # Timestamps (可选添加)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, id, class_name, model_path,
                 zhejiang_pao_english_name=None, pharmacopoeia_english_name=None):
        self.id = id
        self.class_name = class_name
        self.model_path = model_path

    def to_dict(self):
        return {
            'class_id': self.id,
            'class_name': self.class_name,
            'model_path': self.model_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<HerbMainClass {self.id} - {self.class_name}>'
