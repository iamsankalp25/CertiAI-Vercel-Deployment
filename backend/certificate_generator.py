import os
import zipfile

from PIL import Image, ImageStat
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth


# --------------------------------------------------
# Existing certificate templates
# --------------------------------------------------

TEMPLATES = {
    "classic": {
        "background": "#FFFCF3",
        "primary": "#B8860B",
        "secondary": "#E6C86E",
        "title": "#292524",
        "text": "#57534E",
        "accent": "#92700C",
    },
    "modern": {
        "background": "#F7F5FF",
        "primary": "#6D28D9",
        "secondary": "#C4B5FD",
        "title": "#2E1065",
        "text": "#5B556B",
        "accent": "#7C3AED",
    },
    "elegant": {
        "background": "#F3FAF5",
        "primary": "#166534",
        "secondary": "#86C79A",
        "title": "#163B28",
        "text": "#4B6353",
        "accent": "#15803D",
    },
}


# --------------------------------------------------
# Utility functions
# --------------------------------------------------

def safe_filename(name):
    name = str(name).strip()
    invalid_chars = '<>:"/\\|?*'

    for char in invalid_chars:
        name = name.replace(char, "")

    return name if name else "Certificate"


def draw_centered_text(c, text, y, font="Helvetica", size=16, color="#222222"):
    width = c._pagesize[0]
    text = str(text)

    c.setFont(font, size)
    c.setFillColor(HexColor(color))

    text_width = stringWidth(text, font, size)
    c.drawString((width - text_width) / 2, y, text)


def draw_wrapped_centered_text(
    c, text, y, max_width, font, size, color, leading=None
):
    text = str(text)
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()

        if stringWidth(test_line, font, size) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    if not lines:
        lines = [""]

    line_height = leading or size * 1.4

    for line in lines:
        draw_centered_text(c, line, y, font, size, color)
        y -= line_height

    return y


def get_custom_page_size(image_path):
    """
    Create a PDF page with the same aspect ratio as the uploaded image.
    This avoids stretching or cropping landscape certificate designs.
    """
    with Image.open(image_path) as image:
        image_width, image_height = image.size

    if image_width <= 0 or image_height <= 0:
        raise ValueError("The uploaded certificate image has invalid dimensions.")

    ratio = image_width / image_height
    longest_side = 842.0

    if ratio >= 1:
        return longest_side, longest_side / ratio

    return longest_side * ratio, longest_side


# --------------------------------------------------
# Existing template design
# --------------------------------------------------

def draw_certificate_design(c, width, height, template):
    colors = TEMPLATES[template]

    c.setFillColor(HexColor(colors["background"]))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(HexColor(colors["primary"]))
    c.setLineWidth(4)
    c.rect(35, 35, width - 70, height - 70, fill=0, stroke=1)

    c.setStrokeColor(HexColor(colors["secondary"]))
    c.setLineWidth(1.3)
    c.rect(49, 49, width - 98, height - 98, fill=0, stroke=1)

    if template == "classic":
        c.setStrokeColor(HexColor(colors["primary"]))
        c.setLineWidth(2)

        for x, y, dx, dy in [
            (58, 58, 1, 1),
            (width - 58, 58, -1, 1),
            (58, height - 58, 1, -1),
            (width - 58, height - 58, -1, -1),
        ]:
            c.line(x, y, x + dx * 22, y)
            c.line(x, y, x, y + dy * 22)

    elif template == "modern":
        c.setFillColor(HexColor(colors["primary"]))
        c.rect(50, height - 62, width - 100, 5, fill=1, stroke=0)
        c.rect(50, 57, width - 100, 5, fill=1, stroke=0)

        c.setFillColor(HexColor(colors["secondary"]))
        c.circle(67, height - 78, 5, fill=1, stroke=0)
        c.circle(width - 67, height - 78, 5, fill=1, stroke=0)

    elif template == "elegant":
        c.setFillColor(HexColor(colors["secondary"]))
        c.rect(50, 80, 5, height - 160, fill=1, stroke=0)
        c.rect(width - 55, 80, 5, height - 160, fill=1, stroke=0)

        c.setStrokeColor(HexColor(colors["primary"]))
        c.setLineWidth(1.5)
        c.line(150, height - 83, width - 150, height - 83)
        c.line(150, 83, width - 150, 83)


