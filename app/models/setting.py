from datetime import datetime
from app.extensions import db

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    mail_server = db.Column(db.String(150), default='smtp.gmail.com', nullable=False)
    mail_port = db.Column(db.Integer, default=587, nullable=False)
    mail_use_tls = db.Column(db.Boolean, default=True, nullable=False)
    mail_username = db.Column(db.String(150), nullable=True)
    mail_password = db.Column(db.String(250), nullable=True)
    mail_sender_name = db.Column(db.String(100), default='LEGO TICS SAS Soporte', nullable=False)
    mail_sender_email = db.Column(db.String(150), default='soporte@legoitlook.com', nullable=False)
    notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f"<SystemSetting Server={self.mail_server}:{self.mail_port}>"
