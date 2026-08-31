import urllib.parse
from pymongo import MongoClient

username = "2k24cs1q2413756_db_user"
raw_password = "aeuntmzw03@005_T_#"
encoded_password = urllib.parse.quote_plus(raw_password)

uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

print("[TEST] Testing PyMongo tlsDisableOCSPEndpointCheck...")
try:
    client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsDisableOCSPEndpointCheck=True,
        serverSelectionTimeoutMS=5000
    )
    client.admin.command('ping')
    print("[SUCCESS] Connected to MongoDB Atlas Cloud Cluster!")
    db = client["NetraAI-db"]
    print("Existing Collections:", db.list_collection_names())
except Exception as e:
    print(f"[RESULT] Error: {e}")
