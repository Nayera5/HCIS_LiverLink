"""
CSV and PDF downloads of a report built by apps.reporting.reports (same report shape).
PDFs use reportlab, already used for billing receipts.
"""
import csv
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from django.http import FileResponse, HttpResponse
from django.utils import timezone


def export_filename(report, extension):
    return f"liverlink-{report['key'].replace('_', '-')}-{timezone.localdate():%Y%m%d}.{extension}"


def period_text(report):
    period = report['period']
    if not period['date_from'] and not period['date_to']:
        return 'All time'
    return f"{period['date_from'] or 'start'} to {period['date_to'] or 'today'}"


def report_to_csv(report):
    """One CSV file: title and period, the summary, then each section as its own table."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([report['title']])
    writer.writerow(['Period', period_text(report)])
    writer.writerow([])
    writer.writerow(['Summary'])
    for item in report['summary']:
        writer.writerow([item['label'], item['value']])
    for section in report['sections']:
        writer.writerow([])
        writer.writerow([section['title']])
        writer.writerow(section['columns'])
        writer.writerows(section['rows'])
        if not section['rows']:
            writer.writerow(['No data for this period'])

    # UTF-8 with BOM so Excel shows non-ASCII names correctly.
    response = HttpResponse(buffer.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{export_filename(report, "csv")}"'
    return response


def report_to_pdf(report):
    """An A4 PDF: title, period, a summary table and one table per section."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    cell = styles['BodyText'].clone('cell', fontSize=8, leading=10)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f3f4')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d3dbe3')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    def table(header, rows):
        data = [[Paragraph(escape(str(value)), cell) for value in header]]
        data += [[Paragraph(escape(str(value)), cell) for value in row] for row in rows]
        result = Table(data, repeatRows=1, hAlign='LEFT')
        result.setStyle(table_style)
        return result

    story = [
        Paragraph(escape(f"LiverLink — {report['title']}"), styles['Title']),
        Paragraph(f"Period: {period_text(report)} · Generated {timezone.localtime():%Y-%m-%d %H:%M}",
                  styles['Normal']),
        Spacer(1, 0.5 * cm),
        Paragraph('Summary', styles['Heading2']),
        table(['Measure', 'Value'], [[item['label'], item['value']] for item in report['summary']]),
    ]
    for section in report['sections']:
        story += [Spacer(1, 0.4 * cm), Paragraph(escape(section['title']), styles['Heading2'])]
        if section['rows']:
            story.append(table(section['columns'], section['rows']))
        else:
            story.append(Paragraph('No data for this period.', styles['Normal']))

    buffer = BytesIO()
    # Landscape so wide tables (e.g. unpaid invoices) fit on the page.
    SimpleDocTemplate(buffer, pagesize=landscape(A4), title=report['title'],
                      leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm
                      ).build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=export_filename(report, 'pdf'),
                        content_type='application/pdf')
