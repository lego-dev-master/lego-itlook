from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.client import Client, Location, ClientContact


clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/')
@login_required
def index():
    query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'active')

    clients_query = Client.query
    if status_filter == 'active':
        clients_query = clients_query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        clients_query = clients_query.filter_by(is_active=False)

    if query:
        clients_query = clients_query.filter(
            (Client.company_name.ilike(f'%{query}%')) |
            (Client.tax_id.ilike(f'%{query}%')) |
            (Client.contact_name.ilike(f'%{query}%'))
        )

    clients_list = clients_query.order_by(Client.company_name.asc()).all()
    return render_template('clients/index.html', clients=clients_list, query=query, status_filter=status_filter)

@clients_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        tax_id = request.form.get('tax_id', '').strip()
        contact_name = request.form.get('contact_name', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        address = request.form.get('address', '').strip()

        if Client.query.filter_by(tax_id=tax_id).first():
            flash(f'Ya existe un cliente con el NIT/Identificación {tax_id}.', 'danger')
            return render_template('clients/form.html', client=None)

        new_client = Client(
            company_name=company_name,
            tax_id=tax_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            address=address
        )
        db.session.add(new_client)
        db.session.commit()

        # Add initial main location if provided
        main_location_name = request.form.get('main_location_name', 'Sede Principal').strip()
        location = Location(
            client_id=new_client.id,
            name=main_location_name or 'Sede Principal',
            address=address,
            contact_person=contact_name,
            contact_phone=contact_phone
        )
        db.session.add(location)

        # Add initial primary contact
        initial_contact = ClientContact(
            client_id=new_client.id,
            name=contact_name,
            email=contact_email,
            phone=contact_phone,
            position='Contacto Principal',
            is_primary=True
        )
        db.session.add(initial_contact)
        db.session.commit()


        flash(f'Cliente "{company_name}" creado exitosamente.', 'success')
        return redirect(url_for('clients.detail', client_id=new_client.id))

    return render_template('clients/form.html', client=None)

@clients_bp.route('/<int:client_id>')
@login_required
def detail(client_id):
    client = Client.query.get_or_404(client_id)
    return render_template('clients/detail.html', client=client)

@clients_bp.route('/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        client.company_name = request.form.get('company_name', '').strip()
        client.tax_id = request.form.get('tax_id', '').strip()
        client.contact_name = request.form.get('contact_name', '').strip()
        client.contact_email = request.form.get('contact_email', '').strip()
        client.contact_phone = request.form.get('contact_phone', '').strip()
        client.address = request.form.get('address', '').strip()
        
        db.session.commit()
        flash(f'Cliente "{client.company_name}" actualizado.', 'success')
        return redirect(url_for('clients.detail', client_id=client.id))

    return render_template('clients/form.html', client=client)

@clients_bp.route('/<int:client_id>/toggle-status', methods=['POST'])
@login_required
def toggle_status(client_id):
    client = Client.query.get_or_404(client_id)
    client.is_active = not client.is_active
    db.session.commit()
    status_str = "activado" if client.is_active else "deshabilitado"
    flash(f'Cliente "{client.company_name}" ha sido {status_str}.', 'info')
    return redirect(url_for('clients.index'))

@clients_bp.route('/<int:client_id>/add-location', methods=['POST'])
@login_required
def add_location(client_id):
    client = Client.query.get_or_404(client_id)
    name = request.form.get('name', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    contact_person = request.form.get('contact_person', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()

    if not name:
        flash('El nombre de la sede es obligatorio.', 'warning')
        return redirect(url_for('clients.detail', client_id=client_id))

    new_loc = Location(
        client_id=client_id,
        name=name,
        address=address,
        city=city,
        contact_person=contact_person,
        contact_phone=contact_phone
    )
    db.session.add(new_loc)
    db.session.commit()
    flash(f'Sede "{name}" agregada con éxito.', 'success')
    return redirect(url_for('clients.detail', client_id=client_id))

@clients_bp.route('/api/<int:client_id>/locations')
@login_required
def api_locations(client_id):
    locations = Location.query.filter_by(client_id=client_id).all()
    return jsonify([{'id': l.id, 'name': l.name} for l in locations])

@clients_bp.route('/<int:client_id>/add-contact', methods=['POST'])
@login_required
def add_contact(client_id):
    client = Client.query.get_or_404(client_id)
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    position = request.form.get('position', '').strip()
    is_primary = True if request.form.get('is_primary') else False

    if not name or not email:
        flash('Nombre y Correo del contacto son obligatorios.', 'warning')
        return redirect(url_for('clients.detail', client_id=client_id))

    if is_primary:
        # Unset other primary contacts for this client
        ClientContact.query.filter_by(client_id=client_id).update({'is_primary': False})

    new_contact = ClientContact(
        client_id=client_id,
        name=name,
        email=email,
        phone=phone,
        position=position,
        is_primary=is_primary
    )
    db.session.add(new_contact)
    db.session.commit()
    flash(f'Contacto "{name}" agregado con éxito.', 'success')
    return redirect(url_for('clients.detail', client_id=client_id))

@clients_bp.route('/<int:client_id>/delete-contact/<int:contact_id>', methods=['POST'])
@login_required
def delete_contact(client_id, contact_id):
    contact = ClientContact.query.get_or_404(contact_id)
    if contact.client_id != client_id:
        flash('Contacto no corresponde al cliente.', 'danger')
        return redirect(url_for('clients.detail', client_id=client_id))

    db.session.delete(contact)
    db.session.commit()
    flash('Contacto eliminado correctamente.', 'info')
    return redirect(url_for('clients.detail', client_id=client_id))

@clients_bp.route('/api/<int:client_id>/contacts')
@login_required
def api_contacts(client_id):
    contacts = ClientContact.query.filter_by(client_id=client_id).order_by(ClientContact.name.asc()).all()
    return jsonify([
        {
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'position': c.position or '',
            'is_primary': c.is_primary
        } for c in contacts
    ])

