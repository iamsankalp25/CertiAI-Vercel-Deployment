
import os
import sys
import uuid

from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image


# --------------------------------------------------
# Backend path configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# --------------------------------------------------
# Import backend modules
# --------------------------------------------------

from excel_processor import (
    read_excel,
    validate_columns,
    validate_data,
)

from certificate_generator import generate_bulk_certificates

from database import (
    initialize_database,
    get_all_certificates,
    get_certificate,
    get_connection,
    save_template_layout,
    get_template_layout,
)


# --------------------------------------------------
# Flask application and CORS
# --------------------------------------------------

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://www.web-a2z.com",
                "https://web-a2z.com",
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:5501",
                "http://localhost:5501"
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    }
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# --------------------------------------------------
# Folders and configuration
# --------------------------------------------------

if os.environ.get("VERCEL"):
    STORAGE_DIR = Path("/tmp/certiai")
else:
    STORAGE_DIR = BASE_DIR

UPLOAD_FOLDER = STORAGE_DIR / "uploads"
GENERATED_FOLDER = STORAGE_DIR / "generated"
CUSTOM_TEMPLATE_FOLDER = STORAGE_DIR / "custom_templates"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_FOLDER.mkdir(parents=True, exist_ok=True)
CUSTOM_TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)


ALLOWED_TEMPLATES = {
    "classic",
    "modern",
    "elegant",
    "custom",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
}


# --------------------------------------------------
# Temporary application state
# --------------------------------------------------

uploaded_records = []
uploaded_batch_token = None

custom_template_path = None
custom_template_id = None


# --------------------------------------------------
# Initialize database
# --------------------------------------------------

initialize_database()


# --------------------------------------------------
# Home route
# --------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "CertiAI Backend is running",
    })


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "success": True,
        "status": "running",
    })


# --------------------------------------------------
# Upload Excel or CSV
# --------------------------------------------------

@app.route("/api/upload-excel", methods=["POST"])
def upload_excel():
    global uploaded_records, uploaded_batch_token

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file uploaded",
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "success": False,
            "message": "No file selected",
        }), 400

    extension = Path(file.filename).suffix.lower()

    if extension not in {".xlsx", ".xls", ".csv"}:
        return jsonify({
            "success": False,
            "message": "Only Excel or CSV files are allowed",
        }), 400

    unique_name = f"{uuid.uuid4().hex}{extension}"
    file_path = UPLOAD_FOLDER / unique_name

    try:
        file.save(file_path)

        records = read_excel(str(file_path))

        column_errors = validate_columns(records)

        if column_errors:
            return jsonify({
                "success": False,
                "message": "Invalid Excel columns",
                "errors": column_errors,
            }), 400

        validation_errors = validate_data(records)

        uploaded_records = records
        uploaded_batch_token = uuid.uuid4().hex

        return jsonify({
            "success": True,
            "message": "File uploaded successfully",
            "filename": file.filename,
            "total_records": len(records),
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "records": records,
        })

    except Exception as error:
        app.logger.exception("Excel processing failed")

        return jsonify({
            "success": False,
            "message": f"Error processing file: {str(error)}",
        }), 500


# --------------------------------------------------
# Upload custom certificate image
# --------------------------------------------------

@app.route("/api/upload-template", methods=["POST"])
def upload_custom_template():
    global custom_template_path, custom_template_id

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "Please select a certificate image",
        }), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({
            "success": False,
            "message": "No image selected",
        }), 400

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "success": False,
            "message": "Only PNG, JPG and JPEG images are allowed",
        }), 400

    try:
        image = Image.open(file.stream)
        image.verify()

        file.stream.seek(0)
        image = Image.open(file.stream)

        if image.format not in {"PNG", "JPEG"}:
            return jsonify({
                "success": False,
                "message": "Invalid image format",
            }), 400

        width, height = image.size

        if width < 500 or height < 300:
            return jsonify({
                "success": False,
                "message": (
                    "Please upload a higher-resolution certificate image"
                ),
            }), 400

        template_id = uuid.uuid4().hex
        filename = f"{template_id}{extension}"
        save_path = CUSTOM_TEMPLATE_FOLDER / filename

        image.save(save_path)

        save_template_layout(
            template_id=template_id,
            filename=filename,
            image_width=width,
            image_height=height,
            layout={},
        )

        custom_template_path = save_path
        custom_template_id = template_id

        return jsonify({
            "success": True,
            "message": "Custom certificate design uploaded successfully",
            "template_id": template_id,
            "filename": file.filename,
            "width": width,
            "height": height,
        })

    except Exception:
        app.logger.exception("Custom template upload failed")

        return jsonify({
            "success": False,
            "message": "Invalid or corrupted certificate image",
        }), 400


