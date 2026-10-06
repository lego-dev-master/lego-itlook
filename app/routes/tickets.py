import os
from datetime import datetime
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.ticket import Ticket, TicketIntervention
from app.models.client import Client, Location, ClientContact
from app.models.asset import Asset
from app.models.user import User
from app.services.email_service import send_ticket_created_notification, send_ticket_closed_notification

tickets_bp = Blueprint('tickets', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _filtered_tickets_query():
    """Construye la consulta de tickets aplicando los filtros de cliente y fechas.

    Devuelve una tupla (query, date_from, date_to) donde date_from/date_to son
    objetos date o None, para reutilizar en la vista y en la exportación a Excel.
    """
    client_id = request.args.get('client_id', type=int)
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    query = Ticket.query
    if client_id:
        query = query.filter_by(client_id=client_id)

    date_from = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= date_from)
        except (ValueError, TypeError):
            date_from = None

    date_to = None
    if date_to_str:
        try:
            # Incluir todo el día final (hasta las 23:59:59)
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Ticket.created_at <= date_to_end)
        except (ValueError, TypeError):
            date_to = None

    return query, date_from, date_to

def generate_ticket_code():
    year = datetime.utcnow().year
    last_ticket = Ticket.query.order_by(Ticket.id.desc()).first()
    next_id = (last_ticket.id + 1) if last_ticket else 1
    return f"TCK-{year}-{next_id:04d}"

@tickets_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    client_id = request.args.get('client_id', type=int)
    assigned_to_me = request.args.get('my_tickets', type=int)
    sla_filter = request.args.get('sla', '').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    query = Ticket.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if assigned_to_me or not current_user.is_admin:
        query = query.filter_by(assigned_to_id=current_user.id)

    # Filtros por fecha (rango sobre created_at)
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= date_from)
        except (ValueError, TypeError):
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Ticket.created_at <= date_to_end)
        except (ValueError, TypeError):
            pass

    tickets_list = query.order_by(Ticket.created_at.desc()).all()

    if sla_filter == 'breached':
        tickets_list = [t for t in tickets_list if t.is_sla_breached]
    elif sla_filter == 'ontime':
        tickets_list = [t for t in tickets_list if not t.is_sla_breached]

    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template('tickets/index.html',
                           tickets=tickets_list,
                           clients=clients,
                           technicians=technicians,
                           status_filter=status_filter,
                           priority_filter=priority_filter,
                           client_id=client_id,
                           assigned_to_me=assigned_to_me,
                           sla_filter=sla_filter,
                           date_from=date_from_str,
                           date_to=date_to_str)

@tickets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        location_id = request.form.get('location_id', type=int)
        contact_id = request.form.get('contact_id', type=int)
        asset_id = request.form.get('asset_id', type=int)
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Media').strip()
        service_type = request.form.get('service_type', 'Soporte').strip()

        if not title or not description or not client_id:
            flash('Por favor complete los campos obligatorios.', 'warning')
            return render_template('tickets/form.html', ticket=None, clients=clients, technicians=technicians)

        ticket_code = generate_ticket_code()
        created_now = datetime.utcnow()
        sla_due = Ticket.calculate_sla_due(priority, created_now)

        new_ticket = Ticket(
            ticket_code=ticket_code,
            client_id=client_id,
            location_id=location_id if location_id else None,
            contact_id=contact_id if contact_id else None,
            asset_id=asset_id if asset_id else None,
            assigned_to_id=assigned_to_id if assigned_to_id else current_user.id,
            title=title,
            description=description,
            priority=priority,
            service_type=service_type,
            status='Abierto',
            created_at=created_now,
            sla_due_at=sla_due
        )
        db.session.add(new_ticket)
        db.session.commit()

        # Trigger automatic creation email to client contact
        if new_ticket.contact:
            send_ticket_created_notification(new_ticket, new_ticket.contact)

        flash(f'Ticket {ticket_code} creado exitosamente. SLA debido: {sla_due.strftime("%Y-%m-%d %H:%M")}', 'success')
        return redirect(url_for('tickets.detail', ticket_id=new_ticket.id))

    preselected_client_id = request.args.get('client_id', type=int)
    contacts = []
    locations = []
    assets = []
    if preselected_client_id:
        contacts = ClientContact.query.filter_by(client_id=preselected_client_id).order_by(ClientContact.name.asc()).all()
        locations = Location.query.filter_by(client_id=preselected_client_id).all()
        assets = Asset.query.filter_by(client_id=preselected_client_id).all()

    return render_template('tickets/form.html',
                           ticket=None,
                           clients=clients,
                           technicians=technicians,
                           preselected_client_id=preselected_client_id,
                           contacts=contacts,
                           locations=locations,
                           assets=assets)


