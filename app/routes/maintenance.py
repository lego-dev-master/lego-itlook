import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_file)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.maintenance import MaintenanceEvent, MaintenanceEventItem
from app.models.client import Client
from app.models.asset import Asset
from app.models.user import User

maintenance_bp = Blueprint('maintenance', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _save_photo(file, prefix):
    """Guarda una imagen en la carpeta de uploads y devuelve el nombre o None."""
    if file and file.filename != '' and _allowed_image(file.filename):
        sec_filename = secure_filename(file.filename)
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{sec_filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)
        return filename
    return None


@maintenance_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '').strip()
    client_id = request.args.get('client_id', type=int)

    query = MaintenanceEvent.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if client_id:
        query = query.filter_by(client_id=client_id)

    events = query.order_by(MaintenanceEvent.opened_at.desc()).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()

    return render_template('maintenance/index.html',
                           events=events,
                           clients=clients,
                           status_filter=status_filter,
                           client_id=client_id,
                           status_choices=MaintenanceEvent.STATUS_CHOICES)


@maintenance_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        technician_id = request.form.get('technician_id', type=int) or current_user.id
        maintenance_type = request.form.get('maintenance_type', 'Preventivo').strip()
        observations = request.form.get('observations', '').strip()
        asset_ids = request.form.getlist('asset_ids', type=int)

        if not client_id:
            flash('Debe seleccionar un cliente.', 'warning')
            return redirect(url_for('maintenance.create'))
        if not asset_ids:
            flash('Debe seleccionar al menos un equipo para el evento de mantenimiento.', 'warning')
            return redirect(url_for('maintenance.create'))

        opened_at_str = request.form.get('opened_at', '').strip()
        try:
            opened_at = datetime.strptime(opened_at_str, '%Y-%m-%dT%H:%M') if opened_at_str else datetime.utcnow()
        except (ValueError, TypeError):
            opened_at = datetime.utcnow()

        event = MaintenanceEvent(
            client_id=client_id,
            technician_id=technician_id,
            maintenance_type=maintenance_type,
            status=MaintenanceEvent.STATUS_OPEN,
            observations=observations,
            opened_at=opened_at
        )
        db.session.add(event)
        db.session.flush()  # obtener event.id

        for asset_id in asset_ids:
            asset = Asset.query.get(asset_id)
            # Validar que el equipo pertenezca al cliente seleccionado
            if not asset or asset.client_id != client_id:
                continue
            item = MaintenanceEventItem(event_id=event.id, asset_id=asset_id)
            db.session.add(item)

        db.session.commit()
        flash(f'Evento de mantenimiento #{event.id} aperturado con éxito.', 'success')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    preselected_client_id = request.args.get('client_id', type=int)
    assets = []
    if preselected_client_id:
        assets = Asset.query.filter_by(client_id=preselected_client_id).order_by(Asset.internal_code.asc()).all()

    return render_template('maintenance/form.html',
                           clients=clients,
                           technicians=technicians,
                           preselected_client_id=preselected_client_id,
                           assets=assets,
                           now=datetime.utcnow())


@maintenance_bp.route('/<int:event_id>')
@login_required
def detail(event_id):
    event = MaintenanceEvent.query.get_or_404(event_id)
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    # Equipos del cliente que aún no están en el evento
    current_asset_ids = {item.asset_id for item in event.items}
    available_assets = [a for a in event.client.assets if a.id not in current_asset_ids]
    return render_template('maintenance/detail.html',
                           event=event,
                           technicians=technicians,
                           available_assets=available_assets)


