import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date, timedelta

from app import create_app
from app.extensions import db
from app.models import User, Client, Location, ClientContact, Asset, MaintenanceLog, MicrosoftLicense, Ticket, TicketIntervention, SystemSetting

from app.services.license_notifier import check_and_notify_license_expirations

@pytest.fixture
def app():
    app = create_app('test')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_authentication(app):
    with app.app_context():
        user = User(name='Test Tech', email='tech@test.com', role='tech')
        user.set_password('Secret123!')
        db.session.add(user)
        db.session.commit()

        fetched_user = User.query.filter_by(email='tech@test.com').first()
        assert fetched_user is not None
        assert fetched_user.check_password('Secret123!') is True
        assert fetched_user.check_password('WrongPass') is False
        assert fetched_user.is_admin is False

def test_client_and_location_creation(app):
    with app.app_context():
        cli = Client(
            company_name='Empresa Prueba SAS',
            tax_id='999.888.777-1',
            contact_name='Juan Pérez',
            contact_email='juan@prueba.com',
            contact_phone='3001112233',
            address='Calle 123'
        )
        db.session.add(cli)
        db.session.commit()

        loc = Location(client_id=cli.id, name='Sede Norte', city='Bogotá')
        db.session.add(loc)
        db.session.commit()

        assert len(cli.locations) == 1
        assert cli.locations[0].name == 'Sede Norte'

def test_asset_and_maintenance(app):
    with app.app_context():
        user = User(name='Tech 1', email='t1@test.com', role='tech')
        user.set_password('pass')
        cli = Client(company_name='Cli Asset', tax_id='12345', contact_name='A', contact_email='a@a.com', contact_phone='123')
        db.session.add_all([user, cli])
        db.session.commit()

        asset = Asset(
            internal_code='EQ-TEST-001',
            device_type='Servidor',
            brand='Dell',
            model='PowerEdge',
            status='Operativo',
            client_id=cli.id
        )
        db.session.add(asset)
        db.session.commit()

        maint = MaintenanceLog(
            asset_id=asset.id,
            user_id=user.id,
            log_type='Preventivo',
            description='Limpieza de polvo y revisión de RAM',
            cost=50.0
        )
        db.session.add(maint)
        db.session.commit()

        assert len(asset.maintenance_logs) == 1
        assert asset.maintenance_logs[0].log_type == 'Preventivo'

def test_license_expiration_alerts(app):
    with app.app_context():
        admin = User(name='Admin', email='admin@test.com', role='admin')
        admin.set_password('admin')
        cli = Client(company_name='Cli Lic', tax_id='777', contact_name='B', contact_email='b@b.com', contact_phone='123')
        db.session.add_all([admin, cli])
        db.session.commit()

        today = date.today()
        lic_critical = MicrosoftLicense(
            client_id=cli.id,
            subscription_type='M365 Business Premium',
            quantity=10,
            acquisition_date=today - timedelta(days=360),
            expiration_date=today + timedelta(days=5) # 5 days left => critical
        )
        lic_active = MicrosoftLicense(
            client_id=cli.id,
            subscription_type='Azure Plan',
            quantity=1,
            acquisition_date=today - timedelta(days=100),
            expiration_date=today + timedelta(days=90) # 90 days left => active
        )
        db.session.add_all([lic_critical, lic_active])
        db.session.commit()

        assert lic_critical.alert_status == 'critical'
        assert lic_active.alert_status == 'active'

        alerts = check_and_notify_license_expirations()
        assert len(alerts) >= 1
        assert alerts[0]['subscription'] == 'M365 Business Premium'

def test_license_rf07_fields(app):
    with app.app_context():
        cli = Client(company_name='Cli RF07', tax_id='999000', contact_name='X', contact_email='x@x.com', contact_phone='123')
        db.session.add(cli)
        db.session.commit()

        today = date.today()
        lic = MicrosoftLicense(
            client_id=cli.id,
            subscription_type='Office 365 E3',
            quantity=5,
            acquisition_date=today,
            expiration_date=today + timedelta(days=365),
            installation_user='admin@tenant.com',
            installation_password='Password123!',
            activation_code='AAAAA-BBBBB-CCCCC-DDDDD-EEEEE',
            download_link='https://setup.office.com',
            assigned_user_names='Juan Pérez, María Gómez'
        )
        db.session.add(lic)
        db.session.commit()

        fetched = MicrosoftLicense.query.filter_by(subscription_type='Office 365 E3').first()
        assert fetched.installation_user == 'admin@tenant.com'
        assert fetched.installation_password == 'Password123!'
        assert fetched.activation_code == 'AAAAA-BBBBB-CCCCC-DDDDD-EEEEE'
        assert fetched.download_link == 'https://setup.office.com'
        assert fetched.assigned_user_names == 'Juan Pérez, María Gómez'

