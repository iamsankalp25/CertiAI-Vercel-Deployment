
import os
import zipfile

from PIL import Image, ImageStat
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth


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


DEFAULT_CUSTOM_LAYOUT = {
    "organization": {
        "x": 0.5, "y": 0.21,
        "font_size": 17, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
    "title": {
        "x": 0.5, "y": 0.30,
        "font_size": 27, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
    "subtitle": {
        "x": 0.5, "y": 0.34,
        "font_size": 13, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
    "intro": {
        "x": 0.5, "y": 0.41,
        "font_size": 12, "color": "#222222",
        "bold": False, "align": "center", "visible": True
    },
    "name": {
        "x": 0.5, "y": 0.49,
        "font_size": 29, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
    "achievement": {
        "x": 0.5, "y": 0.57,
        "font_size": 13, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
    "event": {
        "x": 0.5, "y": 0.65,
        "font_size": 11, "color": "#222222",
        "bold": False, "align": "center", "visible": True
    },
    "date": {
        "x": 0.5, "y": 0.75,
        "font_size": 11, "color": "#222222",
        "bold": False, "align": "center", "visible": True
    },
    "certificate_id": {
        "x": 0.5, "y": 0.80,
        "font_size": 9, "color": "#222222",
        "bold": True, "align": "center", "visible": True
    },
}


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
    with Image.open(image_path) as image:
        image_width, image_height = image.size

    if image_width <= 0 or image_height <= 0:
        raise ValueError("The uploaded certificate image has invalid dimensions.")

    ratio = image_width / image_height
    longest_side = 842.0

    if ratio >= 1:
        return longest_side, longest_side / ratio

    return longest_side * ratio, longest_side


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


def get_custom_text_color(image_path):
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")

        width, height = image.size

        sample = image.crop((
            int(width * 0.25),
            int(height * 0.25),
            int(width * 0.75),
            int(height * 0.75),
        ))

        sample.thumbnail((100, 100))

        brightness = ImageStat.Stat(sample).mean
        average_brightness = sum(brightness) / 3

        return "#222222" if average_brightness > 145 else "#FFFFFF"

    except Exception:
        return "#222222"


def get_custom_layout(layout=None):
    """Merge saved settings while preserving explicitly hidden fields."""
    result = {}

    for field, default_settings in DEFAULT_CUSTOM_LAYOUT.items():
        settings = dict(default_settings)

        if isinstance(layout, dict):
            saved_settings = layout.get(field)

            if isinstance(saved_settings, dict):
                settings.update(saved_settings)

        result[field] = settings

    return result


def draw_custom_field(c, width, height, text, settings):
    """Draw a field only when its saved visibility setting is enabled."""

    if not settings.get("visible", True):
        return

    text = str(text).strip()

    if not text:
        return

    try:
        x = float(settings.get("x", 0.5))
        y = float(settings.get("y", 0.5))
        size = float(settings.get("font_size", 12))
        color = str(settings.get("color", "#222222"))
        alignment = str(settings.get("align", "center")).lower()
        bold = settings.get("bold", False)

        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        size = max(6.0, min(80.0, size))

        if alignment not in {"left", "center", "right"}:
            alignment = "center"

        if not color.startswith("#") or len(color) not in {4, 7}:
            color = "#222222"

        font = "Helvetica-Bold" if bold else "Helvetica"

        pdf_x = width * x
        pdf_y = height * (1.0 - y)

        max_text_width = width * 0.85

        while stringWidth(text, font, size) > max_text_width and size > 6:
            size -= 1

        text_width = stringWidth(text, font, size)

        if alignment == "center":
            draw_x = pdf_x - text_width / 2
        elif alignment == "right":
            draw_x = pdf_x - text_width
        else:
            draw_x = pdf_x

        c.setFont(font, size)
        c.setFillColor(HexColor(color))
        c.drawString(draw_x, pdf_y, text)

    except (TypeError, ValueError):
        raise ValueError("Invalid custom template field settings.")


def draw_custom_template(
    c,
    width,
    height,
    image_path,
    record,
    layout=None,
):
    """Draw the uploaded image and only the visible participant text fields."""

    if not image_path or not os.path.isfile(image_path):
        raise FileNotFoundError("Custom template image was not found.")

    with Image.open(image_path) as image:
        image.verify()

    c.drawImage(
        ImageReader(image_path),
        0,
        0,
        width=width,
        height=height,
        preserveAspectRatio=False,
        mask="auto",
    )

    default_color = get_custom_text_color(image_path)
    fields = get_custom_layout(layout)

    for field_settings in fields.values():
        if field_settings.get("color") == "#222222":
            field_settings["color"] = default_color

    field_values = {
        "organization": record.get("Organization", ""),
        "title": "CERTIFICATE",
        "subtitle": "OF ACHIEVEMENT",
        "intro": "This certificate is presented to",
        "name": record.get("Name", ""),
        "achievement": record.get("Achievement", ""),
        "event": f"For participating in {record.get('Event', '')}",
        "date": f"Date: {record.get('Date', '')}",
        "certificate_id": (
            f"Certificate ID: {record.get('certificate_id', 'N/A')}"
        ),
    }

    for field, value in field_values.items():
        draw_custom_field(
            c,
            width,
            height,
            value,
            fields[field],
        )


def generate_certificate(
    record,
    output_folder,
    template="classic",
    custom_template_path=None,
    custom_template_layout=None,
):
    os.makedirs(output_folder, exist_ok=True)

    if template not in TEMPLATES and template != "custom":
        template = "classic"

    name = str(record.get("Name", "Certificate")).strip()
    certificate_id = str(record.get("certificate_id", "")).strip()

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
            layout=custom_template_layout,
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


def generate_bulk_certificates(
    records,
    output_folder,
    template="classic",
    custom_template_path=None,
    custom_template_layout=None,
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
            custom_template_layout=custom_template_layout,
        )

        generated_files.append(pdf_path)

    zip_path = os.path.join(output_folder, "certificates.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for pdf_path in generated_files:
            zip_file.write(
                pdf_path,
                os.path.basename(pdf_path),
            )

    return zip_path, generated_files
