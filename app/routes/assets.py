import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.asset import Asset, MaintenanceLog
from app.models.client import Client, Location

assets_bp = Blueprint('assets', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@assets_bp.route('/')
@login_required
def index():
    query = request.args.get('q', '').strip()
    client_id = request.args.get('client_id', type=int)
    device_type = request.args.get('device_type', '').strip()
    status = request.args.get('status', '').strip()

    assets_query = Asset.query
    if query:
        assets_query = assets_query.filter(
            (Asset.internal_code.ilike(f'%{query}%')) |
            (Asset.serial_number.ilike(f'%{query}%')) |
            (Asset.brand.ilike(f'%{query}%')) |
            (Asset.model.ilike(f'%{query}%'))
        )
    if client_id:
        assets_query = assets_query.filter_by(client_id=client_id)
    if device_type:
        assets_query = assets_query.filter_by(device_type=device_type)
    if status:
        assets_query = assets_query.filter_by(status=status)

    assets_list = assets_query.order_by(Asset.created_at.desc()).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    
    device_types = ['Servidor', 'PC Desktop', 'Laptop', 'Switch', 'Router', 'Firewall', 'Impresora', 'UPS', 'Otro']

    return render_template('assets/index.html',
                           assets=assets_list,
                           clients=clients,
                           device_types=device_types,
                           query=query,
                           client_id=client_id,
                           device_type=device_type,
                           status=status)

@assets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    if request.method == 'POST':
        internal_code = request.form.get('internal_code', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        device_type = request.form.get('device_type', '').strip()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        cpu = request.form.get('cpu', '').strip()
        ram = request.form.get('ram', '').strip()
        storage = request.form.get('storage', '').strip()
        os_installed = request.form.get('os_installed', '').strip()
        status = request.form.get('status', 'Operativo').strip()
        client_id = request.form.get('client_id', type=int)
        location_id = request.form.get('location_id', type=int)
        notes = request.form.get('notes', '').strip()

        if Asset.query.filter_by(internal_code=internal_code).first():
            flash(f'El código interno "{internal_code}" ya existe.', 'danger')
            return render_template('assets/form.html', asset=None, clients=clients)

        new_asset = Asset(
            internal_code=internal_code,
            serial_number=serial_number,
            device_type=device_type,
            brand=brand,
            model=model,
            cpu=cpu,
            ram=ram,
            storage=storage,
            os_installed=os_installed,
            status=status,
            client_id=client_id,
            location_id=location_id if location_id else None,
            notes=notes
        )
        db.session.add(new_asset)
        db.session.commit()
        flash(f'Equipo "{internal_code}" registrado exitosamente en Hoja de Vida.', 'success')
        return redirect(url_for('assets.detail', asset_id=new_asset.id))

    return render_template('assets/form.html', asset=None, clients=clients)

@assets_bp.route('/<int:asset_id>')
@login_required
def detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return render_template('assets/detail.html', asset=asset)

@assets_bp.route('/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    
    if request.method == 'POST':
        asset.internal_code = request.form.get('internal_code', '').strip()
        asset.serial_number = request.form.get('serial_number', '').strip()
        asset.device_type = request.form.get('device_type', '').strip()
        asset.brand = request.form.get('brand', '').strip()
        asset.model = request.form.get('model', '').strip()
        asset.cpu = request.form.get('cpu', '').strip()
        asset.ram = request.form.get('ram', '').strip()
        asset.storage = request.form.get('storage', '').strip()
        asset.os_installed = request.form.get('os_installed', '').strip()
        asset.status = request.form.get('status', 'Operativo').strip()
        asset.client_id = request.form.get('client_id', type=int)
        
        loc_id = request.form.get('location_id', type=int)
        asset.location_id = loc_id if loc_id else None
        asset.notes = request.form.get('notes', '').strip()

        db.session.commit()
        flash(f'Equipo "{asset.internal_code}" actualizado.', 'success')
        return redirect(url_for('assets.detail', asset_id=asset.id))

    return render_template('assets/form.html', asset=asset, clients=clients)

@assets_bp.route('/<int:asset_id>/add-maintenance', methods=['POST'])
@login_required
def add_maintenance(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    log_type = request.form.get('log_type', 'Preventivo')
    description = request.form.get('description', '').strip()
    cost = request.form.get('cost', 0.0, type=float)

    if not description:
        flash('La descripción del mantenimiento es obligatoria.', 'warning')
        return redirect(url_for('assets.detail', asset_id=asset_id))

    filename = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename != '' and allowed_file(file.filename):
            sec_filename = secure_filename(file.filename)
            filename = f"maint_{asset_id}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

    log = MaintenanceLog(
        asset_id=asset_id,
        user_id=current_user.id,
        log_type=log_type,
        description=description,
        cost=cost,
        attachment_filename=filename
    )
    
    # Update asset status if requested
    new_status = request.form.get('new_asset_status')
    if new_status:
        asset.status = new_status

    db.session.add(log)
    db.session.commit()
    flash('Registro de mantenimiento añadido a la hoja de vida.', 'success')
    return redirect(url_for('assets.detail', asset_id=asset_id))

@assets_bp.route('/api/<int:client_id>/assets')
@login_required
def api_assets(client_id):
    assets = Asset.query.filter_by(client_id=client_id).all()
    return jsonify([{'id': a.id, 'internal_code': a.internal_code, 'name': f"{a.internal_code} - {a.device_type} ({a.brand} {a.model})"} for a in assets])
