from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DB_NAME]

print("=== REAL DATABASE STATUS ===")
print(f"Users Count: {db.users.count_documents({})}")
for u in db.users.find():
    print(f"  • {u.get('username')} ({u.get('role')}) - {u.get('full_name')} - {u.get('email')}")

print(f"\nDoctors Count: {db.doctors.count_documents({})}")
for d in db.doctors.find():
    print(f"  • {d.get('full_name')} ({d.get('specialization')}) - Status: {d.get('approval_status')}")

print(f"\nPatients Count: {db.patients.count_documents({})}")
for p in db.patients.find():
    print(f"  • {p.get('full_name')} (Age {p.get('age')}) - Phone: {p.get('phone')}")
