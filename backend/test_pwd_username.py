import urllib.parse
from pymongo import MongoClient

username = "2k24cs1q2413756_db_user"
password = "2k24cs1q2413756_db_user"

uri = f"mongodb+srv://{username}:{password}@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

print(f"[TEST] Testing MongoDB Atlas with password = username ({password})...")
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("[SUCCESS] CONNECTED TO MONGODB ATLAS SUCCESSFULLY!")
    db = client["NetraAI-db"]
    print("Collections in Atlas:", db.list_collection_names())
except Exception as e:
    print(f"[RESULT] {e}")