# --------------------------------------------------
# Custom template: image background and text placement
# --------------------------------------------------

def get_custom_text_color(image_path):
    """
    Estimate a readable text color from the central portion of the image.
    This is a simple brightness estimate, not semantic blank-area detection.
    """
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")

        width, height = image.size

        # Sample the central region where participant details are placed.
        left = int(width * 0.25)
        top = int(height * 0.25)
        right = int(width * 0.75)
        bottom = int(height * 0.75)

        sample = image.crop((left, top, right, bottom))
        sample.thumbnail((100, 100))

        brightness = ImageStat.Stat(sample).mean
        average_brightness = sum(brightness) / 3

        return "#222222" if average_brightness > 145 else "#FFFFFF"

    except Exception:
        return "#222222"


def draw_custom_template(c, width, height, image_path, record):
    """
    Draw the uploaded design as the page background and place participant
    information at proportional positions on the certificate.
    """
    if not image_path or not os.path.isfile(image_path):
        raise FileNotFoundError("Custom template image was not found.")

    with Image.open(image_path) as image:
        image.verify()

    # The PDF page uses the image's aspect ratio, so fill the page cleanly.
    c.drawImage(
        ImageReader(image_path),
        0,
        0,
        width=width,
        height=height,
        preserveAspectRatio=False,
        mask="auto",
    )

    text_color = get_custom_text_color(image_path)
    center_x = width / 2

    organization = str(record.get("Organization", "")).strip()
    name = str(record.get("Name", "")).strip()
    event = str(record.get("Event", "")).strip()
    date = str(record.get("Date", "")).strip()
    achievement = str(record.get("Achievement", "")).strip()
    certificate_id = str(record.get("certificate_id", "N/A"))

    max_text_width = width * 0.76

    def draw_auto_text(text, y_position, font, size, color):
        text = str(text)

        while (
            stringWidth(text, font, size) > max_text_width
            and size > 8
        ):
            size -= 1

        c.setFont(font, size)
        c.setFillColor(HexColor(color))

        text_width = stringWidth(text, font, size)
        c.drawString(center_x - text_width / 2, y_position, text)

    # Text positions are proportional to the uploaded design's page size.
    # They are a practical default; different artwork may need adjustment.
    draw_auto_text(
        organization,
        height * 0.79,
        "Helvetica-Bold",
        17,
        text_color,
    )

    draw_auto_text(
        "CERTIFICATE",
        height * 0.70,
        "Helvetica-Bold",
        27,
        text_color,
    )

    draw_auto_text(
        "OF ACHIEVEMENT",
        height * 0.66,
        "Helvetica-Bold",
        13,
        text_color,
    )

    draw_auto_text(
        "This certificate is presented to",
        height * 0.59,
        "Helvetica",
        12,
        text_color,
    )

    name_size = 29
    while (
        stringWidth(name, "Helvetica-Bold", name_size) > max_text_width
        and name_size > 14
    ):
        name_size -= 1

    draw_auto_text(
        name,
        height * 0.51,
        "Helvetica-Bold",
        name_size,
        text_color,
    )

    draw_wrapped_centered_text(
        c,
        achievement,
        height * 0.43,
        max_text_width,
        "Helvetica-Bold",
        13,
        text_color,
        18,
    )

    draw_wrapped_centered_text(
        c,
        f"For participating in {event}",
        height * 0.35,
        max_text_width,
        "Helvetica",
        11,
        text_color,
        16,
    )

    draw_auto_text(
        f"Date: {date}",
        height * 0.25,
        "Helvetica",
        11,
        text_color,
    )

    draw_auto_text(
        f"Certificate ID: {certificate_id}",
        height * 0.20,
        "Helvetica-Bold",
        9,
        text_color,
    )


# --------------------------------------------------
# Generate one certificate
# --------------------------------------------------

