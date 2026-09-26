from datetime import datetime
from app.extensions import db

class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False) # Razón social
    tax_id = db.Column(db.String(50), unique=True, nullable=False) # NIT / Identificación tributaria
    contact_name = db.Column(db.String(120), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    locations = db.relationship('Location', backref='client', lazy=True, cascade='all, delete-orphan')
    contacts = db.relationship('ClientContact', backref='client', lazy=True, cascade='all, delete-orphan')
    assets = db.relationship('Asset', backref='client', lazy=True, cascade='all, delete-orphan')
    licenses = db.relationship('MicrosoftLicense', backref='client', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='client', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Client {self.company_name}>"


class ClientContact(db.Model):
    __tablename__ = 'client_contacts'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tickets = db.relationship('Ticket', backref='contact', lazy=True)

    def __repr__(self):
        return f"<ClientContact {self.name} ({self.email})>"



class Location(db.Model):
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False) # Nombre Sede/Departamento
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    contact_person = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assets = db.relationship('Asset', backref='location', lazy=True)
    tickets = db.relationship('Ticket', backref='location', lazy=True)

    def __repr__(self):
        return f"<Location {self.name} - Client {self.client_id}>"
