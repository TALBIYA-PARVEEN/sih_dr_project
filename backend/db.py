import os
import uuid
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

class MongoManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.patients = None
        self.doctors = None
        self.admins = None
        self.screenings = None
        self.reports = None
        self.messages = None

    def init_app(self, app):
        mongo_uri = app.config.get("MONGO_URI", "mongodb://127.0.0.1:27017/dr_screening_db")
        db_name = app.config.get("MONGO_DB_NAME", "NetraAI-db")

        try:
            import certifi
            ca_file = certifi.where()
            self.client = MongoClient(
                mongo_uri,
                tlsCAFile=ca_file,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=15000
            )
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            print(f"[MONGODB-ATLAS] Connected successfully to Cloud Cluster: {db_name}")
        except Exception as e:
            try:
                self.client = MongoClient(
                    mongo_uri,
                    tlsAllowInvalidCertificates=True,
                    serverSelectionTimeoutMS=15000,
                    connectTimeoutMS=15000
                )
                self.client.admin.command('ping')
                self.db = self.client[db_name]
                print(f"[MONGODB-ATLAS] Connected via TLS Fallback: {db_name}")
            except Exception as e2:
                print(f"[MONGODB-FATAL] Cloud connection error: {e2}. Using InMemory fallback.")
                self.db = InMemoryDatabase()

        # Dedicated Collections
        self.users = self.db["users"]
        self.patients = self.db["patients"]
        self.doctors = self.db["doctors"]
        self.admins = self.db["admins"]
        self.screenings = self.db["screenings"]
        self.reports = self.db["reports"]
        self.messages = self.db["messages"]

        try:
            self.users.create_index("username", unique=True)
            self.users.create_index("email", unique=True)
            self.patients.create_index("user_id", unique=True)
            self.doctors.create_index("user_id", unique=True)
            self.admins.create_index("user_id", unique=True)
            self.screenings.create_index("patient_id")
            self.reports.create_index("screening_id")
        except Exception:
            pass

        # Seed / Update Master Admin
        admin_email = app.config.get("ADMIN_EMAIL", "admin@teleophta.org")
        admin_user = self.users.find_one({"username": "admin"})
        if not admin_user or "password_hash" not in admin_user:
            admin_user_id = admin_user["id"] if admin_user else str(uuid.uuid4())
            admin_user_doc = {
                "id": admin_user_id,
                "username": "admin",
                "email": admin_email,
                "password_hash": generate_password_hash(app.config.get("ADMIN_PASSWORD", "Admin@SIH2026")),
                "full_name": app.config.get("ADMIN_NAME", "Master District Admin"),
                "role": "admin",
                "is_email_verified": True,
                "created_at": datetime.utcnow().isoformat()
            }
            self.users.update_one({"username": "admin"}, {"$set": admin_user_doc}, upsert=True)

            admin_profile_doc = {
                "id": str(uuid.uuid4()),
                "user_id": admin_user_id,
                "full_name": app.config.get("ADMIN_NAME", "Master District Admin"),
                "email": admin_email,
                "district_jurisdiction": "National District Level",
                "telemetry_access_level": "SuperAdmin",
                "created_at": datetime.utcnow().isoformat()
            }
            self.admins.update_one({"user_id": admin_user_id}, {"$set": admin_profile_doc}, upsert=True)
            print(f"[MONGODB] Master Admin Verified: {admin_email}")

# In-Memory Datastore Fallback
class InMemoryCollection:
    def __init__(self):
        self.data = []

    def find_one(self, query):
        for item in self.data:
            match = True
            for k, v in query.items():
                if k == "$or":
                    or_match = any(all(item.get(sub_k) == sub_v for sub_k, sub_v in cond.items()) for cond in v)
                    if not or_match: match = False; break
                elif isinstance(v, dict) and "$ne" in v:
                    if item.get(k) == v["$ne"]: match = False; break
                elif item.get(k) != v:
                    match = False; break
            if match: return item
        return None

    def find(self, query=None, sort=None, limit=None):
        res = list(self.data)
        if query:
            filtered = []
            for item in res:
                match = True
                for k, v in query.items():
                    if k == "$or":
                        if not any(all(item.get(sub_k) == sub_v for sub_k, sub_v in cond.items()) for cond in v):
                            match = False; break
                    elif isinstance(v, dict) and "$ne" in v:
                        if item.get(k) == v["$ne"]: match = False; break
                    elif item.get(k) != v:
                        match = False; break
                if match: filtered.append(item)
            res = filtered
        if sort:
            for field, order in reversed(sort):
                res.sort(key=lambda x: x.get(field, ""), reverse=(order == -1))
        if limit: res = res[:limit]
        return res

    def insert_one(self, doc):
        if "_id" not in doc: doc["_id"] = str(uuid.uuid4())
        self.data.append(doc)
        return doc

    def insert_many(self, docs):
        for d in docs: self.insert_one(d)

    def update_one(self, query, update, upsert=False):
        item = self.find_one(query)
        if item and "$set" in update:
            item.update(update["$set"])
        elif not item and upsert and "$set" in update:
            new_doc = dict(query)
            new_doc.update(update["$set"])
            self.insert_one(new_doc)

    def count_documents(self, query):
        return len(self.find(query))

    def create_index(self, *args, **kwargs): pass

class InMemoryDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = InMemoryCollection()
        return self.collections[name]

mongo = MongoManager()
