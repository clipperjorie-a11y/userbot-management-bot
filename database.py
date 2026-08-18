import json, os

DB_FILE = "database.json"

def get_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "sellers": {}, "payments": {}}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "sellers": {}, "payments": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)
      
