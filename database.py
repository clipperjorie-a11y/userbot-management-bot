import os
import json
from datetime import datetime, timedelta
from pymongo import MongoClient

# =====================
# MongoDB Connection
# =====================
MONGO_URI = os.environ.get("MONGO_URI", "")
client = MongoClient(MONGO_URI)
mongo_db = client["botdb"]
collection = mongo_db["data"]

# =====================
# Core DB Functions
# =====================

def get_db():
    """Get database"""
    try:
        doc = collection.find_one({"_id": "main"})
        if not doc:
            default_db = {
                "_id": "main",
                "users": {},
                "sellers": {},
                "transactions": []
            }
            collection.insert_one(default_db)
            return default_db
        return doc
    except Exception as e:
        print(f"DB Load Error: {e}")
        return {"users": {}, "sellers": {}, "transactions": []}

def save_db(data):
    """Save database"""
    try:
        data["_id"] = "main"
        collection.replace_one({"_id": "main"}, data, upsert=True)
        return True
    except Exception as e:
        print(f"DB Save Error: {e}")
        return False

# =====================
# User Functions
# =====================

def init_user(uid):
    """Initialize user dengan default settings"""
    uid = str(uid)
    db = get_db()
    if uid not in db["users"]:
        db["users"][uid] = {
            "uid": uid,
            "access": False,
            "access_until": None,
            "is_reseller": False,
            "reseller_id": None,
            "reseller_customers": [],
            "commission": 0,
            "settings": {
                "auto_reply": False,
                "auto_read": False,
                "auto_typing": False,
                "prefix": ".",
                "language": "id"
            },
            "keywords": [],
            "banwords": [],
            "created_at": datetime.now().isoformat()
        }
        save_db(db)
    return db["users"][uid]

def get_user(uid):
    """Get user data"""
    uid = str(uid)
    db = get_db()
    if uid not in db["users"]:
        return init_user(uid)
    return db["users"][uid]

def save_user(uid, data):
    """Save user data"""
    uid = str(uid)
    db = get_db()
    db["users"][uid] = data
    return save_db(db)

def check_access(uid):
    """Check if user has access"""
    uid = str(uid)
    user = get_user(uid)
    if not user.get("access", False):
        return False
    access_until = user.get("access_until")
    if access_until:
        try:
            until = datetime.fromisoformat(access_until)
            if datetime.now() > until:
                user["access"] = False
                save_user(uid, user)
                return False
        except Exception:
            pass
    return True

def grant_access(uid, duration_days=30):
    """Grant access to user"""
    uid = str(uid)
    user = get_user(uid)
    user["access"] = True
    user["access_until"] = (datetime.now() + timedelta(days=duration_days)).isoformat()
    return save_user(uid, user)

def revoke_access(uid):
    """Revoke access from user"""
    uid = str(uid)
    user = get_user(uid)
    user["access"] = False
    user["access_until"] = None
    return save_user(uid, user)

def get_all_users():
    """Get all users"""
    db = get_db()
    return db.get("users", {})

def get_active_users():
    """Get users with active access"""
    users = get_all_users()
    active = {}
    for uid, data in users.items():
        if check_access(uid):
            active[uid] = data
    return active

def delete_user(uid):
    """Delete user"""
    uid = str(uid)
    db = get_db()
    if uid in db["users"]:
        del db["users"][uid]
        save_db(db)
    return True

# =====================
# Reseller Functions
# =====================

def make_reseller(uid, commission=0):
    """Make user a reseller"""
    uid = str(uid)
    user = get_user(uid)
    user["is_reseller"] = True
    user["commission"] = commission
    user["reseller_customers"] = user.get("reseller_customers", [])
    return save_user(uid, user)

def remove_reseller(uid):
    """Remove reseller status"""
    uid = str(uid)
    user = get_user(uid)
    user["is_reseller"] = False
    user["commission"] = 0
    return save_user(uid, user)

def add_reseller_customer(reseller_id, customer_id):
    """Add customer to reseller"""
    reseller_id = str(reseller_id)
    customer_id = str(customer_id)
    user = get_user(reseller_id)
    customers = user.get("reseller_customers", [])
    if customer_id not in customers:
        customers.append(customer_id)
        user["reseller_customers"] = customers
        save_user(reseller_id, user)
    # Set reseller_id on customer
    customer = get_user(customer_id)
    customer["reseller_id"] = reseller_id
    save_user(customer_id, customer)
    return user

