import json
import os
from datetime import datetime, timedelta

DB_FILE = "database.json"

def get_db():
    """Get database"""
    if not os.path.exists(DB_FILE):
        default_db = {
            "users": {},
            "sellers": {},
            "transactions": []
        }
        save_db(default_db)
        return default_db
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"DB Load Error: {e}")
        return {"users": {}, "sellers": {}, "transactions": []}

def save_db(data):
    """Save database"""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"DB Save Error: {e}")
        return False

def init_user(uid):
    """Initialize user dengan default settings"""
    uid = str(uid)
    db = get_db()
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "tier": "none",  # none, jaseb_only, autoreply, full, reseller
            "expired": None,
            "warranty": None,
            "session": "",
            "claimed_trial": False,
            "is_reseller": False,
            "reseller_customers": [],
            "created_at": datetime.now().isoformat(),
            "settings": {
                # AUTO BROADCAST
                "bc_enabled": False,
                "bc_text": "",
                "bc_delay": 5,
                "bc_targets": [],
                
                # AUTO FORWARD
                "fw_enabled": False,
                "fw_source_ch": "",
                "fw_targets": [],
                "fw_delay": 5,
                
                # AUTO REPLY
                "ar_enabled": False,
                "ar_keywords": [],  # [{"keyword": "hi", "response": "hello", "enabled": True}]
                "ar_banwords": [],
                
                # GROUP MANAGEMENT
                "groups": []
            }
        }
    
    save_db(db)
    return db["users"][uid]

def get_user(uid):
    """Get user data"""
    uid = str(uid)
    db = get_db()
    if uid not in db["users"]:
        init_user(uid)
    return db["users"][uid]

def save_user(uid, user_data):
    """Save user data"""
    uid = str(uid)
    db = get_db()
    db["users"][uid] = user_data
    save_db(db)

def check_access(uid, feature):
    """Check user access to feature"""
    user = get_user(uid)
    tier = user.get("tier", "none")
    expired = user.get("expired")
    
    # Check if expired
    if expired:
        try:
            exp_dt = datetime.fromisoformat(expired)
            if datetime.now() > exp_dt:
                return False
        except:
            pass
    
    # Feature access mapping
    access_map = {
        "jaseb_only": ["bc", "forward"],
        "autoreply": ["reply"],
        "full": ["bc", "forward", "reply", "ban", "group"],
        "reseller": ["all"]
    }
    
    allowed = access_map.get(tier, [])
    
    if "all" in allowed:
        return True
    return feature in allowed

def grant_access(uid, tier, days=30, warranty_days=0):
    """Grant access tier to user"""
    uid = str(uid)
    user = get_user(uid)
    
    expired = (datetime.now() + timedelta(days=days)).isoformat()
    warranty = (datetime.now() + timedelta(days=warranty_days)).isoformat() if warranty_days > 0 else None
    
    user["tier"] = tier
    user["expired"] = expired
    user["warranty"] = warranty
    
    save_user(uid, user)
    
    return {
        "success": True,
        "tier": tier,
        "expired": expired,
        "warranty": warranty
    }

def make_reseller(uid):
    """Convert user to reseller"""
    uid = str(uid)
    user = get_user(uid)
    user["is_reseller"] = True
    user["tier"] = "reseller"
    
    # Give unlimited access
    user["expired"] = (datetime.now() + timedelta(days=9999)).isoformat()
    
    save_user(uid, user)
    return True

def add_reseller_customer(seller_uid, customer_uid, tier, days=30):
    """Reseller kasih akses ke customer mereka"""
    seller_uid = str(seller_uid)
    customer_uid = str(customer_uid)
    
    seller = get_user(seller_uid)
    if not seller.get("is_reseller"):
        return False
    
    # Grant access to customer
    grant_access(customer_uid, tier, days, warranty_days=0)
    
    # Track customer di reseller
    if customer_uid not in seller.get("reseller_customers", []):
        seller["reseller_customers"].append(customer_uid)
        save_user(seller_uid, seller)
    
    return True

def remove_reseller_customer(seller_uid, customer_uid):
    """Remove customer dari reseller"""
    seller_uid = str(seller_uid)
    customer_uid = str(customer_uid)
    
    seller = get_user(seller_uid)
    if customer_uid in seller.get("reseller_customers", []):
        seller["reseller_customers"].remove(customer_uid)
        save_user(seller_uid, seller)
        return True
    return False

def update_settings(uid, key, value):
    """Update user settings"""
    uid = str(uid)
    user = get_user(uid)
    
    if "settings" not in user:
        user["settings"] = {}
    
    user["settings"][key] = value
    save_user(uid, user)
    return True