def generate_certificate(
    record,
    output_folder,
    template="classic",
    custom_template_path=None,
):
    os.makedirs(output_folder, exist_ok=True)

    if template not in TEMPLATES and template != "custom":
        template = "classic"

    name = str(record.get("Name", "Certificate")).strip()
    certificate_id = str(record.get("certificate_id", "")).strip()

    # Add the unique ID to the filename so repeated participant names
    # never overwrite one another.
    filename_base = safe_filename(name)

    if certificate_id:
        filename_base = f"{filename_base}_{safe_filename(certificate_id)}"

    filename = f"{filename_base}.pdf"
    output_path = os.path.join(output_folder, filename)

    if template == "custom":
        if not custom_template_path:
            raise ValueError("A custom template image is required.")

        width, height = get_custom_page_size(custom_template_path)
        page_size = (width, height)
    else:
        page_size = A4
        width, height = page_size

    c = canvas.Canvas(output_path, pagesize=page_size)

    if template == "custom":
        draw_custom_template(
            c,
            width,
            height,
            custom_template_path,
            record,
        )

    else:
        colors = TEMPLATES[template]

        event = str(record.get("Event", "")).strip()
        organization = str(record.get("Organization", "")).strip()
        date = str(record.get("Date", "")).strip()
        achievement = str(record.get("Achievement", "")).strip()
        certificate_id = str(record.get("certificate_id", "N/A"))

        draw_certificate_design(c, width, height, template)

        draw_wrapped_centered_text(
            c, organization, height - 125, width - 150,
            "Helvetica-Bold", 18, colors["primary"], 23
        )

        draw_centered_text(
            c, "CERTIFICATE", height - 190,
            "Helvetica-Bold", 31, colors["title"]
        )

        draw_centered_text(
            c, "OF ACHIEVEMENT", height - 220,
            "Helvetica-Bold", 14, colors["accent"]
        )

        divider_y = height - 245
        c.setStrokeColor(HexColor(colors["secondary"]))
        c.setLineWidth(1.5)
        c.line(175, divider_y, width - 175, divider_y)

        draw_centered_text(
            c, "This certificate is proudly presented to",
            height - 285, "Helvetica", 13, colors["text"]
        )

        name_size = 28

        while (
            stringWidth(name, "Helvetica-Bold", name_size) > width - 130
            and name_size > 16
        ):
            name_size -= 1

        draw_centered_text(
            c, name, height - 340,
            "Helvetica-Bold", name_size, colors["primary"]
        )

        c.setStrokeColor(HexColor(colors["secondary"]))
        c.setLineWidth(1.5)
        c.line(130, height - 355, width - 130, height - 355)

        draw_wrapped_centered_text(
            c, achievement, height - 400, width - 120,
            "Helvetica-Bold", 14, colors["title"], 19
        )

        draw_wrapped_centered_text(
            c, f"for participating in {event}",
            height - 450, width - 120,
            "Helvetica", 12, colors["text"], 17
        )

        draw_centered_text(
            c, f"Date: {date}", height - 505,
            "Helvetica", 12, colors["text"]
        )

        draw_centered_text(
            c, f"Certificate ID: {certificate_id}",
            height - 532, "Helvetica-Bold", 10, colors["primary"]
        )

        c.setStrokeColor(HexColor(colors["primary"]))
        c.setLineWidth(1)

        c.line(85, 135, 245, 135)
        c.line(width - 245, 135, width - 85, 135)

        draw_centered_text(
            c, "Authorized Signature", 115,
            "Helvetica", 10, colors["text"]
        )

        right_text = "Certificate Authority"
        right_width = stringWidth(right_text, "Helvetica", 10)

        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor(colors["text"]))
        c.drawString(
            width - 165 - right_width / 2,
            115,
            right_text,
        )

        draw_centered_text(
            c, "Generated by CertiAI", 75,
            "Helvetica", 9, colors["text"]
        )

    c.save()
    return output_path


# --------------------------------------------------
# Generate certificates in bulk
# --------------------------------------------------

def generate_bulk_certificates(
    records,
    output_folder,
    template="classic",
    custom_template_path=None,
):
    os.makedirs(output_folder, exist_ok=True)

    if template not in TEMPLATES and template != "custom":
        template = "classic"

    generated_files = []

    for record in records:
        pdf_path = generate_certificate(
            record,
            output_folder,
            template=template,
            custom_template_path=custom_template_path,
        )
        generated_files.append(pdf_path)

    zip_path = os.path.join(output_folder, "certificates.zip")

    with zipfile.ZipFile(
        zip_path, "w", zipfile.ZIP_DEFLATED
    ) as zip_file:
        for pdf_path in generated_files:
            zip_file.write(
                pdf_path,
                os.path.basename(pdf_path),
            )

    return zip_path, generated_files
