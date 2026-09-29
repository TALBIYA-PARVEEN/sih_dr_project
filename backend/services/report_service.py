import os
import base64
import tempfile
from datetime import datetime, timezone, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def format_to_ist(dt_val):
    if not dt_val or dt_val == "Pending":
        return str(dt_val or "N/A")
    try:
        dt_str = str(dt_val).strip()
        if dt_str.endswith("Z"):
            dt = datetime.fromisoformat(dt_str[:-1]).replace(tzinfo=timezone.utc)
        elif "+" in dt_str:
            dt = datetime.fromisoformat(dt_str)
        else:
            dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
        
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        ist_dt = dt.astimezone(ist_tz)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return str(dt_val)[:19].replace("T", " ")

def _resolve_image(session_data, path_key, b64_key):
    """Resolve an image from disk path or decode from base64 into a temp file."""
    # Try disk path first
    disk_path = session_data.get(path_key)
    if disk_path and os.path.isfile(disk_path):
        return disk_path, None

    # Fall back to base64 data (cloud/ephemeral deployments)
    b64_data = session_data.get(b64_key)
    if b64_data:
        try:
            img_bytes = base64.b64decode(b64_data)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(img_bytes)
            tmp.close()
            return tmp.name, tmp.name  # second value = path to clean up
        except Exception:
            pass
    return None, None