@maintenance_bp.route('/<int:event_id>/add-assets', methods=['POST'])
@login_required
def add_assets(event_id):
    event = MaintenanceEvent.query.get_or_404(event_id)
    if event.is_finished:
        flash('No se pueden modificar los equipos de un evento terminado.', 'warning')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    asset_ids = request.form.getlist('asset_ids', type=int)
    added = 0
    for asset_id in asset_ids:
        asset = Asset.query.get(asset_id)
        if not asset or asset.client_id != event.client_id:
            continue
        if MaintenanceEventItem.query.filter_by(event_id=event.id, asset_id=asset_id).first():
            continue
        db.session.add(MaintenanceEventItem(event_id=event.id, asset_id=asset_id))
        added += 1

    db.session.commit()
    if added:
        flash(f'{added} equipo(s) agregado(s) al evento.', 'success')
    else:
        flash('No se agregaron equipos nuevos.', 'info')
    return redirect(url_for('maintenance.detail', event_id=event.id))


@maintenance_bp.route('/<int:event_id>/item/<int:item_id>/photos', methods=['POST'])
@login_required
def upload_photos(event_id, item_id):
    event = MaintenanceEvent.query.get_or_404(event_id)
    item = MaintenanceEventItem.query.get_or_404(item_id)
    if item.event_id != event.id:
        flash('El equipo no corresponde a este evento.', 'danger')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    photo_before = _save_photo(request.files.get('photo_before'), f'maint_before_{item.id}')
    photo_after = _save_photo(request.files.get('photo_after'), f'maint_after_{item.id}')

    if photo_before:
        # Reemplazar foto anterior si existía
        item.photo_before = photo_before
    if photo_after:
        item.photo_after = photo_after

    notes = request.form.get('notes', '').strip()
    if notes:
        item.notes = notes

    db.session.commit()

    if photo_before or photo_after:
        flash('Fotografías cargadas correctamente.', 'success')
    else:
        flash('No se cargó ninguna imagen válida (formatos: png, jpg, jpeg, gif, webp).', 'warning')
    return redirect(url_for('maintenance.detail', event_id=event.id))


@maintenance_bp.route('/<int:event_id>/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(event_id, item_id):
    event = MaintenanceEvent.query.get_or_404(event_id)
    if event.is_finished:
        flash('No se pueden modificar los equipos de un evento terminado.', 'warning')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    item = MaintenanceEventItem.query.get_or_404(item_id)
    if item.event_id != event.id:
        flash('El equipo no corresponde a este evento.', 'danger')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    db.session.delete(item)
    db.session.commit()
    flash('Equipo removido del evento.', 'info')
    return redirect(url_for('maintenance.detail', event_id=event.id))


@maintenance_bp.route('/<int:event_id>/update-status', methods=['POST'])
@login_required
def update_status(event_id):
    event = MaintenanceEvent.query.get_or_404(event_id)
    new_status = request.form.get('status', '').strip()

    if new_status not in MaintenanceEvent.STATUS_CHOICES:
        flash('Estado inválido.', 'warning')
        return redirect(url_for('maintenance.detail', event_id=event.id))

    event.status = new_status

    if new_status == MaintenanceEvent.STATUS_DONE:
        # Al terminar, se habilita/registra la fecha de cierre
        if not event.finished_at:
            event.finished_at = datetime.utcnow()
    else:
        # Si se reabre, se limpia la fecha de cierre
        event.finished_at = None

    observations = request.form.get('observations')
    if observations is not None:
        event.observations = observations.strip()

    db.session.commit()
    flash(f'Estado del evento actualizado a "{new_status}".', 'success')
    return redirect(url_for('maintenance.detail', event_id=event.id))


@maintenance_bp.route('/<int:event_id>/export/pdf')
@login_required
def export_pdf(event_id):
    """Genera el informe PDF del evento de mantenimiento (req-03, punto 2.4)."""
    event = MaintenanceEvent.query.get_or_404(event_id)

    from app.services.maintenance_pdf import generate_maintenance_event_pdf
    pdf_buffer = generate_maintenance_event_pdf(event, current_app.config['UPLOAD_FOLDER'])

    filename = f"informe_mantenimiento_evento_{event.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@maintenance_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin:
        flash('Acceso denegado: Se requieren permisos de Administrador.', 'danger')
        return redirect(url_for('maintenance.detail', event_id=event_id))

    event = MaintenanceEvent.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Evento de mantenimiento eliminado.', 'info')
    return redirect(url_for('maintenance.index'))
