import certifi
from pymongo import MongoClient

uri = "mongodb+srv://2k24cs1q2413756_db_user:NetraAI2026@cluster0.orlzz77.mongodb.net/NetraAI-db?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["NetraAI-db"]

print("=" * 60)
print("LIVE MONGODB ATLAS DATABASE: NetraAI-db")
print("=" * 60)

for col in sorted(db.list_collection_names()):
    count = db[col].count_documents({})
    print(f"Collection '{col}': {count} documents")

print("=" * 60)
print("ALL COLLECTIONS AND RECORDS ARE LIVE IN YOUR ATLAS DASHBOARD!")