def remove_reseller_customer(reseller_id, customer_id):
    """Remove customer from reseller"""
    reseller_id = str(reseller_id)
    customer_id = str(customer_id)
    user = get_user(reseller_id)
    customers = user.get("reseller_customers", [])
    if customer_id in customers:
        customers.remove(customer_id)
        user["reseller_customers"] = customers
        save_user(reseller_id, user)
    # Remove reseller_id from customer
    customer = get_user(customer_id)
    customer["reseller_id"] = None
    save_user(customer_id, customer)
    return user

def get_resellers():
    """Get all resellers"""
    users = get_all_users()
    resellers = {}
    for uid, data in users.items():
        if data.get("is_reseller", False):
            resellers[uid] = data
    return resellers

# =====================
# Seller Functions
# =====================

def get_seller(uid):
    """Get seller data"""
    uid = str(uid)
    db = get_db()
    return db["sellers"].get(uid, {})

def save_seller(uid, data):
    """Save seller data"""
    uid = str(uid)
    db = get_db()
    db["sellers"][uid] = data
    return save_db(db)

def get_all_sellers():
    """Get all sellers"""
    db = get_db()
    return db.get("sellers", {})

# =====================
# Settings Functions
# =====================

def update_settings(uid, settings):
    """Update user settings"""
    uid = str(uid)
    user = get_user(uid)
    current_settings = user.get("settings", {})
    current_settings.update(settings)
    user["settings"] = current_settings
    return save_user(uid, user)

def get_settings(uid):
    """Get user settings"""
    uid = str(uid)
    user = get_user(uid)
    return user.get("settings", {})

def reset_settings(uid):
    """Reset user settings to default"""
    uid = str(uid)
    user = get_user(uid)
    user["settings"] = {
        "auto_reply": False,
        "auto_read": False,
        "auto_typing": False,
        "prefix": ".",
        "language": "id"
    }
    return save_user(uid, user)

# =====================
# Keyword Functions
# =====================

def add_keyword(uid, keyword):
    """Add keyword for user"""
    uid = str(uid)
    user = get_user(uid)
    keywords = user.get("keywords", [])
    if keyword not in keywords:
        keywords.append(keyword)
        user["keywords"] = keywords
        save_user(uid, user)
    return user

def remove_keyword(uid, keyword):
    """Remove keyword for user"""
    uid = str(uid)
    user = get_user(uid)
    keywords = user.get("keywords", [])
    if keyword in keywords:
        keywords.remove(keyword)
        user["keywords"] = keywords
        save_user(uid, user)
    return user

def get_keywords(uid):
    """Get all keywords for user"""
    uid = str(uid)
    user = get_user(uid)
    return user.get("keywords", [])

def clear_keywords(uid):
    """Clear all keywords for user"""
    uid = str(uid)
    user = get_user(uid)
    user["keywords"] = []
    return save_user(uid, user)

# =====================
# Banword Functions
# =====================

def add_banword(uid, word):
    """Add banned word for user"""
    uid = str(uid)
    user = get_user(uid)
    banwords = user.get("banwords", [])
    if word not in banwords:
        banwords.append(word)
        user["banwords"] = banwords
        save_user(uid, user)
    return user

def remove_banword(uid, word):
    """Remove banned word for user"""
    uid = str(uid)
    user = get_user(uid)
    banwords = user.get("banwords", [])
    if word in banwords:
        banwords.remove(word)
        user["banwords"] = banwords
        save_user(uid, user)
    return user

def get_banwords(uid):
    """Get all banned words for user"""
    uid = str(uid)
    user = get_user(uid)
    return user.get("banwords", [])

def clear_banwords(uid):
    """Clear all banned words for user"""
    uid = str(uid)
    user = get_user(uid)
    user["banwords"] = []
    return save_user(uid, user)

# =====================
# Transaction Functions
# =====================

def add_transaction(data):
    """Add transaction"""
    db = get_db()
    transaction = {
        "id": len(db["transactions"]) + 1,
        "timestamp": datetime.now().isoformat(),
        **data
    }
    db["transactions"].append(transaction)
    save_db(db)
    return transaction

def get_transactions():
    """Get all transactions"""
    db = get_db()
    return db.get("transactions", [])

def get_user_transactions(uid):
    """Get transactions for specific user"""
    uid = str(uid)
    transactions = get_transactions()
    return [t for t in transactions if str(t.get("uid")) == uid]

def clear_transactions():
    """Clear all transactions"""
    db = get_db()
    db["transactions"] = []
    return save_db(db)
    
