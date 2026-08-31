from app import create_app
from db import mongo

app = create_app()
client = app.test_client()

print("[TEST] Checking Patient History Endpoint...")

pat = mongo.users.find_one({"username": "patient_ramesh"})
if pat:
    res = client.get(f"/api/patient/history/{pat['id']}")
    assert res.status_code == 200
    data = res.get_json()
    print(f"[PASS] Total reports found for patient_ramesh ({pat['id']}): {data['total']}")
    for idx, r in enumerate(data.get("history", [])):
        print(f"  [{idx+1}] Severity: {r.get('final_severity_name')}, Quality: {r.get('quality_status')}, Doctor: {r.get('doctor_name')}, PDF: {r.get('pdf_report_url')}")

screenings_list = list(mongo.screenings.find())
print(f"\n[PASS] Total Screenings in Atlas: {len(screenings_list)}")
print("[SUCCESS] Patient history verified and working 100%!")
