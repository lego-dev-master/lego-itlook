from datetime import datetime, date
from app.extensions import db

class MicrosoftLicense(db.Model):
    __tablename__ = 'microsoft_licenses'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    subscription_type = db.Column(db.String(100), nullable=False) # ej: M365 Business Premium, Azure, Windows Server, Office 365 E3
    quantity = db.Column(db.Integer, default=1, nullable=False)
    acquisition_date = db.Column(db.Date, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    assigned_users_count = db.Column(db.Integer, default=0)
    installation_user = db.Column(db.String(100), nullable=True) # Usuario de instalación
    installation_password = db.Column(db.String(100), nullable=True) # Clave
    activation_code = db.Column(db.String(100), nullable=True) # Código de activación
    download_link = db.Column(db.String(200), nullable=True) # Link de descarga
    assigned_user_names = db.Column(db.String(500), nullable=True) # Lista de usuarios que usan esas licencias
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    @property
    def days_until_expiration(self):
        if not self.expiration_date:
            return 999
        today = date.today()
        return (self.expiration_date - today).days

    @property
    def alert_status(self):
        """
        Returns alert urgency:
        - 'expired': Expired (< 0 days)
        - 'critical': <= 5 days (Red)
        - 'warning': <= 15 days (Orange)
        - 'notice': <= 30 days (Yellow)
        - 'active': > 30 days (Green)
        """
        days = self.days_until_expiration
        if days < 0:
            return 'expired'
        elif days <= 5:
            return 'critical'
        elif days <= 15:
            return 'warning'
        elif days <= 30:
            return 'notice'
        return 'active'

    @property
    def status_badge_class(self):
        status_map = {
            'expired': 'bg-dark text-white',
            'critical': 'bg-danger text-white',
            'warning': 'bg-warning text-dark',
            'notice': 'bg-info text-dark',
            'active': 'bg-success text-white'
        }
        return status_map.get(self.alert_status, 'bg-secondary')

    def __repr__(self):
        return f"<MicrosoftLicense {self.subscription_type} - Client {self.client_id}>"
