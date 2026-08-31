from pymongo import MongoClient
import os
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DB_NAME]

print("=== USERS ===")
for u in db.users.find():
    print(f"- ID: {u.get('id')}, Username: {u.get('username')}, Email: {u.get('email')}, Role: {u.get('role')}, Name: {u.get('full_name')}")

print("\n=== DOCTORS ===")
for d in db.doctors.find():
    print(f"- ID: {d.get('id')}, Name: {d.get('full_name')}, License: {d.get('license_number')}, Status: {d.get('approval_status', d.get('active_status'))}")

print("\n=== PATIENTS ===")
for p in db.patients.find():
    print(f"- ID: {p.get('id')}, Name: {p.get('full_name')}, Email: {p.get('email')}")

print(f"\nTotal Screenings: {db.screenings.count_documents({})}")
