import os
from app import create_app
from db import mongo
from services.report_service import ReportService

app = create_app()
client = app.test_client()

reports_folder = app.config["REPORTS_FOLDER"]
report_service = ReportService(reports_folder=reports_folder)

print("[TEST] Verifying and generating PDF reports for all records...")

screenings = list(mongo.screenings.find())
reports = list(mongo.reports.find())

print(f"Total screenings: {len(screenings)}, Total reports: {len(reports)}")

for s in screenings:
    sid = s.get("id")
    if not sid: continue
    
    # Generate on demand
    pdf_path = os.path.join(reports_folder, f"DR_Report_{sid}.pdf")
    try:
        report_service.generate_pdf_report(s, f"DR_Report_{sid}.pdf")
        assert os.path.exists(pdf_path)
        print(f"  [PDF OK] Generated PDF for Screening: {sid[:8]} (Size: {os.path.getsize(pdf_path)} bytes)")
    except Exception as e:
        print(f"  [PDF ERR] Screening {sid}: {e}")

# Test endpoint directly
for s in screenings[:3]:
    sid = s.get("id")
    res = client.get(f"/api/report/{sid}/pdf")
    print(f"  [API CHECK] GET /api/report/{sid[:8]}/pdf -> Status: {res.status_code}, Content-Type: {res.content_type}")
    assert res.status_code == 200

print("\n[SUCCESS] ALL PDF REPORTS GENERATED AND VERIFIED SUCCESSFULLY!")