def add_keyword(uid, keyword, response):
    """Add auto reply keyword"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    keywords = st.get("ar_keywords", [])
    
    # Check if already exists
    for kw in keywords:
        if kw.get("keyword", "").lower() == keyword.lower():
            return False
    
    keywords.append({
        "keyword": keyword,
        "response": response,
        "enabled": True
    })
    
    st["ar_keywords"] = keywords
    user["settings"] = st
    save_user(uid, user)
    return True

def remove_keyword(uid, keyword):
    """Remove auto reply keyword"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    keywords = st.get("ar_keywords", [])
    keywords = [kw for kw in keywords if kw.get("keyword", "").lower() != keyword.lower()]
    
    st["ar_keywords"] = keywords
    user["settings"] = st
    save_user(uid, user)
    return True

def add_banword(uid, word):
    """Add ban word"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    banwords = st.get("ar_banwords", [])
    word = word.strip().lower()
    
    if word not in banwords:
        banwords.append(word)
    
    st["ar_banwords"] = banwords
    user["settings"] = st
    save_user(uid, user)
    return True

def remove_banword(uid, word):
    """Remove ban word"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    banwords = st.get("ar_banwords", [])
    word = word.strip().lower()
    
    banwords = [b for b in banwords if b != word]
    
    st["ar_banwords"] = banwords
    user["settings"] = st
    save_user(uid, user)
    return True

def add_bc_target(uid, target):
    """Add broadcast target"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    targets = st.get("bc_targets", [])
    target = target.strip()
    
    if target not in targets:
        targets.append(target)
    
    st["bc_targets"] = targets
    user["settings"] = st
    save_user(uid, user)
    return True

def remove_bc_target(uid, target):
    """Remove broadcast target"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    targets = st.get("bc_targets", [])
    targets = [t for t in targets if t != target.strip()]
    
    st["bc_targets"] = targets
    user["settings"] = st
    save_user(uid, user)
    return True

def add_fw_target(uid, target):
    """Add forward target"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    targets = st.get("fw_targets", [])
    target = target.strip()
    
    # Check if already exists
    if isinstance(targets, list):
        for t in targets:
            if isinstance(t, dict) and t.get("target") == target:
                return False
            if isinstance(t, str) and t == target:
                return False
    
    # Add new target
    if isinstance(targets, list) and targets and isinstance(targets[0], dict):
        targets.append({"target": target, "delay": 5})
    else:
        targets.append(target)
    
    st["fw_targets"] = targets
    user["settings"] = st
    save_user(uid, user)
    return True

def remove_fw_target(uid, target):
    """Remove forward target"""
    uid = str(uid)
    user = get_user(uid)
    st = user.get("settings", {})
    
    targets = st.get("fw_targets", [])
    target = target.strip()
    
    if isinstance(targets, list):
        new_targets = []
        for t in targets:
            if isinstance(t, dict) and t.get("target") != target:
                new_targets.append(t)
            elif isinstance(t, str) and t != target:
                new_targets.append(t)
        st["fw_targets"] = new_targets
    
    user["settings"] = st
    save_user(uid, user)
    return True

def get_user_info(uid):
    """Get full user info"""
    user = get_user(uid)
    
    return {
        "uid": uid,
        "tier": user.get("tier"),
        "expired": user.get("expired"),
        "warranty": user.get("warranty"),
        "is_reseller": user.get("is_reseller"),
        "customers": len(user.get("reseller_customers", [])),
        "session_status": "✅" if user.get("session") else "❌",
        "trial_claimed": user.get("claimed_trial")
    }

def get_pricing():
    """Get pricing structure"""
    return {
        "jaseb_only": {
            "name": "🔵 Jaseb Only",
            "1_bulan_nogar": 3500,
            "1_bulan_fullgar": 4000,
            "permanen_nogar": 10000,
            "permanen_fullgar": 18000
        },
        "autoreply": {
            "name": "🟢 Auto-Reply",
            "1_bulan_nogar": 5000,
            "1_bulan_fullgar": 7000,
            "permanen_nogar": 20000,
            "permanen_fullgar": 30000
        },
        "full": {
            "name": "🟡 Full Fitur",
            "1_bulan_nogar": 7000,
            "1_bulan_fullgar": 10000,
            "permanen_nogar": 25000,
            "permanen_fullgar": 35000
        },
        "reseller": {
            "name": "👑 Reseller",
            "1_bulan": 40000,
            "permanen": 250000
        }
    }
    