@tickets_bp.route('/<int:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    return render_template('tickets/detail.html', ticket=ticket, technicians=technicians)

@tickets_bp.route('/<int:ticket_id>/add-intervention', methods=['POST'])
@login_required
def add_intervention(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    notes = request.form.get('notes', '').strip()
    hours_spent = request.form.get('hours_spent', 0.5, type=float)
    new_status = request.form.get('status')
    reassign_to_id = request.form.get('reassign_to_id', type=int)

    if not notes:
        flash('Las notas de la intervención son obligatorias.', 'warning')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    previous_status = ticket.status
    filename = None

    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename != '' and allowed_file(file.filename):
            sec_filename = secure_filename(file.filename)
            filename = f"tck_{ticket_id}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

    # Status update logic
    status_changed_to_closed = False
    if new_status and new_status != ticket.status:
        ticket.status = new_status
        if new_status in ['Resuelto', 'Cerrado']:
            status_changed_to_closed = True
            if not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
        if new_status == 'Cerrado' and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()

    # Reassignment logic
    if reassign_to_id and reassign_to_id != ticket.assigned_to_id:
        ticket.assigned_to_id = reassign_to_id

    intervention = TicketIntervention(
        ticket_id=ticket_id,
        user_id=current_user.id,
        notes=notes,
        hours_spent=hours_spent,
        previous_status=previous_status,
        new_status=ticket.status,
        attachment_filename=filename
    )

    db.session.add(intervention)
    db.session.commit()

    # Trigger automatic resolution email to contact if ticket was resolved/closed
    if status_changed_to_closed and ticket.contact:
        send_ticket_closed_notification(ticket, ticket.contact, notes)

    flash('Intervención registrada en el historial del ticket.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/export/excel')
@login_required
def export_excel():
    client_id = request.args.get('client_id', type=int)
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()

    query = Ticket.query
    if client_id:
        query = query.filter_by(client_id=client_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)

    # Filtros por rango de fechas sobre la fecha de creación
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= date_from)
        except (ValueError, TypeError):
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Ticket.created_at <= date_to_end)
        except (ValueError, TypeError):
            pass

    tickets_list = query.order_by(Ticket.created_at.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets de Servicio"

    headers = [
        "ID",
        "Código Ticket",
        "Cliente",
        "NIT / ID Fiscal",
        "Sede",
        "Contacto",
        "Correo Contacto",
        "Equipo (Código Interno)",
        "Asunto",
        "Descripción",
        "Tipo de Servicio",
        "Prioridad",
        "Estado",
        "Técnico Asignado",
        "Fecha Creación",
        "Límite SLA",
        "SLA Cumplido",
        "Fecha Resolución",
        "Fecha Cierre",
        "Horas Totales Intervención",
        "N° Intervenciones",
        "Fecha Registro"
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    ws.append(headers)
    ws.row_dimensions[1].height = 26

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    for t in tickets_list:
        total_hours = sum(float(i.hours_spent or 0) for i in t.interventions)
        row_data = [
            t.id,
            t.ticket_code or '',
            t.client.company_name if t.client else '',
            t.client.tax_id if t.client else '',
            t.location.name if t.location else 'Sede Principal',
            t.contact.name if t.contact else '',
            t.contact.email if t.contact else '',
            t.asset.internal_code if t.asset else '',
            t.title or '',
            t.description or '',
            t.service_type or '',
            t.priority or '',
            t.status or '',
            t.assigned_to_user.name if t.assigned_to_user else 'Sin Asignar',
            t.created_at.strftime('%Y-%m-%d %H:%M') if t.created_at else '',
            t.sla_due_at.strftime('%Y-%m-%d %H:%M') if t.sla_due_at else '',
            'No' if t.is_sla_breached else 'Sí',
            t.resolved_at.strftime('%Y-%m-%d %H:%M') if t.resolved_at else '',
            t.closed_at.strftime('%Y-%m-%d %H:%M') if t.closed_at else '',
            round(total_hours, 2),
            len(t.interventions),
            t.created_at.strftime('%Y-%m-%d %H:%M') if t.created_at else ''
        ]
        ws.append(row_data)

    for row in range(2, len(tickets_list) + 2):
        ws.row_dimensions[row].height = 20
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"reporte_tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

