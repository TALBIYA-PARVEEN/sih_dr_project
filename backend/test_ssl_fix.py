import ssl
import urllib.parse
from pymongo import MongoClient

username = "2k24cs1q2413756_db_user"
raw_password = "aeuntmzw03@005_T_#"
encoded_password = urllib.parse.quote_plus(raw_password)

uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

print("[TEST] Testing custom SSL Context...")
try:
    client = MongoClient(uri, ssl_context=ssl_ctx, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("[SUCCESS] Connected to MongoDB Atlas with custom SSL Context!")
    db = client["NetraAI-db"]
    print("Existing Collections:", db.list_collection_names())
    
    # Create collections explicitly
    db.create_collection("users") if "users" not in db.list_collection_names() else None
    db.create_collection("screenings") if "screenings" not in db.list_collection_names() else None
    db.create_collection("messages") if "messages" not in db.list_collection_names() else None
    db.create_collection("notifications") if "notifications" not in db.list_collection_names() else None
    
    print("Collections after init:", db.list_collection_names())
except Exception as e:
    print(f"[RESULT] Error: {e}")
