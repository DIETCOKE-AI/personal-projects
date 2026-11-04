from datetime import datetime
from extensions import db

class UserContact(db.Model):
    __tablename__ = 'user_contact'

    user_id = db.Column(db.BigInteger, db.ForeignKey('sys_user.user_id'), primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(20), nullable=False)
    postal_code = db.Column(db.String(20))
    
    # 建立与SysUser表的关系
    user = db.relationship('SysUser', backref=db.backref('contact_info', uselist=False))

    def __init__(self, user_id, address, city, country, postal_code=None):
        self.user_id = user_id
        self.address = address
        self.city = city
        self.country = country
        self.postal_code = postal_code

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'postal_code': self.postal_code
        }

    def __repr__(self):
        return f'<UserContact {self.user_id}>'