# --------------------------------------------------
# Save and retrieve custom template layout
# --------------------------------------------------

@app.route(
    "/api/template-layout/<template_id>",
    methods=["GET", "POST", "OPTIONS"],
)
def template_layout(template_id):
    global custom_template_path, custom_template_id

    # Handle browser CORS preflight request.
    if request.method == "OPTIONS":
        return "", 204

    # Retrieve saved layout.
    if request.method == "GET":
        try:
            template = get_template_layout(template_id)

            if not template:
                return jsonify({
                    "success": False,
                    "message": "Template layout not found",
                }), 404

            return jsonify({
                "success": True,
                "template": template,
            }), 200

        except Exception as error:
            app.logger.exception("Template layout retrieval failed")

            return jsonify({
                "success": False,
                "message": str(error),
            }), 500

    # Save layout.
    if request.method == "POST":

        if (
            not custom_template_id
            or template_id != custom_template_id
            or not custom_template_path
            or not custom_template_path.is_file()
        ):
            return jsonify({
                "success": False,
                "message": "Custom template not found. Please upload it again.",
            }), 404

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "A valid JSON layout is required",
            }), 400

        layout = data.get("layout")

        if not isinstance(layout, dict):
            return jsonify({
                "success": False,
                "message": "Layout must be a JSON object",
            }), 400

        if len(str(layout)) > 50000:
            return jsonify({
                "success": False,
                "message": "Layout data is too large",
            }), 400

        try:
            existing_template = get_template_layout(template_id)

            if not existing_template:
                return jsonify({
                    "success": False,
                    "message": "Template metadata not found",
                }), 404

            save_template_layout(
                template_id=template_id,
                filename=existing_template["filename"],
                image_width=existing_template["image_width"],
                image_height=existing_template["image_height"],
                layout=layout,
            )

            return jsonify({
                "success": True,
                "message": "Template layout saved successfully",
                "template_id": template_id,
                "layout": layout,
            }), 200

        except Exception as error:
            app.logger.exception("Template layout save failed")

            return jsonify({
                "success": False,
                "message": f"Could not save template layout: {str(error)}",
            }), 500


# --------------------------------------------------
# Generate certificates and save to SQLite
# --------------------------------------------------

