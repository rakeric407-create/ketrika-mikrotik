import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets

DB_NAME = "ketrika.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle TEXT UNIQUE NOT NULL,
        client_nom TEXT NOT NULL,
        client_telephone TEXT,
        type_abonnement TEXT,
        date_creation TEXT,
        date_expiration TEXT,
        actif INTEGER DEFAULT 1,
        nb_utilisations INTEGER DEFAULT 0,
        prix_paye REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cle_licence TEXT,
        client_final TEXT,
        modele_mikrotik TEXT,
        type_config TEXT,
        options_json TEXT,
        warp_private_key TEXT,
        warp_public_key TEXT,
        warp_client_ip TEXT,
        date_creation TEXT,
        config_id TEXT UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT
    )''')
    admin_pass = hashlib.sha256("ketrika2025".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)", ("admin", admin_pass))
    
    # 4 CLÉS DE TEST PERMANENTES (UNE POUR CHAQUE NIVEAU DE PRIX)
    test_exp = (datetime.now() + timedelta(days=365)).isoformat()
    c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, prix_paye) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("KTR-BASE-10K-TEST", "Client 10k Test", "0382817100", "base", datetime.now().isoformat(), test_exp, 10000))
    c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, prix_paye) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("KTR-WARP-20K-TEST", "Client 20k Test", "0382817100", "warp", datetime.now().isoformat(), test_exp, 20000))
    c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, prix_paye) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("KTR-HOTSPOT-30K-TEST", "Client 30k Test", "0382817100", "hotspot", datetime.now().isoformat(), test_exp, 30000))
    c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, prix_paye) VALUES (?, ?, ?, ?, ?, ?, ?)",
              ("KTR-PRO-50K-TEST", "Client 50k Test", "0382817100", "pro", datetime.now().isoformat(), test_exp, 50000))
    
    conn.commit()
    conn.close()

def generer_cle_licence():
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return f"KTR-{parts[0]}-{parts[1]}-{parts[2]}"

def creer_licence(client_nom, telephone, type_abo, prix):
    cle = generer_cle_licence()
    date_creation = datetime.now().isoformat()
    expiration = datetime.now() + timedelta(days=365) # Valide 1 an par défaut
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO licences 
                 (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, prix_paye) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (cle, client_nom, telephone, type_abo, date_creation, expiration.isoformat(), prix))
    conn.commit()
    conn.close()
    return cle

def verifier_licence(cle):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM licences WHERE cle=? AND actif=1", (cle,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    expiration = datetime.fromisoformat(row[6])
    if expiration < datetime.now():
        return {"valide": False, "raison": "Licence expiree"}
    return {"valide": True, "id": row[0], "client": row[2], "type": row[4], "expiration": row[6], "utilisations": row[8]}

def incrementer_utilisation(cle):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE licences SET nb_utilisations = nb_utilisations + 1 WHERE cle=?", (cle,))
    conn.commit()
    conn.close()

def sauvegarder_config(cle, client_final, modele, type_config, options, warp_data, config_id):
    import json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO configurations 
                 (cle_licence, client_final, modele_mikrotik, type_config, options_json, warp_private_key, warp_public_key, warp_client_ip, date_creation, config_id) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (cle, client_final, modele, type_config, json.dumps(options),
               warp_data.get("private_key", ""), warp_data.get("public_key", ""), warp_data.get("client_ip", ""),
               datetime.now().isoformat(), config_id))
    conn.commit()
    conn.close()

def get_config_by_id(config_id):
    import json
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM configurations WHERE config_id=?", (config_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "cle": row[1], "client": row[2], "modele": row[3],
            "type": row[4], "options": json.loads(row[5]),
            "warp_private": row[6], "warp_public": row[7], "warp_ip": row[8]
        }
    return None

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(prix_paye) FROM licences WHERE actif=1")
    total, revenu = c.fetchone()
    c.execute("SELECT COUNT(*) FROM configurations")
    nb_configs = c.fetchone()[0]
    conn.close()
    return {
        "total_clients": total or 0,
        "revenu_total": revenu or 0,
        "nb_configs": nb_configs
    }

def verifier_admin(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE username=? AND password_hash=?", (username, password_hash))
    row = c.fetchone()
    conn.close()
    return row is not None
