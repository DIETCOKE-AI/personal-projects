
from extensions import db

class SysUser(db.Model):
    __tablename__ = 'sys_user'

    user_id = db.Column(db.BigInteger, primary_key=True)
    user_name = db.Column(db.String(30), nullable=False)
    nick_name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(50), default='')
    phonenumber = db.Column(db.String(11), default='')

    def __repr__(self):
        return f'<SysUser {self.user_name}>'
