from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client[Config.MONGO_DB_NAME]

print("[CLEANUP] Cleaning mock and test data from MongoDB Atlas...")

# 1. Real usernames to preserve
REAL_USERNAMES = ["admin", "talbiya"]

# Delete mock users
deleted_users = db.users.delete_many({"username": {"$nin": REAL_USERNAMES}})
print(f"- Deleted {deleted_users.deleted_count} mock user accounts.")

# Get real user IDs
real_users = list(db.users.find())
real_user_ids = [u["id"] for u in real_users]
real_usernames = [u["username"] for u in real_users]
print(f"- Preserved Real Users: {[(u['username'], u['full_name'], u['email']) for u in real_users]}")

# 2. Delete mock doctors (keep only if user_id in real_user_ids)
deleted_docs = db.doctors.delete_many({"user_id": {"$nin": real_user_ids}})
print(f"- Deleted {deleted_docs.deleted_count} mock doctor profiles.")

# 3. Delete mock patients (keep only if user_id in real_user_ids)
deleted_pats = db.patients.delete_many({"user_id": {"$nin": real_user_ids}})
print(f"- Deleted {deleted_pats.deleted_count} mock patient profiles.")

# 4. Clean screenings and reports that don't belong to real users
deleted_screenings = db.screenings.delete_many({
    "$and": [
        {"patient_user_id": {"$nin": real_user_ids + real_usernames}},
        {"patient_name": {"$ne": "Talbiya Parveen"}}
    ]
})
print(f"- Deleted {deleted_screenings.deleted_count} test screenings.")

# 5. Clean mock messages
deleted_msgs = db.messages.delete_many({
    "sender_id": {"$nin": real_user_ids + real_usernames}
})
print(f"- Deleted {deleted_msgs.deleted_count} mock messages.")

# Print final reality check
print("\n=== REAL DATABASE STATE ===")
print("Users:", db.users.count_documents({}))
for u in db.users.find():
    print(" ", u.get("username"), "|", u.get("role"), "|", u.get("full_name"), "|", u.get("email"))

print("Doctors:", db.doctors.count_documents({}))
for d in db.doctors.find():
    print(" ", d.get("full_name"), "| License:", d.get("license_number"), "| Approval:", d.get("approval_status"))

print("Patients:", db.patients.count_documents({}))
for p in db.patients.find():
    print(" ", p.get("full_name"), "| Age:", p.get("age"), "| Phone:", p.get("phone"))

print("Screenings:", db.screenings.count_documents({}))