def test_license_excel_export(client, app):
    with app.app_context():
        user = User(name='Admin Export', email='admin_export@test.com', role='admin')
        user.set_password('pass')
        cli = Client(company_name='Empresa Export SAS', tax_id='123456789', contact_name='Cont', contact_email='c@exp.com', contact_phone='123')
        db.session.add_all([user, cli])
        db.session.commit()

        today = date.today()
        lic = MicrosoftLicense(
            client_id=cli.id,
            subscription_type='M365 Business Standard',
            quantity=15,
            acquisition_date=today,
            expiration_date=today + timedelta(days=180),
            installation_user='admin@empresaexport.com',
            installation_password='SecretPassword123',
            activation_code='EXCEL-TEST-CODE-12345',
            download_link='https://setup.office.com',
            assigned_user_names='Usuario 1, Usuario 2',
            notes='Licencia adquirida para departamento TI'
        )
        db.session.add(lic)
        db.session.commit()

        client.post('/login', data={'email': 'admin_export@test.com', 'password': 'pass'}, follow_redirects=True)

        response = client.get('/licenses/export/excel')
        assert response.status_code == 200
        assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'reporte_licencias_' in response.headers.get('Content-Disposition', '')



def test_ticket_sla_calculation(app):
    with app.app_context():
        cli = Client(company_name='Cli Ticket', tax_id='888', contact_name='C', contact_email='c@c.com', contact_phone='123')
        db.session.add(cli)
        db.session.commit()

        start_time = datetime.utcnow()
        tck_critical = Ticket(
            ticket_code='TCK-2026-TEST1',
            client_id=cli.id,
            title='Caída de Servidor Principal',
            description='Urgente',
            priority='Crítica',
            created_at=start_time,
            sla_due_at=Ticket.calculate_sla_due('Crítica', start_time)
        )
        db.session.add(tck_critical)
        db.session.commit()

        expected_due = start_time + timedelta(hours=2)
        assert abs((tck_critical.sla_due_at - expected_due).total_seconds()) < 5
        assert tck_critical.is_sla_breached is False

def test_dashboard_rendering(client, app):
    with app.app_context():
        user = User(name='Admin User', email='admin@test.com', role='admin')
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

        # Login
        client.post('/login', data={'email': 'admin@test.com', 'password': 'pass'}, follow_redirects=True)
        response = client.get('/')
        assert response.status_code == 200
        assert b'Panel de Control Operativo' in response.data

def test_client_contacts_and_ticket_notifications(app):
    with app.app_context():
        cli = Client(company_name='Cli Contact Test', tax_id='55443322', contact_name='P', contact_email='p@p.com', contact_phone='123')
        db.session.add(cli)
        db.session.commit()

        contact = ClientContact(
            client_id=cli.id,
            name='Carlos Restrepo',
            email='crestrepo@client.com',
            phone='3001234567',
            position='Gerente TI',
            is_primary=True
        )
        db.session.add(contact)
        db.session.commit()

        assert len(cli.contacts) == 1
        assert cli.contacts[0].email == 'crestrepo@client.com'

        # Ticket with contact
        tck = Ticket(
            ticket_code='TCK-2026-CONT1',
            client_id=cli.id,
            contact_id=contact.id,
            title='Solicitud de Acceso',
            description='Acceso a carpeta compartida',
            priority='Baja',
            created_at=datetime.utcnow(),
            sla_due_at=Ticket.calculate_sla_due('Baja')
        )
        db.session.add(tck)
        db.session.commit()

        assert tck.contact is not None
        assert tck.contact.name == 'Carlos Restrepo'

def test_system_settings(app):
    with app.app_context():
        from app.models import SystemSetting
        settings = SystemSetting.get_settings()
        assert settings.mail_server == 'smtp.gmail.com'
        assert settings.notifications_enabled is True

        settings.mail_server = 'smtp.office365.com'
        db.session.commit()

        fetched = SystemSetting.get_settings()
        assert fetched.mail_server == 'smtp.office365.com'


