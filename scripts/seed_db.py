import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date, timedelta
from app import create_app

from app.extensions import db
from app.models import User, Client, Location, ClientContact, Asset, MaintenanceLog, MicrosoftLicense, Ticket, TicketIntervention, SystemSetting

app = create_app('dev')

def seed_database():
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding System Settings...")
        settings = SystemSetting(
            mail_server='smtp.gmail.com',
            mail_port=587,
            mail_use_tls=True,
            mail_username='soporte@legoitlook.com',
            mail_password='AppPassword123!',
            mail_sender_name='LEGO TICS SAS Soporte',
            mail_sender_email='soporte@legoitlook.com',
            notifications_enabled=True
        )
        db.session.add(settings)
        db.session.commit()

        print("Seeding Users...")
        admin = User(name='Administrador IT', email='admin@legoitlook.com', role='admin')
        admin.set_password('Admin123!')

        tech1 = User(name='Carlos Mendoza (Técnico Sr)', email='carlos.mendoza@legoitlook.com', role='tech')
        tech1.set_password('Tech123!')

        tech2 = User(name='Andrea Rodríguez (Técnico)', email='andrea.rodriguez@legoitlook.com', role='tech')
        tech2.set_password('Tech123!')

        db.session.add_all([admin, tech1, tech2])
        db.session.commit()

        print("Seeding Clients, Contacts & Locations...")
        client1 = Client(
            company_name='Alimentos del Caribe S.A.S.',
            tax_id='900.543.210-1',
            contact_name='Roberto Gómez',
            contact_email='rgomez@alimentoscaribe.com',
            contact_phone='+57 315 9876543',
            address='Zona Franca Barranquilla Lote 12'
        )
        client2 = Client(
            company_name='Constructora Urbano SAS',
            tax_id='800.123.999-4',
            contact_name='Laura Restrepo',
            contact_email='lrestrepo@constructoraurbano.co',
            contact_phone='+57 300 4567890',
            address='Calle 93 #11A-28, Bogotá'
        )
        client3 = Client(
            company_name='Banco Financiero Andino',
            tax_id='860.001.555-8',
            contact_name='Felipe Jaramillo',
            contact_email='fjaramillo@bancoandino.com',
            contact_phone='+57 320 1112233',
            address='Carrera 7 #71-21, Bogotá'
        )

        db.session.add_all([client1, client2, client3])
        db.session.commit()

        # Contacts
        cont1_1 = ClientContact(client_id=client1.id, name='Roberto Gómez', email='rgomez@alimentoscaribe.com', phone='+57 315 9876543', position='Gerente General', is_primary=True)
        cont1_2 = ClientContact(client_id=client1.id, name='Dora Silva', email='dsilva@alimentoscaribe.com', phone='+57 301 2223344', position='Jefa de Sistemas', is_primary=False)
        cont2_1 = ClientContact(client_id=client2.id, name='Laura Restrepo', email='lrestrepo@constructoraurbano.co', phone='+57 300 4567890', position='Directora de Operaciones', is_primary=True)
        cont3_1 = ClientContact(client_id=client3.id, name='Felipe Jaramillo', email='fjaramillo@bancoandino.com', phone='+57 320 1112233', position='Gerente de Tecnología', is_primary=True)

        db.session.add_all([cont1_1, cont1_2, cont2_1, cont3_1])
        db.session.commit()

        # Locations
        loc1_1 = Location(client_id=client1.id, name='Planta Barranquilla', city='Barranquilla', address='Zona Franca Lote 12', contact_person='Roberto Gómez', contact_phone='+57 315 9876543')
        loc1_2 = Location(client_id=client1.id, name='Sede Administrativa Medellín', city='Medellín', address='El Poblado Cra 43A #1-50', contact_person='Dora Silva', contact_phone='+57 301 2223344')
        loc2_1 = Location(client_id=client2.id, name='Oficinas Bogotá', city='Bogotá', address='Calle 93 #11A-28', contact_person='Laura Restrepo', contact_phone='+57 300 4567890')
        loc3_1 = Location(client_id=client3.id, name='Torre Principal Bogotá', city='Bogotá', address='Carrera 7 #71-21', contact_person='Felipe Jaramillo', contact_phone='+57 320 1112233')

        db.session.add_all([loc1_1, loc1_2, loc2_1, loc3_1])
        db.session.commit()


        print("Seeding Assets & Maintenance Logs...")
        asset1 = Asset(
            internal_code='SRV-CARIBE-01',
            serial_number='SN-DELL-998822',
            device_type='Servidor',
            brand='Dell',
            model='PowerEdge R750',
            cpu='2x Intel Xeon Gold 6330',
            ram='128 GB DDR4',
            storage='4x 1.92TB SSD RAID10',
            os_installed='Windows Server 2022 Datacenter',
            status='Operativo',
            client_id=client1.id,
            location_id=loc1_1.id,
            notes='Servidor principal de base de datos de producción ERP.'
        )

        asset2 = Asset(
            internal_code='LAP-URBANO-014',
            serial_number='SN-LEN-554433',
            device_type='Laptop',
            brand='Lenovo',
            model='ThinkPad T14 Gen 3',
            cpu='Intel Core i7 1260P',
            ram='16 GB DDR4',
            storage='512 GB NVMe SSD',
            os_installed='Windows 11 Pro',
            status='En Mantenimiento',
            client_id=client2.id,
            location_id=loc2_1.id,
            notes='Asignado a Dirección de Obras. Presentó pantalla azul.'
        )

        asset3 = Asset(
            internal_code='SW-ANDINO-CORE',
            serial_number='SN-CISCO-771122',
            device_type='Switch',
            brand='Cisco',
            model='Catalyst 9300 48P',
            cpu='Multicore Custom CISCO',
            ram='8 GB',
            storage='16 GB Flash',
            os_installed='Cisco IOS-XE 17.6',
            status='Operativo',
            client_id=client3.id,
            location_id=loc3_1.id,
            notes='Switch Core principal piso 5.'
        )

        db.session.add_all([asset1, asset2, asset3])
        db.session.commit()

        # Maintenance logs
        maint1 = MaintenanceLog(
            asset_id=asset1.id,
            user_id=tech1.id,
            log_type='Preventivo',
            description='Limpieza física de chasis, actualización de Firmware iDRAC9 a v5.10 y revisión de redundancia de fuentes.',
            cost=150.00
        )
        maint2 = MaintenanceLog(
            asset_id=asset2.id,
            user_id=tech2.id,
            log_type='Correctivo',
            description='Diagnóstico de falla por corrupción de drivers de pantalla. Reinstalación limpia de SO Windows 11 Pro.',
            cost=80.00
        )
        db.session.add_all([maint1, maint2])
        db.session.commit()

        print("Seeding Microsoft Licenses...")
        today = date.today()
        lic1 = MicrosoftLicense(
            client_id=client1.id,
            subscription_type='Microsoft 365 Business Premium',
            quantity=45,
            assigned_users_count=42,
            acquisition_date=today - timedelta(days=360),
            expiration_date=today + timedelta(days=4), # CRITICAL <= 5 DAYS!
            installation_user='admin@alimentoscaribe.onmicrosoft.com',
            installation_password='P@ssw0rdCaribe2026',
            activation_code='M365-PREM-9988-7766-5544',
            download_link='https://setup.office.com/',
            assigned_user_names='Roberto Gómez, Ana Martínez, Dora Silva, Carlos López',
            notes='Licencias contratadas vía Canal CSP Directo.'
        )
        lic2 = MicrosoftLicense(
            client_id=client2.id,
            subscription_type='Azure Plan (Suscripción Infraestructura)',
            quantity=1,
            assigned_users_count=1,
            acquisition_date=today - timedelta(days=350),
            expiration_date=today + timedelta(days=12), # WARNING <= 15 DAYS!
            installation_user='devops@constructoraurbano.onmicrosoft.com',
            installation_password='AzureUrbanoPass!',
            activation_code='AZURE-PLAN-SUB-2026-X1',
            download_link='https://portal.azure.com/',
            assigned_user_names='Laura Restrepo (DevOps Team)',
            notes='Crédito reservado Azure dev/test.'
        )
        lic3 = MicrosoftLicense(
            client_id=client3.id,
            subscription_type='Microsoft 365 E5 Enterprise',
            quantity=120,
            assigned_users_count=115,
            acquisition_date=today - timedelta(days=200),
            expiration_date=today + timedelta(days=160), # ACTIVE > 30 DAYS!
            installation_user='globaladmin@bancoandino.com',
            installation_password='E5SecureBank2026!',
            activation_code='E5ENT-BANK-1122-3344-5566',
            download_link='https://portal.office.com/',
            assigned_user_names='Felipe Jaramillo, Dirección Ejecutiva, Gerencia Financiera',
            notes='Enterprise Agreement.'
        )
        lic4 = MicrosoftLicense(
            client_id=client1.id,
            subscription_type='Windows Server 2022 Standard (16 Core)',
            quantity=4,
            assigned_users_count=4,
            acquisition_date=today - timedelta(days=370),
            expiration_date=today - timedelta(days=5), # EXPIRED!
            installation_user='administrator@localdomain',
            installation_password='WinServerKey2026',
            activation_code='WNS22-STD-4433-2211-0099',
            download_link='https://www.microsoft.com/evalcenter/',
            assigned_user_names='Servidores BD Caribe 1 al 4',
            notes='Licencia de servidor en evaluación vencida.'
        )


        db.session.add_all([lic1, lic2, lic3, lic4])
        db.session.commit()

        print("Seeding Tickets & Interventions...")
        now = datetime.utcnow()
        tck1 = Ticket(
            ticket_code='TCK-2026-0001',
            client_id=client2.id,
            location_id=loc2_1.id,
            contact_id=cont2_1.id,
            asset_id=asset2.id,
            assigned_to_id=tech2.id,
            title='Falla Crítica: Laptop Dirección no enciende pantalla',
            description='La laptop del Ing. Pérez presenta pantallas azules recurrentes y fallas en el inicio de sesión.',
            priority='Crítica',
            service_type='Soporte',
            status='En Proceso',
            created_at=now - timedelta(hours=1),
            sla_due_at=now + timedelta(hours=1) # SLA 2 hours
        )

        tck2 = Ticket(
            ticket_code='TCK-2026-0002',
            client_id=client1.id,
            location_id=loc1_1.id,
            contact_id=cont1_2.id,
            asset_id=asset1.id,
            assigned_to_id=tech1.id,
            title='Mantenimiento Preventivo Trimestral Servidor ERP',
            description='Ejecución de rutina de respaldo de base de datos y parches de seguridad acumulativos de Windows Server.',
            priority='Media',
            service_type='Mantenimiento',
            status='Abierto',
            created_at=now - timedelta(hours=3),
            sla_due_at=now + timedelta(hours=5) # SLA 8 hours
        )


        db.session.add_all([tck1, tck2])
        db.session.commit()

        it1 = TicketIntervention(
            ticket_id=tck1.id,
            user_id=tech2.id,
            notes='Se recibe el equipo en taller técnico. Se detecta corrupción de archivos de sistema en sectores de disco.',
            hours_spent=1.0,
            previous_status='Abierto',
            new_status='En Proceso'
        )
        db.session.add(it1)
        db.session.commit()

        print("Database successfully seeded with realistic Lego ITlook data!")

if __name__ == '__main__':
    seed_database()