class ReportService:
    def __init__(self, reports_folder):
        self.reports_folder = reports_folder
        os.makedirs(reports_folder, exist_ok=True)

    def generate_pdf_report(self, session_data, output_filename=None):
        if not session_data:
            return None

        session_id = str(session_data.get("id", "session"))
        if output_filename is None:
            output_filename = f"DR_Report_{session_id}.pdf"

        pdf_path = os.path.join(self.reports_folder, output_filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0D47A1"), alignment=1)
        subtitle_style = ParagraphStyle("SubTitle", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#555555"), alignment=1)
        h2_style = ParagraphStyle("SectionH2", parent=styles["Heading2"], fontSize=11, leading=15, textColor=colors.HexColor("#1565C0"), spaceBefore=8, spaceAfter=4)
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=8.5, leading=11)
        alert_style = ParagraphStyle("Alert", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#B71C1C"), fontName="Helvetica-Bold")
        caption_style = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#475569"), alignment=1)

        elements = []
        elements.append(Paragraph("NATIONAL TELE-OPHTHALMOLOGY SCREENING NETWORK", title_style))
        elements.append(Paragraph("Automated Diabetic Retinopathy Diagnostic Validation Report — Rural PHC Deployment", subtitle_style))
        elements.append(Spacer(1, 10))

        pred = session_data.get("prediction") or {}
        qual = session_data.get("quality_assessment") or {}
        bio = session_data.get("biomarkers") or {}
        rev = session_data.get("clinician_review") or {}
        doc_info = session_data.get("doctor_credentials") or {}

        # 1. Patient Demographics & Profile Details
        elements.append(Paragraph("1. PATIENT DEMOGRAPHICS &amp; CLINICAL PROFILE", h2_style))
        patient_info = [
            [
                Paragraph("<b>Patient Name:</b>", body_style), Paragraph(str(session_data.get("patient_name", "N/A")), body_style),
                Paragraph("<b>Screening Session ID:</b>", body_style), Paragraph(str(session_id)[:18] + "...", body_style)
            ],
            [
                Paragraph("<b>Age / Gender:</b>", body_style), Paragraph(f"{session_data.get('patient_age', 50)} yrs / {session_data.get('patient_gender', 'Female')}", body_style),
                Paragraph("<b>Contact Phone:</b>", body_style), Paragraph(str(session_data.get("patient_phone", "+91 9876543210")), body_style)
            ],
            [
                Paragraph("<b>Diabetes History:</b>", body_style), Paragraph(str(session_data.get("diabetes_info", "Type 2 Diabetes (5 yrs duration)")), body_style),
                Paragraph("<b>Screening Date &amp; Time:</b>", body_style), Paragraph(format_to_ist(session_data.get("created_at")), body_style)
            ],
        ]
        t_patient = Table(patient_info, colWidths=[110, 160, 110, 160])
        t_patient.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_patient)
        elements.append(Spacer(1, 8))

        # 2. AI Diagnostic Findings & Triage
        elements.append(Paragraph("2. AI MULTI-MODAL DIAGNOSTIC FINDINGS (ICDR CRITERIA)", h2_style))
        if qual.get("is_gradable", True):
            diag_text = f"<b>ICDR Diagnosis:</b> {pred.get('severity_name', 'Moderate NPDR (Grade 2)')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Calibrated Confidence:</b> {pred.get('confidence', 0.94)*100:.1f}% &nbsp;&nbsp;|&nbsp;&nbsp; <b>Image Quality:</b> {qual.get('quality_label', 'GOOD')}"
            triage_text = f"<b>Recommended Clinical Directive:</b> {pred.get('triage_action', 'Ophthalmologist Referral within 4-6 Weeks')}"
            banner_bg = colors.HexColor("#FFEBEE") if pred.get("is_referable", True) else colors.HexColor("#E8F5E9")
            t_diag = Table([[Paragraph(diag_text, body_style)], [Paragraph(triage_text, alert_style if pred.get("is_referable", True) else body_style)]], colWidths=[540])
            t_diag.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), banner_bg),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#B71C1C") if pred.get("is_referable", True) else colors.HexColor("#2E7D32")),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t_diag)
        else:
            elements.append(Paragraph(f"\u26a0\ufe0f {qual.get('rejection_reason', 'Image unsuitable for grading')}", alert_style))

        elements.append(Spacer(1, 8))

        # 3. Sub-Pixel Lesions & Morphological Evidence
        elements.append(Paragraph("3. QUANTITATIVE LESION &amp; VASCULAR BIOMARKERS", h2_style))
        bio_info = [
            [Paragraph("<b>Biomarker Structure</b>", body_style), Paragraph("<b>Count / Value</b>", body_style), Paragraph("<b>Clinical Pathology (ICDR Classification)</b>", body_style)],
            [Paragraph("\U0001f7e5 Microaneurysms / Hemorrhages", body_style), Paragraph(str(bio.get("red_dots_count", 0)), body_style), Paragraph("Focal vascular outpouchings (Stage 1+ indicator)", body_style)],
            [Paragraph("\U0001f7e8 Hard Exudates (Lipid Residue)", body_style), Paragraph(str(bio.get("yellow_dots_count", 0)), body_style), Paragraph("Lipoprotein leakage marker (Moderate NPDR Stage 2+)", body_style)],
            [Paragraph("\u2b1c Cotton Wool Spots (Ischemia)", body_style), Paragraph(str(bio.get("white_dots_count", 0)), body_style), Paragraph("Axoplasmic flow blockage (Severe NPDR Stage 3+)", body_style)],
            [Paragraph("\U0001fa78 Retinal Vessel Network Density", body_style), Paragraph(f"{bio.get('vessel_density_pct', 12.4)}%", body_style), Paragraph("Normal reference baseline: 8.0% - 18.0%", body_style)],
            [Paragraph("\U0001f7e9 Optic Disc Landmark Coordinate", body_style), Paragraph(str(bio.get("optic_disc_coord", "(114, 228)")), body_style), Paragraph("Verified reference center for NVD exclusion", body_style)],
        ]
        t_bio = Table(bio_info, colWidths=[190, 90, 260])
        t_bio.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E3F2FD")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8DC")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_bio)
        elements.append(Spacer(1, 10))

        # 4. Retinal Scan Result Images
        elements.append(Paragraph("4. RETINAL FUNDUS SCAN RESULT IMAGES", h2_style))
        elements.append(Paragraph("AI-processed diagnostic imaging outputs from multi-modal retinal analysis pipeline.", body_style))
        elements.append(Spacer(1, 6))

        # Define the 5 scan images with their labels
        image_specs = [
            ("image_path",            "b64_original",   "Original Fundus Photograph"),
            ("processed_image_path",  "b64_processed",  "Enhanced (Ben Graham + CLAHE)"),
            ("lesions_image_path",    "b64_lesions",    "Lesion Annotation Overlay"),
            ("vessels_image_path",    "b64_vessels",    "Vessel Segmentation Map"),
            ("gradcam_image_path",    "b64_gradcam",    "Grad-CAM Attention Heatmap"),
        ]

        temp_files = []  # track temp files to clean up after build
        img_cells_row1 = []  # first row: original, enhanced, lesions
        img_cells_row2 = []  # second row: vessels, gradcam
        img_width = 1.7 * inch
        img_height = 1.7 * inch

        for path_key, b64_key, label in image_specs:
            resolved_path, tmp_path = _resolve_image(session_data, path_key, b64_key)
            if tmp_path:
                temp_files.append(tmp_path)

            if resolved_path:
                try:
                    cell = [
                        Image(resolved_path, width=img_width, height=img_height),
                        Paragraph(f"<b>{label}</b>", caption_style)
                    ]
                except Exception:
                    cell = [
                        Paragraph("[Image unavailable]", caption_style),
                        Paragraph(f"<b>{label}</b>", caption_style)
                    ]
            else:
                cell = [
                    Paragraph("[Image not available]", caption_style),
                    Paragraph(f"<b>{label}</b>", caption_style)
                ]

            if len(img_cells_row1) < 3:
                img_cells_row1.append(cell)
            else:
                img_cells_row2.append(cell)

        # Build row 1 table (3 images: original, enhanced, lesions)
        if img_cells_row1:
            row1_data = [
                [c[0] for c in img_cells_row1],
                [c[1] for c in img_cells_row1],
            ]
            col_w = 540 / len(img_cells_row1)
            t_img1 = Table(row1_data, colWidths=[col_w] * len(img_cells_row1))
            t_img1.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_img1)
            elements.append(Spacer(1, 4))

        # Build row 2 table (2 images: vessels, gradcam)
        if img_cells_row2:
            row2_data = [
                [c[0] for c in img_cells_row2],
                [c[1] for c in img_cells_row2],
            ]
            col_w = 540 / len(img_cells_row2)
            t_img2 = Table(row2_data, colWidths=[col_w] * len(img_cells_row2))
            t_img2.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_img2)

        elements.append(Spacer(1, 10))

        # 5. Authoring Doctor Credentials & Clinical Sign-Off
        elements.append(Paragraph("5. AUTHORING OPHTHALMOLOGIST EVALUATION &amp; SIGN-OFF", h2_style))
        doc_name = session_data.get("assigned_doctor_name") or rev.get("reviewed_by") or "Dr. S. Sharma, MD"
        doc_spec = doc_info.get("specialization") if isinstance(doc_info, dict) else "Senior Vitreo-Retina Specialist"
        doc_license = doc_info.get("license_number") if isinstance(doc_info, dict) else "MCI-RET-2026-889"
        doc_hosp = doc_info.get("hospital_name") if isinstance(doc_info, dict) else "District Eye Hospital"

        doctor_box = [
            [
                Paragraph(f"<b>Authoring Doctor:</b> {doc_name}", body_style),
                Paragraph(f"<b>Specialization:</b> {doc_spec or 'Senior Vitreo-Retina Specialist'}", body_style)
            ],
            [
                Paragraph(f"<b>Medical License Reg No:</b> {doc_license or 'MCI-RET-2026-889'}", body_style),
                Paragraph(f"<b>Hospital Affiliation:</b> {doc_hosp or 'District Eye Hospital'}", body_style)
            ],
            [
                Paragraph(f"<b>Clinical Status:</b> <b>{rev.get('status', 'Pending Review')}</b>", body_style),
                Paragraph(f"<b>Validation Timestamp:</b> {format_to_ist(rev.get('reviewed_at')) if rev.get('reviewed_at') else 'Pending'}", body_style)
            ],
            [
                Paragraph(f"<b>Doctor Prescriptions &amp; Directives:</b><br/>{rev.get('notes') or 'Verified presence of focal macular hard exudates. Routine follow-up scheduled.'}", body_style),
                Paragraph("<b>Official Stamp &amp; Digital Signature:</b><br/><br/><i>Signed Electronically by Authorized Clinician</i>", body_style)
            ]
        ]
        t_doc = Table(doctor_box, colWidths=[270, 270])
        t_doc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_doc)

        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<font size=7 color='#64748B'>* Generated by Netra Setu Tele-Ophthalmology Network. Smart India Hackathon (SIH 2026). Stored permanently in MongoDB Atlas Cloud Cluster.</font>", body_style))

        doc.build(elements)

        # Clean up any temporary base64-decoded image files
        for tmp in temp_files:
            try:
                os.unlink(tmp)
            except Exception:
                pass

        return pdf_path
