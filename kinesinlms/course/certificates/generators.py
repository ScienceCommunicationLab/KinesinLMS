import io
from typing import List

from django.conf import settings
from django.utils import formats
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Frame, BaseDocTemplate, PageTemplate, Paragraph, Image, Table, Spacer

from kinesinlms.certificates.models import Certificate, Signatory


def draw_certificate_borders(canvas, doc):   # noqa: F841
    canvas.setPageSize(landscape(letter))

    # Save the current settings
    canvas.saveState()

    # Draw the static stuff

    # create borders
    upper_left_border_img = ImageReader(f"{settings.APPS_DIR}/static/certificates/images/upper-left-corner.png")
    upper_right_border_img = ImageReader(f"{settings.APPS_DIR}/static/certificates/images/upper-right-corner.png")
    bottom_left_border_img = ImageReader(f"{settings.APPS_DIR}/static/certificates/images/bottom-left-corner.png")
    bottom_right_border_img = ImageReader(f"{settings.APPS_DIR}/static/certificates/images/bottom-right-corner.png")

    canvas.drawImage(upper_left_border_img, 0.2 * inch, 7.2 * inch, width=74, height=74)
    canvas.drawImage(upper_right_border_img, 9.7 * inch, 7.2 * inch, width=74, height=74)
    canvas.drawImage(bottom_left_border_img, 0.2 * inch, 0.2 * inch, width=74, height=74)
    canvas.drawImage(bottom_right_border_img, 9.7 * inch, 0.2 * inch, width=74, height=74)

    # Restore setting to before function call
    canvas.restoreState()


def generate_custom_certificate(certificate: Certificate) -> io.BytesIO:   # noqa: F841
    """
    Create PDF representation of a certificate with a custom template.
    TODO:
        Use PDFKit or similar to get rid of this custom code
        and just use HTML templates..
    """
    raise NotImplemented("Custom certificates are not yet implemented.")


def generate_base_certificate(certificate: Certificate) -> io.BytesIO:
    """
    Generate a PDF version of a course completion certificate.
    """

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    doc = BaseDocTemplate(buffer, pagesize=letter)

    # Create a Frame for the Flowables part of the certificate
    landscape_frame = Frame(1 * inch, 1 * inch, 9 * inch, 6.5 * inch,
                            leftPadding=0, rightPadding=0,
                            topPadding=0, bottomPadding=0,
                            id='landscape_frame')

    # Add the Frame to the template and tell the template to call draw_static for each page
    template = PageTemplate(id='test', frames=[landscape_frame], onPage=draw_certificate_borders)

    # Add the template to the doc
    doc.addPageTemplates([template])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='student_name',
                              alignment=TA_CENTER,
                              fontSize=22,
                              leading=24,
                              spaceBefore=40,
                              spaceAfter=20))
    styles.add(ParagraphStyle(name='course_name',
                              alignment=TA_CENTER,
                              fontSize=22,
                              leading=24,
                              spaceBefore=20,
                              spaceAfter=20))
    styles.add(ParagraphStyle(name='normal',
                              alignment=TA_CENTER,
                              leftIndent=20,
                              rightIndent=20,
                              fontSize=16,
                              leading=22,
                              spaceAfter=6))
    styles.add(ParagraphStyle(name='muted',
                              alignment=TA_CENTER,
                              fontSize=12,
                              leading=14,
                              textColor="#999999"))
    styles.add(ParagraphStyle(name='signature_name',
                              alignment=TA_CENTER,
                              spaceBefore=4,
                              spaceAfter=10,
                              fontSize=12,
                              leading=14))
    styles.add(ParagraphStyle(name='signature_info',
                              alignment=TA_CENTER,
                              fontSize=10,
                              leading=14))

    # container for pdf elements
    elements = []

    logo = Image(f"{settings.APPS_DIR}/static/certificates/images/site-logo-certificate.png",
                 width=254,
                 height=83)
    elements.append(logo)

    student_name_p = Paragraph(certificate.student_name, styles["student_name"])
    elements.append(student_name_p)

    achievement_text = "successfully completed, received a passing grade, and was awarded<br/>" \
                       "this KinesinLMS Certificate of Completion in "
    achievement_p = Paragraph(achievement_text, styles["normal"])
    elements.append(achievement_p)

    course_p = Paragraph(certificate.course_name, styles["course_name"])
    elements.append(course_p)

    date_text = formats.date_format(certificate.created_at)
    date_p = Paragraph(f"Date awarded: {date_text}", styles["normal"])
    elements.append(date_p)

    cert_id_text = f"Certificate ID: {certificate.uuid}"
    cert_id_p = Paragraph(cert_id_text, styles["muted"])
    elements.append(cert_id_p)
    elements.append(Spacer(1, 10))

    sigs = []
    signatories: List[Signatory] = certificate.certificate_template.signatories.all()
    for signatory in signatories:
        sig_image = Image(signatory.signature_image.path, width=156, height=52)
        sig_p = Paragraph(signatory.name, styles['signature_name'])
        sig_info_p = Paragraph(signatory.title, styles['signature_info'])
        sig_parts = [sig_image, sig_p, sig_info_p]
        if signatory.organization:
            sig_org = Paragraph(signatory.organization, styles['signature_info'])
            sig_parts.append(sig_org)
        sigs.append(sig_parts)

    sig_table_data = [
        [
            sigs
        ]
    ]

    sig_table = Table(sig_table_data, style=[
        ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'), ])
    elements.append(sig_table)

    doc.build(elements)

    return buffer
