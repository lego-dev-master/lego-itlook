from datetime import datetime
from app.extensions import db


class MaintenanceEvent(db.Model):
    """Evento de mantenimiento físico de equipos (preventivo o correctivo).

    Un evento pertenece a un cliente y puede agrupar uno o muchos equipos
    del mismo cliente (ver MaintenanceEventItem).
    """
    __tablename__ = 'maintenance_events'

    id = db.Column(db.Integer, primary_key=True)  # Id incremental
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Técnico responsable

    # Tipo de mantenimiento asociado al evento
    maintenance_type = db.Column(db.String(30), default='Preventivo', nullable=False)

    # Abierto | En elaboración | Terminado
    status = db.Column(db.String(30), default='Abierto', nullable=False)

    # Observaciones del técnico
    observations = db.Column(db.Text, nullable=True)

    # Fecha y hora de apertura / terminación
    opened_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('MaintenanceEventItem', backref='event',
                            lazy=True, cascade='all, delete-orphan')

    STATUS_OPEN = 'Abierto'
    STATUS_IN_PROGRESS = 'En elaboración'
    STATUS_DONE = 'Terminado'
    STATUS_CHOICES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]

    @property
    def status_badge_class(self):
        smap = {
            'Abierto': 'bg-primary text-white',
            'En elaboración': 'bg-warning text-dark',
            'Terminado': 'bg-success text-white',
        }
        return smap.get(self.status, 'bg-secondary')

    @property
    def type_badge_class(self):
        return 'bg-info text-dark' if self.maintenance_type == 'Preventivo' else 'bg-warning text-dark'

    @property
    def is_finished(self):
        return self.status == self.STATUS_DONE

    def __repr__(self):
        return f"<MaintenanceEvent {self.id} - {self.status}>"


class MaintenanceEventItem(db.Model):
    """Equipo incluido en un evento de mantenimiento, con fotos antes/después."""
    __tablename__ = 'maintenance_event_items'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('maintenance_events.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)

    # Observaciones por equipo (opcional)
    notes = db.Column(db.Text, nullable=True)

    # Fotos opcionales: antes y después del mantenimiento
    photo_before = db.Column(db.String(255), nullable=True)
    photo_after = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MaintenanceEventItem {self.id} event={self.event_id} asset={self.asset_id}>"
