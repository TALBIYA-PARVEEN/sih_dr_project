import urllib.parse
from pymongo import MongoClient

# User's exact credentials
username = "2k24cs1q2413756_db_user"
raw_password = "aeuntmzw03@005_T_#"
encoded_password = urllib.parse.quote_plus(raw_password)

uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

print(f"[TEST] Attempting to connect to MongoDB Atlas with URI...")

try:
    import certifi
    ca = certifi.where()
    client = MongoClient(uri, tlsCAFile=ca, serverSelectionTimeoutMS=8000)
    client.admin.command('ping')
    print("[SUCCESS] Connected to MongoDB Atlas Cloud Cluster via certifi!")
except Exception as e1:
    print(f"[NOTE] certifi attempt failed: {e1}. Trying tlsAllowInvalidCertificates...")
    try:
        client = MongoClient(uri, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=8000)
        client.admin.command('ping')
        print("[SUCCESS] Connected to MongoDB Atlas Cloud Cluster via tlsAllowInvalidCertificates!")
    except Exception as e2:
        print(f"[FAILED] Direct connection error: {e2}")
        client = None

if client:
    db = client["NetraAI-db"]
    print("[INFO] Database collections before insert:", db.list_collection_names())
    
    # Insert test seed record to ensure collections exist in Atlas UI
    db.users.update_one(
        {"username": "admin"},
        {"$set": {
            "id": "admin-001",
            "username": "admin",
            "email": "admin@teleophta.org",
            "full_name": "Master District Admin",
            "role": "admin",
            "is_email_verified": True
        }},
        upsert=True
    )
    print("[SUCCESS] Seeded 'users' collection in MongoDB Atlas!")
    print("[INFO] Database collections now:", db.list_collection_names())
