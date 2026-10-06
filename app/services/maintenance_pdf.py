"""Generación de reportes PDF para eventos de mantenimiento (req-03, punto 2.4).

Usa ReportLab (pura Python, sin dependencias de sistema) para construir un
informe con:
  - Encabezado: datos de LEGO TICS SAS + nombre del cliente y datos del evento.
  - Detalle de los equipos intervenidos (con sus fotos antes/después si existen).

Devuelve un objeto BytesIO listo para enviarse con send_file().
"""
import os
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, HRFlowable
)

# Paleta corporativa (coincide con el tema de la app)
COLOR_PRIMARY = colors.HexColor('#0ea5e9')
COLOR_DARK = colors.HexColor('#0f172a')
COLOR_SLATE = colors.HexColor('#1e293b')
COLOR_MUTED = colors.HexColor('#64748b')
COLOR_LIGHT = colors.HexColor('#f1f5f9')
COLOR_BORDER = colors.HexColor('#cbd5e1')


def _fmt_dt(dt):
    if not dt:
        return '—'
    return dt.strftime('%d/%m/%Y %H:%M')


def _fmt_date(dt):
    if not dt:
        return '—'
    return dt.strftime('%d/%m/%Y')


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='DocTitle', parent=styles['Title'],
        fontName='Helvetica-Bold', fontSize=18, leading=22,
        textColor=COLOR_DARK, alignment=TA_LEFT, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name='DocSubtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, leading=13,
        textColor=COLOR_MUTED, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12, leading=15,
        textColor=COLOR_PRIMARY, spaceBefore=8, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='Cell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, leading=12, textColor=COLOR_DARK,
    ))
    styles.add(ParagraphStyle(
        name='CellBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=COLOR_DARK,
    ))
    styles.add(ParagraphStyle(
        name='CellMuted', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11, textColor=COLOR_MUTED,
    ))
    styles.add(ParagraphStyle(
        name='EquipmentName', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=COLOR_DARK,
    ))
    styles.add(ParagraphStyle(
        name='SmallRight', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, leading=11,
        textColor=COLOR_MUTED, alignment=TA_RIGHT,
    ))
    return styles


def _footer(canvas, doc):
    """Dibuja el pie de página en cada hoja."""
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 15 * mm, width - 15 * mm, 15 * mm)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(COLOR_MUTED)
    canvas.drawString(15 * mm, 10 * mm, 'LEGO TICS SAS — Informe de Mantenimiento de Equipos')
    canvas.drawRightString(width - 15 * mm, 10 * mm, f'Página {doc.page}')
    canvas.restoreState()