@app.route("/api/generate-certificates", methods=["POST"])
def generate_certificates():
    global uploaded_records, uploaded_batch_token
    global custom_template_path, custom_template_id

    if not uploaded_records:
        return jsonify({
            "success": False,
            "message": "Please upload an Excel file first",
        }), 400

    if not uploaded_batch_token:
        return jsonify({
            "success": False,
            "message": "Please upload the Excel file again",
        }), 400

    data = request.get_json(silent=True) or {}

    template = data.get("template", "classic")

    if not isinstance(template, str):
        template = "classic"

    template = template.strip().lower()

    if template not in ALLOWED_TEMPLATES:
        return jsonify({
            "success": False,
            "message": "Invalid template selected",
            "allowed_templates": sorted(ALLOWED_TEMPLATES),
        }), 400

    selected_custom_path = None
    selected_custom_layout = None

    if template == "custom":
        requested_template_id = data.get("custom_template_id")

        if (
            not custom_template_path
            or not custom_template_path.is_file()
            or not custom_template_id
            or requested_template_id != custom_template_id
        ):
            return jsonify({
                "success": False,
                "message": "Please upload a custom certificate design first",
            }), 400

        selected_custom_path = custom_template_path

        selected_template = get_template_layout(custom_template_id)

        if not selected_template:
            return jsonify({
                "success": False,
                "message": "Custom template layout not found",
            }), 400

        selected_custom_layout = selected_template.get("layout", {})

    validation_errors = validate_data(uploaded_records)

    if validation_errors:
        return jsonify({
            "success": False,
            "message": "Please correct the invalid participant data",
            "errors": validation_errors,
        }), 400

    batch_id = uploaded_batch_token

    output_folder = GENERATED_FOLDER / batch_id
    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        records_with_ids = []

        for record in uploaded_records:
            updated_record = dict(record)

            updated_record["certificate_id"] = (
                uuid.uuid4().hex[:12].upper()
            )

            records_with_ids.append(updated_record)

        if template == "custom":
            zip_path, generated_files = generate_bulk_certificates(
                records_with_ids,
                str(output_folder),
                template="custom",
                custom_template_path=str(selected_custom_path),
                custom_template_layout=selected_custom_layout,
            )
        else:
            zip_path, generated_files = generate_bulk_certificates(
                records_with_ids,
                str(output_folder),
                template=template,
            )

        if len(generated_files) != len(records_with_ids):
            raise RuntimeError(
                "Not all certificates were generated"
            )

        with get_connection() as connection:
            for record in records_with_ids:
                connection.execute(
                    """
                    INSERT INTO certificates (
                        certificate_id,
                        participant_name,
                        event,
                        organization,
                        certificate_date,
                        achievement,
                        generated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["certificate_id"],
                        str(record["Name"]).strip(),
                        str(record["Event"]).strip(),
                        str(record["Organization"]).strip(),
                        str(record["Date"]).strip(),
                        str(record["Achievement"]).strip(),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

        return jsonify({
            "success": True,
            "message": (
                f"Certificates generated successfully "
                f"using the {template} template"
            ),
            "template": template,
            "total_certificates": len(generated_files),
            "download_url": f"/api/download/{batch_id}",
        })

    except Exception as error:
        app.logger.exception("Certificate generation failed")

        return jsonify({
            "success": False,
            "message": (
                f"Certificate generation failed: {str(error)}"
            ),
        }), 500


# --------------------------------------------------
# List saved certificates
# --------------------------------------------------

@app.route("/api/certificates", methods=["GET"])
def list_certificates():
    try:
        records = get_all_certificates()

        return jsonify({
            "success": True,
            "total": len(records),
            "certificates": records,
        })

    except Exception as error:
        app.logger.exception("Could not retrieve certificates")

        return jsonify({
            "success": False,
            "message": str(error),
        }), 500


# --------------------------------------------------
# Verify certificate by ID
# --------------------------------------------------

@app.route("/api/verify/<certificate_id>", methods=["GET"])
def verify_certificate(certificate_id):
    record = get_certificate(certificate_id)

    if record is None:
        return jsonify({
            "success": False,
            "verified": False,
            "message": "Certificate not found",
        }), 404

    return jsonify({
        "success": True,
        "verified": True,
        "certificate": record,
    })


# --------------------------------------------------
# Download generated certificates ZIP
# --------------------------------------------------

@app.route("/api/download/<batch_id>", methods=["GET"])
def download_certificates(batch_id):

    if not batch_id or any(
        character not in "0123456789abcdef"
        for character in batch_id.lower()
    ):
        return jsonify({
            "success": False,
            "message": "Invalid batch ID",
        }), 400

    zip_path = GENERATED_FOLDER / batch_id / "certificates.zip"

    if not zip_path.is_file():
        return jsonify({
            "success": False,
            "message": "Certificate file not found",
        }), 404

    return send_file(
        str(zip_path),
        as_attachment=True,
        download_name="certificates.zip",
    )


# --------------------------------------------------
# Run Flask application locally
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
