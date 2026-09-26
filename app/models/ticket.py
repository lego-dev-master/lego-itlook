from datetime import datetime, timedelta
from app.extensions import db

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Integer
    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(30), unique=True, nullable=False) # e.g. TCK-2026-0001
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('client_contacts.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    priority = db.Column(db.String(20), default='Media', nullable=False) # Baja, Media, Alta, Crítica
    service_type = db.Column(db.String(30), default='Soporte', nullable=False) # Soporte, Mantenimiento, Proyecto
    status = db.Column(db.String(30), default='Abierto', nullable=False) # Abierto, En Proceso, Espera Cliente, Resuelto, Cerrado
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sla_due_at = db.Column(db.DateTime, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    interventions = db.relationship('TicketIntervention', backref='ticket', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def calculate_sla_due(priority, created_time=None):
        if created_time is None:
            created_time = datetime.utcnow()
        hours_map = {
            'Crítica': 2,
            'Alta': 4,
            'Media': 8,
            'Baja': 24
        }
        hours = hours_map.get(priority, 8)
        return created_time + timedelta(hours=hours)

    @property
    def is_sla_breached(self):
        if self.status in ['Resuelto', 'Cerrado']:
            return self.resolved_at and self.resolved_at > self.sla_due_at
        return datetime.utcnow() > self.sla_due_at

    @property
    def priority_badge_class(self):
        pmap = {
            'Crítica': 'bg-danger text-white',
            'Alta': 'bg-warning text-dark',
            'Media': 'bg-info text-dark',
            'Baja': 'bg-secondary text-white'
        }
        return pmap.get(self.priority, 'bg-secondary')

    @property
    def status_badge_class(self):
        smap = {
            'Abierto': 'bg-primary text-white',
            'En Proceso': 'bg-warning text-dark',
            'Espera Cliente': 'bg-info text-dark',
            'Resuelto': 'bg-success text-white',
            'Cerrado': 'bg-dark text-white'
        }
        return smap.get(self.status, 'bg-secondary')

    def __repr__(self):
        return f"<Ticket {self.ticket_code} - {self.priority}>"


class TicketIntervention(db.Model):
    __tablename__ = 'ticket_interventions'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    notes = db.Column(db.Text, nullable=False)
    hours_spent = db.Column(db.Numeric(4, 2), default=0.5)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    attachment_filename = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TicketIntervention {self.id} for Ticket {self.ticket_id}>"
