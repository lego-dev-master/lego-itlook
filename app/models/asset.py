from datetime import datetime
from app.extensions import db

class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)
    internal_code = db.Column(db.String(50), unique=True, nullable=False) # Código interno / Serial
    serial_number = db.Column(db.String(100), nullable=True)
    device_type = db.Column(db.String(50), nullable=False) # Servidor, PC, Laptop, Switch, Router, Impresora, Otro
    brand = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    
    # Specs
    cpu = db.Column(db.String(100), nullable=True)
    ram = db.Column(db.String(50), nullable=True)
    storage = db.Column(db.String(100), nullable=True)
    os_installed = db.Column(db.String(100), nullable=True)
    
    # Status & Assignment
    status = db.Column(db.String(30), default='Operativo', nullable=False) # Operativo, En Mantenimiento, Dado de baja
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    maintenance_logs = db.relationship('MaintenanceLog', backref='asset', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='asset', lazy=True)
    maintenance_items = db.relationship('MaintenanceEventItem', backref='asset', lazy=True)

    @property
    def maintenance_records(self):
        """Bitácora del equipo: ítems de eventos de mantenimiento TERMINADOS.

        La bitácora se alimenta exclusivamente del módulo de mantenimientos
        (req-03, punto 2.3). Devuelve los ítems ordenados por fecha de cierre
        descendente (el más reciente primero).
        """
        from app.models.maintenance import MaintenanceEvent
        items = [it for it in self.maintenance_items
                 if it.event and it.event.status == MaintenanceEvent.STATUS_DONE]
        return sorted(items, key=lambda it: it.event.finished_at or it.event.opened_at, reverse=True)

    def __repr__(self):
        return f"<Asset {self.internal_code} - {self.brand} {self.model}>"


class MaintenanceLog(db.Model):
    __tablename__ = 'maintenance_logs'

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Técnico que realizó el mantenimiento
    log_type = db.Column(db.String(30), nullable=False) # Preventivo, Correctivo
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Numeric(10, 2), default=0.00)
    attachment_filename = db.Column(db.String(255), nullable=True) # Archivo o soporte adjunto (PDF/Imagen)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MaintenanceLog {self.id} for Asset {self.asset_id}>"