def _header_block(event, styles):
    """Bloque de encabezado: marca + datos del cliente y del evento."""
    flowables = []

    # Línea de marca
    brand = Paragraph(
        '<font color="#0ea5e9"><b>LEGO ITlook</b></font> '
        '<font color="#64748b">| LEGO TICS SAS</font>',
        styles['DocSubtitle']
    )
    title = Paragraph('Informe de Mantenimiento de Equipos', styles['DocTitle'])

    right = Paragraph(
        f'<b>Evento #{event.id}</b><br/>Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        styles['SmallRight']
    )

    head_table = Table(
        [[Paragraph('', styles['Cell']), right]],
        colWidths=[110 * mm, 60 * mm]
    )
    head_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    flowables.append(brand)
    flowables.append(title)
    flowables.append(Spacer(1, 4))
    flowables.append(head_table)
    flowables.append(Spacer(1, 8))
    flowables.append(HRFlowable(width='100%', thickness=1.2, color=COLOR_PRIMARY))
    flowables.append(Spacer(1, 10))

    # Tarjeta de datos del cliente y del evento
    client = event.client
    technician = event.technician.name if event.technician else 'Sin Asignar'

    def kv(label, value):
        return [
            Paragraph(label, styles['CellMuted']),
            Paragraph(str(value), styles['CellBold']),
        ]

    info_rows = [
        [Paragraph('CLIENTE', styles['CellMuted']), Paragraph('', styles['CellMuted']),
         Paragraph('DATOS DEL EVENTO', styles['CellMuted']), Paragraph('', styles['CellMuted'])],
        [Paragraph(str(client.company_name if client else '—'), styles['EquipmentName']), '',
         Paragraph(f'Tipo: <b>{event.maintenance_type}</b>', styles['Cell']), ''],
        [Paragraph(f'NIT: {client.tax_id if client else "—"}', styles['Cell']), '',
         Paragraph(f'Estado: <b>{event.status}</b>', styles['Cell']), ''],
        [Paragraph(f'Contacto: {client.contact_name if client else "—"}', styles['Cell']), '',
         Paragraph(f'Técnico: {technician}', styles['Cell']), ''],
        [Paragraph(f'Tel: {client.contact_phone if client else "—"}', styles['Cell']), '',
         Paragraph(f'Apertura: {_fmt_dt(event.opened_at)}', styles['Cell']), ''],
        [Paragraph(f'Email: {client.contact_email if client else "—"}', styles['Cell']), '',
         Paragraph(f'Terminación: {_fmt_dt(event.finished_at)}', styles['Cell']), ''],
    ]

    info_table = Table(info_rows, colWidths=[32 * mm, 53 * mm, 32 * mm, 53 * mm])
    info_table.setStyle(TableStyle([
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (0, 2), (1, 2)),
        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (0, 4), (1, 4)),
        ('SPAN', (0, 5), (1, 5)),
        ('SPAN', (2, 1), (3, 1)),
        ('SPAN', (2, 2), (3, 2)),
        ('SPAN', (2, 3), (3, 3)),
        ('SPAN', (2, 4), (3, 4)),
        ('SPAN', (2, 5), (3, 5)),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    flowables.append(info_table)

    if event.observations:
        flowables.append(Spacer(1, 10))
        flowables.append(Paragraph('Observaciones del Técnico (Evento)', styles['SectionTitle']))
        flowables.append(Paragraph(event.observations.replace('\n', '<br/>'), styles['Cell']))

    return flowables


def _equipment_summary_table(event, styles):
    """Tabla resumen de los equipos intervenidos en el evento."""
    rows = [[
        Paragraph('#', styles['CellBold']),
        Paragraph('Código Interno', styles['CellBold']),
        Paragraph('Tipo', styles['CellBold']),
        Paragraph('Marca / Modelo', styles['CellBold']),
        Paragraph('Serial', styles['CellBold']),
        Paragraph('Sede', styles['CellBold']),
    ]]
    for idx, item in enumerate(event.items, start=1):
        a = item.asset
        rows.append([
            Paragraph(str(idx), styles['Cell']),
            Paragraph(a.internal_code or '—', styles['CellBold']),
            Paragraph(a.device_type or '—', styles['Cell']),
            Paragraph(f'{(a.brand or "")} {(a.model or "")}'.strip() or '—', styles['Cell']),
            Paragraph(a.serial_number or '—', styles['Cell']),
            Paragraph(a.location.name if a.location else 'Sede Principal', styles['Cell']),
        ])

    table = Table(rows, colWidths=[10 * mm, 30 * mm, 28 * mm, 40 * mm, 32 * mm, 30 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT]),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def _equipment_detail(event, upload_folder, styles):
    """Detalle por equipo: especificaciones, notas y fotos antes/después."""
    flowables = []
    flowables.append(Paragraph('Detalle de Equipos Intervenidos', styles['SectionTitle']))

    for idx, item in enumerate(event.items, start=1):
        a = item.asset
        block = []

        header = Paragraph(
            f'{idx}. {a.internal_code or "—"} '
            f'<font color="#64748b" size="9">— {a.device_type or ""}</font>',
            styles['EquipmentName']
        )
        block.append(header)
        block.append(Spacer(1, 4))

        # Especificaciones
        specs = [
            [Paragraph('Marca / Modelo', styles['CellMuted']),
             Paragraph(f'{(a.brand or "")} {(a.model or "")}'.strip() or '—', styles['Cell'])],
            [Paragraph('Serial', styles['CellMuted']),
             Paragraph(a.serial_number or '—', styles['Cell'])],
            [Paragraph('CPU / RAM / Disco', styles['CellMuted']),
             Paragraph(f'{a.cpu or "N/A"} | {a.ram or "N/A"} | {a.storage or "N/A"}', styles['Cell'])],
            [Paragraph('Sistema Operativo', styles['CellMuted']),
             Paragraph(a.os_installed or 'No registrado', styles['Cell'])],
            [Paragraph('Estado actual', styles['CellMuted']),
             Paragraph(a.status or '—', styles['Cell'])],
        ]
        specs_table = Table(specs, colWidths=[40 * mm, 130 * mm])
        specs_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (0, -1), COLOR_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ]))
        block.append(specs_table)

        # Notas del equipo
        if item.notes:
            block.append(Spacer(1, 4))
            block.append(Paragraph(
                f'<b>Nota del equipo:</b> {item.notes}'.replace('\n', '<br/>'),
                styles['Cell']
            ))

        # Fotos antes / después
        before_path = os.path.join(upload_folder, item.photo_before) if item.photo_before else None
        after_path = os.path.join(upload_folder, item.photo_after) if item.photo_after else None
        before_ok = before_path and os.path.exists(before_path)
        after_ok = after_path and os.path.exists(after_path)

        if before_ok or after_ok:
            block.append(Spacer(1, 6))
            img_w, img_h = 75 * mm, 55 * mm

            def img_cell(path, ok, label):
                if ok:
                    try:
                        img = Image(path)
                        img._restrictSize(img_w, img_h)
                        return [Paragraph(label, styles['CellMuted']), img]
                    except Exception:
                        return [Paragraph(label, styles['CellMuted']),
                                Paragraph('(No se pudo cargar la imagen)', styles['CellMuted'])]
                return [Paragraph(label, styles['CellMuted']),
                        Paragraph('<font color="#94a3b8">Sin foto</font>', styles['CellMuted'])]

            photos_table = Table(
                [[Paragraph('<b>ANTES</b>', styles['Cell']), Paragraph('<b>DESPUÉS</b>', styles['Cell'])],
                 [img_cell(before_path, before_ok, ''), img_cell(after_path, after_ok, '')]],
                colWidths=[85 * mm, 85 * mm]
            )
            photos_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_LIGHT),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            block.append(photos_table)

        block.append(Spacer(1, 8))
        # Mantener cada equipo en una misma página cuando sea posible
        flowables.append(KeepTogether(block))

    return flowables


def generate_maintenance_event_pdf(event, upload_folder):
    """Genera el PDF del evento y devuelve un BytesIO listo para enviar."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title=f'Informe de Mantenimiento Evento #{event.id}',
        author='LEGO TICS SAS',
    )
    styles = _build_styles()

    story = []
    story.extend(_header_block(event, styles))
    story.append(Spacer(1, 14))

    if event.items:
        story.append(Paragraph('Resumen de Equipos', styles['SectionTitle']))
        story.append(_equipment_summary_table(event, styles))
        story.append(Spacer(1, 14))
        story.extend(_equipment_detail(event, upload_folder, styles))

        # Totales
        story.append(Spacer(1, 6))
        total_txt = f'Total de equipos intervenidos: <b>{len(event.items)}</b>'
        story.append(Paragraph(total_txt, styles['Cell']))
    else:
        story.append(Paragraph('Este evento no tiene equipos asociados.', styles['Cell']))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)
    return buffer
