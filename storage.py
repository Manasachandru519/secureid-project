import os, sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "secureid.db"

class Store:
    def __init__(self):
        self.mongo = None
        uri = os.getenv("MONGO_URI", "").strip()
        if uri:
            try:
                from pymongo import MongoClient
                client = MongoClient(uri, serverSelectionTimeoutMS=1800)
                client.admin.command("ping")
                self.mongo = client[uri.rsplit("/", 1)[-1].split("?")[0] or "secureid"]
            except Exception as exc:
                print("MongoDB unavailable; using SQLite:", exc)
        self._init_sqlite()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS identities(
                id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
                encrypted_data TEXT NOT NULL, identity_hash TEXT NOT NULL,
                status TEXT NOT NULL, risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL, created_at TEXT NOT NULL, ocr_text TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS alerts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, identity_id TEXT, email TEXT,
                score INTEGER, reason TEXT, created_at TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS blocks(
                idx INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
                identity_id TEXT, data_hash TEXT, previous_hash TEXT, block_hash TEXT
            )""")

    def add_identity(self, item):
        if self.mongo is not None:
            self.mongo.identities.insert_one(dict(item))
            return
        with self._conn() as c:
            c.execute("INSERT INTO identities VALUES(?,?,?,?,?,?,?,?,?,?)", tuple(item[k] for k in
                ["id","name","email","encrypted_data","identity_hash","status","risk_score","risk_level","created_at","ocr_text"]))

    def get_identity_by_email(self, email):
        if self.mongo is not None:
            return self.mongo.identities.find_one({"email": email}, {"_id": 0})
        with self._conn() as c:
            row = c.execute("SELECT * FROM identities WHERE lower(email)=lower(?)", (email,)).fetchone()
            return dict(row) if row else None

    def list_identities(self):
        if self.mongo is not None:
            return list(self.mongo.identities.find({}, {"_id": 0}).sort("created_at", -1))
        with self._conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM identities ORDER BY created_at DESC").fetchall()]

    def update_status(self, identity_id, status):
        if self.mongo is not None:
            self.mongo.identities.update_one({"id": identity_id}, {"$set": {"status": status}})
        else:
            with self._conn() as c:
                c.execute("UPDATE identities SET status=? WHERE id=?", (status, identity_id))

    def add_alert(self, identity_id, email, score, reason):
        now = datetime.now(timezone.utc).isoformat()
        if self.mongo is not None:
            self.mongo.alerts.insert_one({"identity_id":identity_id,"email":email,"score":score,"reason":reason,"created_at":now})
        else:
            with self._conn() as c:
                c.execute("INSERT INTO alerts(identity_id,email,score,reason,created_at) VALUES(?,?,?,?,?)",
                          (identity_id,email,score,reason,now))

    def list_alerts(self):
        if self.mongo is not None:
            return list(self.mongo.alerts.find({}, {"_id":0}).sort("created_at",-1))
        with self._conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()]

    def add_block(self, block):
        if self.mongo is not None:
            self.mongo.blocks.insert_one(dict(block))
        else:
            with self._conn() as c:
                c.execute("INSERT INTO blocks(idx,timestamp,identity_id,data_hash,previous_hash,block_hash) VALUES(?,?,?,?,?,?)",
                          tuple(block[k] for k in ["idx","timestamp","identity_id","data_hash","previous_hash","block_hash"]))

    def list_blocks(self):
        if self.mongo is not None:
            return list(self.mongo.blocks.find({}, {"_id":0}).sort("idx",1))
        with self._conn() as c:
            return [dict(x) for x in c.execute("SELECT * FROM blocks ORDER BY idx").fetchall()]
