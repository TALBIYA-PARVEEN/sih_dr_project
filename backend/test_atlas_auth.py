import urllib.parse
from pymongo import MongoClient

username = "2k24cs1q2413756_db_user"
raw_password = "aeuntmzw03@005_T_#"
encoded_password = urllib.parse.quote_plus(raw_password)

# Test with authSource=admin
uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.orlzz77.mongodb.net/NetraAI-db?authSource=admin&retryWrites=true&w=majority&appName=Cluster0"

print(f"[TEST] Testing MongoDB Atlas with authSource=admin...")
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("[SUCCESS] CONNECTED TO MONGODB ATLAS WITH authSource=admin!")
    db = client["NetraAI-db"]
    print("Collections in Atlas:", db.list_collection_names())
except Exception as e:
    print(f"[RESULT] {e}")
