const API_URL = "https://certiai-backend.onrender.com";

const fileInput = document.getElementById("fileInput");
const uploadArea = document.getElementById("uploadArea");
const fileName = document.getElementById("fileName");
const results = document.getElementById("results");
const recordCount = document.getElementById("recordCount");
const validation = document.getElementById("validation");
const tableBody = document.getElementById("tableBody");
const generateButton = document.getElementById("generateButton");

// Custom template elements
const customTemplateInput = document.getElementById("customTemplateInput");
const customTemplateSection = document.getElementById("customTemplateSection");
const customUploadZone = document.getElementById("customUploadZone");
const customBrowseButton = document.getElementById("customBrowseButton");
const customTemplatePreview = document.getElementById("customTemplatePreview");
const customTemplateImage = document.getElementById("customTemplateImage");
const customTemplateName = document.getElementById("customTemplateName");
const customTemplateStatus = document.getElementById("customTemplateStatus");
const removeCustomTemplateButton = document.getElementById("removeCustomTemplateButton");

let uploadedData = [];
let uploadedBatchToken = null;
let customTemplateId = null;
let customTemplateObjectUrl = null;

let isExcelUploading = false;
let isCustomTemplateUploading = false;
let isGenerating = false;


/* ==========================================
   INITIALIZATION
========================================== */

document.addEventListener("DOMContentLoaded", () => {
    updateCustomTemplateSection();
    updateGenerateButton();
});

document.querySelectorAll('input[name="template"]').forEach(radio => {
    radio.addEventListener("change", () => {
        updateCustomTemplateSection();
        updateGenerateButton();
    });
});


/* ==========================================
   EXCEL FILE SELECTION
========================================== */

if (fileInput) {
    fileInput.addEventListener("change", () => {
        const file = fileInput.files?.[0];

        if (file) {
            fileName.textContent = `Uploading ${file.name}...`;
            uploadFile(file);
        }
    });
}


/* ==========================================
   EXCEL DRAG AND DROP
========================================== */

if (uploadArea) {

    uploadArea.addEventListener("dragover", event => {
        event.preventDefault();
        uploadArea.classList.add("dragging");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragging");
    });

    uploadArea.addEventListener("drop", event => {
        event.preventDefault();

        uploadArea.classList.remove("dragging");

        const file = event.dataTransfer?.files?.[0];

        if (file) {
            fileName.textContent = `Uploading ${file.name}...`;
            uploadFile(file);
        }
    });
}


/* ==========================================
   UPLOAD EXCEL FILE
========================================== */

async function uploadFile(file) {

    if (!file) return;

    isExcelUploading = true;

    uploadedData = [];
    uploadedBatchToken = null;

    updateGenerateButton();

    validation.innerHTML = `
        <div class="validation-message">
            Uploading and validating
            <strong>${escapeHTML(file.name)}</strong>...
        </div>
    `;

    const formData = new FormData();

    formData.append("file", file);

    try {

        const response = await fetch(
            `${API_URL}/api/upload-excel`,
            {
                method: "POST",
                body: formData
            }
        );

        const data = await readJsonResponse(response);

        console.log("Excel upload response:", data);

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Excel upload failed.");
        }

        uploadedData = Array.isArray(data.records)
            ? data.records
            : [];

        uploadedBatchToken =
            data.batch_token ||
            data.uploaded_batch_token ||
            null;

        fileName.textContent = file.name;

        recordCount.textContent =
            `${uploadedData.length} record${uploadedData.length === 1 ? "" : "s"}`;

        results.style.display = "block";

        displayTable(uploadedData);

        if (data.valid) {

            validation.innerHTML = `
                <div class="validation-message success">
                    ✓ File uploaded and validated successfully.
                </div>
            `;

        } else {

            validation.innerHTML = `
                <div class="validation-message error">
                    ⚠ ${formatErrors(data.errors)}
                </div>
            `;
        }

    } catch (error) {

        console.error("Excel upload error:", error);

        uploadedData = [];
        uploadedBatchToken = null;

        fileName.textContent = file.name;
        recordCount.textContent = "0 records";

        validation.innerHTML = `
            <div class="validation-message error">
                ⚠ ${escapeHTML(error.message)}
            </div>
        `;

    } finally {

        isExcelUploading = false;

        updateGenerateButton();
    }
}


/* ==========================================
   DISPLAY EXCEL RECORDS
========================================== */

function displayTable(records) {

    tableBody.innerHTML = "";

    records.forEach((record, index) => {

        const row = document.createElement("tr");

        const values = [
            index + 1,
            record.Name,
            record.Event,
            record.Organization,
            record.Date,
            record.Achievement
        ];

        values.forEach(value => {

            const cell = document.createElement("td");

            cell.textContent =
                value === null || value === undefined
                    ? ""
                    : String(value);

            row.appendChild(cell);
        });

        tableBody.appendChild(row);
    });
}


/* ==========================================
   CUSTOM TEMPLATE UPLOAD
========================================== */

if (customBrowseButton && customTemplateInput) {

    customBrowseButton.addEventListener("click", () => {
        customTemplateInput.click();
    });
}

if (customUploadZone && customTemplateInput) {

    customUploadZone.addEventListener("click", event => {

        if (
            event.target === customUploadZone ||
            event.target.closest(".custom-upload-zone-content")
        ) {
            customTemplateInput.click();
        }
    });

    customUploadZone.addEventListener("dragover", event => {
        event.preventDefault();
        customUploadZone.classList.add("dragging");
    });

    customUploadZone.addEventListener("dragleave", () => {
        customUploadZone.classList.remove("dragging");
    });

    customUploadZone.addEventListener("drop", event => {

        event.preventDefault();

        customUploadZone.classList.remove("dragging");

        const file = event.dataTransfer?.files?.[0];

        if (file) {
            uploadCustomTemplate(file);
        }
    });
}

if (customTemplateInput) {

    customTemplateInput.addEventListener("change", () => {

        const file = customTemplateInput.files?.[0];

        if (file) {
            uploadCustomTemplate(file);
        }
    });
}

if (removeCustomTemplateButton) {

    removeCustomTemplateButton.addEventListener("click", event => {

        event.preventDefault();
        event.stopPropagation();

        clearCustomTemplate();
    });
}


/* ==========================================
   UPLOAD CUSTOM TEMPLATE TO BACKEND
========================================== */

async function uploadCustomTemplate(file) {

    if (!file) return;

    const allowedTypes = [
        "image/png",
        "image/jpeg"
    ];

    const maxSize = 10 * 1024 * 1024;

    if (!allowedTypes.includes(file.type)) {

        showCustomTemplateStatus(
            "Please select a JPG or PNG image.",
            true
        );

        customTemplateInput.value = "";

        return;
    }

    if (file.size > maxSize) {

        showCustomTemplateStatus(
            "Image must be smaller than 10 MB.",
            true
        );

        customTemplateInput.value = "";

        return;
    }

    isCustomTemplateUploading = true;

    customTemplateId = null;

    updateGenerateButton();

    showCustomTemplateStatus(
        "Uploading your certificate design...",
        false
    );

    if (customTemplateObjectUrl) {
        URL.revokeObjectURL(customTemplateObjectUrl);
    }

    customTemplateObjectUrl = URL.createObjectURL(file);

    if (customTemplateImage) {
        customTemplateImage.src = customTemplateObjectUrl;
        customTemplateImage.alt = "Custom certificate template preview";
    }

    if (customTemplateName) {
        customTemplateName.textContent = file.name;
    }

    if (customTemplatePreview) {
        customTemplatePreview.hidden = false;
        customTemplatePreview.style.display = "block";
    }

    const formData = new FormData();

    formData.append("file", file);

    try {

        const response = await fetch(
            `${API_URL}/api/upload-template`,
            {
                method: "POST",
                body: formData
            }
        );

        const data = await readJsonResponse(response);

        console.log("Custom template response:", data);

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Custom template upload failed."
            );
        }

        customTemplateId =
            data.template_id ||
            data.custom_template_id ||
            data.id ||
            null;

        if (!customTemplateId) {
            throw new Error(
                "The server did not return a template ID."
            );
        }

        showCustomTemplateStatus(
            "✓ Custom design uploaded successfully.",
            false
        );

    } catch (error) {

        console.error("Custom template upload error:", error);

        customTemplateId = null;

        showCustomTemplateStatus(
            error.message,
            true
        );

    } finally {

        isCustomTemplateUploading = false;

        updateGenerateButton();
    }
}


/* ==========================================
   REMOVE CUSTOM TEMPLATE
========================================== */

function clearCustomTemplate() {

    customTemplateId = null;

    if (customTemplateInput) {
        customTemplateInput.value = "";
    }

    if (customTemplateObjectUrl) {

        URL.revokeObjectURL(customTemplateObjectUrl);

        customTemplateObjectUrl = null;
    }

    if (customTemplateImage) {
        customTemplateImage.removeAttribute("src");
    }

    if (customTemplateName) {
        customTemplateName.textContent = "";
    }

    if (customTemplatePreview) {
        customTemplatePreview.hidden = true;
        customTemplatePreview.style.display = "none";
    }

    showCustomTemplateStatus(
        "No custom design uploaded.",
        false
    );

    updateGenerateButton();
}


/* ==========================================
   CUSTOM TEMPLATE STATUS
========================================== */

function showCustomTemplateStatus(message, isError) {

    if (!customTemplateStatus) return;

    customTemplateStatus.textContent = message;

    customTemplateStatus.classList.toggle(
        "error",
        Boolean(isError)
    );

    customTemplateStatus.classList.toggle(
        "success",
        !isError
    );
}


/* ==========================================
   TEMPLATE SELECTION
========================================== */

function getSelectedTemplate() {

    const selected = document.querySelector(
        'input[name="template"]:checked'
    );

    return selected ? selected.value : "classic";
}

function updateCustomTemplateSection() {

    if (!customTemplateSection) return;

    const isCustomSelected =
        getSelectedTemplate() === "custom";

    customTemplateSection.hidden = !isCustomSelected;

    customTemplateSection.style.display =
        isCustomSelected ? "block" : "none";
}


/* ==========================================
   GENERATE BUTTON VALIDATION
========================================== */

function updateGenerateButton() {

    if (!generateButton) return;

    const customSelected =
        getSelectedTemplate() === "custom";

    const customTemplateReady =
        !customSelected || Boolean(customTemplateId);

    generateButton.disabled =
        uploadedData.length === 0 ||
        isExcelUploading ||
        isCustomTemplateUploading ||
        isGenerating ||
        !customTemplateReady;
}


/* ==========================================
   GENERATE CERTIFICATES
========================================== */

if (generateButton) {

    generateButton.addEventListener(
        "click",
        generateCertificates
    );
}

async function generateCertificates() {

    if (uploadedData.length === 0) {

        showValidationError(
            "Please upload a valid Excel file first."
        );

        return;
    }

    const selectedTemplate = getSelectedTemplate();

    if (
        selectedTemplate === "custom" &&
        !customTemplateId
    ) {

        showValidationError(
            "Please upload your custom certificate design first."
        );

        return;
    }

    isGenerating = true;

    updateGenerateButton();

    generateButton.textContent =
        "Generating Certificates...";

    validation.innerHTML = `
        <div class="validation-message">
            Creating ${uploadedData.length} certificates.
            Please wait...
        </div>
    `;

    const requestBody = {
        template: selectedTemplate
    };

    if (selectedTemplate === "custom") {

        requestBody.custom_template_id =
            customTemplateId;
    }

    if (uploadedBatchToken) {

        requestBody.uploaded_batch_token =
            uploadedBatchToken;
    }

    try {

        const response = await fetch(
            `${API_URL}/api/generate-certificates`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(requestBody)
            }
        );

        const data = await readJsonResponse(response);

        console.log(
            "Certificate generation response:",
            data
        );

        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Certificate generation failed."
            );
        }

        validation.innerHTML = `
            <div class="validation-message success">
                ✓ ${Number(data.total_certificates || uploadedData.length)}
                certificates generated successfully.
                Your ZIP download should start automatically.
            </div>
        `;

        const downloadUrl = data.download_url
            ? (
                data.download_url.startsWith("http")
                    ? data.download_url
                    : `${API_URL}${data.download_url}`
            )
            : null;

        if (!downloadUrl) {

            throw new Error(
                "Certificates were generated, but the server did not return a download URL."
            );
        }

        const link = document.createElement("a");

        link.href = downloadUrl;
        link.download = "certificates.zip";

        document.body.appendChild(link);

        link.click();

        link.remove();

    } catch (error) {

        console.error(
            "Certificate generation error:",
            error
        );

        showValidationError(error.message);

    } finally {

        isGenerating = false;

        generateButton.textContent =
            "✦ Generate Certificates →";

        updateGenerateButton();
    }
}


/* ==========================================
   HELPER FUNCTIONS
========================================== */

async function readJsonResponse(response) {

    const responseText = await response.text();

    let data;

    try {

        data = responseText
            ? JSON.parse(responseText)
            : {};

    } catch {

        throw new Error(
            `Server returned an invalid response (HTTP ${response.status}).`
        );
    }

    return data;
}


function showValidationError(message) {

    if (!validation) return;

    validation.innerHTML = `
        <div class="validation-message error">
            ⚠ ${escapeHTML(message)}
        </div>
    `;
}


function formatErrors(errors) {

    if (!Array.isArray(errors) || errors.length === 0) {

        return "The Excel file contains invalid data.";
    }

    return errors
        .map(error => escapeHTML(error))
        .join("<br>");
}


function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}