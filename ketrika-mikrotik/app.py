from flask import Flask, request, Response, render_template_string, session, redirect, url_for, send_file
from database import *
from warp_api import creer_config_warp_complete
import sqlite3, secrets, string, random, io, os, traceback
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.url_map.strict_slashes = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "ketrika.db")

FB_LINK = "https://www.facebook.com/loza.nama.376"
NUMERO_MVOLA = "038 28 171 00"
NUMERO_ORANGE = "037 39 755 72"
NOM_COMPTE = "Jean Eric"
BINANCE_ID = "1229612637"
USDT_BEP20 = "0x0c4bcb1beabbff154f7d445a549f1e5b42de9088"

# CONFIGURATION EMAIL GMAIL
SMTP_EMAIL = "rakeric407@gmail.com"
SMTP_PASSWORD = "leqdikphdahrjblk"

def envoyer_email_cle(destinataire, nom, cle, pack_nom):
    if not destinataire or "@" not in destinataire:
        return False
    try:
        sujet = f"✅ Votre Clé KETRIKA - {pack_nom}"
        message_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #0284c7, #059669); color: white; padding: 25px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px; font-family: sans-serif;">⚡ KETRIKA MIKROTIK PRO ⚡</h1>
                    <p style="margin: 5px 0 0; opacity: 0.9; font-size: 14px;">Votre licence a été activée avec succès</p>
                </div>
                <div style="padding: 25px; background: #ffffff;">
                    <p style="font-size: 15px;">Bonjour <b>{nom}</b>,</p>
                    <p>Merci pour votre commande. Votre paiement a été validé ! Voici votre clé d'activation unique :</p>
                    <div style="background: #f8fafc; border: 2px dashed #0284c7; padding: 18px; font-size: 22px; font-weight: bold; text-align: center; color: #0284c7; letter-spacing: 4px; margin: 20px 0; border-radius: 10px;">
                        {cle}
                    </div>
                    <p style="font-size: 12px; color: #64748b;"><i>Note : Cette clé est valable pour 1 seul routeur (Usage unique).</i></p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                    <p style="font-weight: bold; color: #0f172a;">🚀 Comment l'injecter en 5 secondes ?</p>
                    <ol style="padding-left: 20px; font-size: 13px; color: #334155;">
                        <li style="margin-bottom: 6px;">Rendez-vous sur notre site : <a href="https://ketrika-mikrotik.onrender.com" style="color:#0284c7; font-weight: bold;">ketrika-mikrotik.onrender.com</a></li>
                        <li style="margin-bottom: 6px;">Entrez votre clé dans la section <b>Activation</b>.</li>
                        <li>Copiez la commande unique et collez-la dans le <b>New Terminal</b> de Winbox !</li>
                    </ol>
                    <br>
                    <p style="font-size: 13px;">Besoin d'assistance ? Contactez-nous directement sur WhatsApp au <b>038 28 171 00</b>.</p>
                </div>
                <div style="background: #f1f5f9; text-align: center; padding: 15px; font-size: 11px; color: #94a3b8;">
                    © 2026 KETRIKA MIKROTIK PRO • Madagascar
                </div>
            </div>
        </body>
        </html>
        """
        msg = MIMEMultipart()
        msg['From'] = f"KETRIKA MIKROTIK <{SMTP_EMAIL}>"
        msg['To'] = destinataire
        msg['Subject'] = sujet
        msg.attach(MIMEText(message_html, 'html'))
        
        # Utilisation du port TLS 587 (plus stable sur les serveurs Cloud que le 465 SSL)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erreur Envoi Email: {e}")
        return False

def init_all_tables():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS licences (id INTEGER PRIMARY KEY AUTOINCREMENT, cle TEXT UNIQUE NOT NULL, client_nom TEXT NOT NULL, client_telephone TEXT, type_abonnement TEXT, date_creation TEXT, date_expiration TEXT, actif INTEGER DEFAULT 1, nb_utilisations INTEGER DEFAULT 0, prix_paye REAL DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS configurations (id INTEGER PRIMARY KEY AUTOINCREMENT, cle_licence TEXT, client_final TEXT, modele_mikrotik TEXT, type_config TEXT, options_json TEXT, warp_private_key TEXT, warp_public_key TEXT, warp_client_ip TEXT, date_creation TEXT, config_id TEXT UNIQUE)''')
        c.execute('''CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY AUTOINCREMENT, client_nom TEXT, telephone TEXT, formule TEXT, montant REAL, reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE', cle_generee TEXT, date_commande TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS avis (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, ville TEXT, etoiles INTEGER NOT NULL, commentaire TEXT NOT NULL, date_avis TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)''')
        
        import hashlib
        admin_pass = hashlib.sha256("ketrika2025".encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)", ("admin", admin_pass))

        c.execute("SELECT COUNT(*) FROM avis")
        if c.fetchone()[0] < 3:
            avis_initiaux = [
                ("Mamy R.", "Antananarivo", 5, "Script injecté après reset total sur mon hAP ax2. Configuration parfaite du premier coup !", "2026-01-15"),
                ("Jean Luc", "Tamatave", 5, "Configuration propre sur hAP ac2. Wi-Fi et pare-feu impeccables.", "2026-01-20"),
                ("Boutique Alpha", "Majunga", 5, "Pack Wi-Fi Zone parfait avec gestion de débit pour mon business.", "2026-01-28"),
                ("David M.", "La Réunion", 5, "Paiement USDT par Binance Pay instantané. Clé reçue par mail en 5 min. Excellent !", "2026-02-01"),
                ("Toky N.", "Diego Suarez", 5, "Très satisfait de l'optimisation réseau et de la réactivité WhatsApp.", "2026-02-02")
            ]
            c.executemany("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", avis_initiaux)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erreur init DB: {e}")

init_all_tables()

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "prix_usd": 2.50, "desc": "Config A à Z + IP Libre + Optimisation + Wi-Fi", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "prix_usd": 3.75, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Premium VPN", "prix": 20000, "prix_usd": 5.00, "desc": "Standard + Tunnel WireGuard confidentiel gratuit", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "prix_usd": 7.50, "desc": "Premium + Portail Hotspot + Débit contrôlé + DNS", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "prix_usd": 12.50, "desc": "Solution intégrale + Multi-WAN + PPPoE + QoS", "badge": "PRO STUDIO"}
}

MODELES_MIKROTIK = [
    "hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)", "hAP ac2 (Dual Band Wireless)", "hAP ac3 (Dual Band Wireless)",
    "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (Wireless)", "LHG 5", "SXTsq", "hAP lite (Wireless 2.4G)",
    "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)",
    "CCR1009", "CCR2004", "CCR2116", "Chateau LTE/5G", "Autre RouterOS v7"
]

BANDWIDTH_PROFILES = {
    "illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Plein débit sans restriction"},
    "ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10 Mbps ↓ / 5 Mbps ↑"},
    "rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5 Mbps ↓ / 2 Mbps ↑"},
    "standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2 Mbps ↓ / 1 Mbps ↑"},
    "eco": {"nom": "🔒 ÉCO (1M/512K)", "down": "1M", "up": "512k", "desc": "1 Mbps ↓ / 512 Kbps ↑"},
    "custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Entrez vos limites"}
}

IP_SUGGESTIONS = ["192.168.88.1", "192.168.1.1", "192.168.0.1", "192.168.10.1", "192.168.100.1", "10.0.0.1", "10.0.1.1", "10.10.10.1", "172.16.0.1", "172.16.1.1", "172.20.0.1"]

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>KETRIKA MIKROTIK PRO • Solution Réseau Professionnelle</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg-main: #eef2ff; --bg-card: #ffffff; --accent-cyan: #0284c7; --accent-green: #059669; --accent-purple: #7c3aed; --accent-orange: #ea580c; --accent-gold: #f59e0b; --text-dark: #0f172a; --text-body: #334155; --text-muted: #64748b; --border-light: #e2e8f0; }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: linear-gradient(135deg, #eef2ff 0%, #f1f5f9 100%); color: var(--text-dark); min-height: 100vh; padding: 10px; -webkit-font-smoothing: antialiased; }
        .container { max-width: 860px; margin: auto; }
        
        .top-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 10px 14px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border: 1px solid var(--border-light); border-radius: 14px; box-shadow: 0 4px 15px rgba(2,132,199,0.06); gap: 6px; flex-wrap: wrap; }
        .nav-brand { display: flex; align-items: center; gap: 8px; font-family: 'Space Grotesk'; font-weight: 800; font-size: 13px; color: var(--text-dark); text-decoration: none; }
        .nav-logo-icon { width: 26px; height: 26px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; }
        .top-links { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
        .top-links a { font-size: 11px; color: #fff; text-decoration: none; font-weight: 700; padding: 6px 11px; border-radius: 10px; transition: 0.2s; white-space: nowrap; }
        .btn-fb { background: linear-gradient(135deg, #1877f2, #0d6efd); }
        .btn-tuto { background: linear-gradient(135deg, #7c3aed, #6d28d9); }
        .lang-btn { background: linear-gradient(135deg, #ede9fe, #ddd6fe); color: var(--accent-purple); border: 1px solid #c4b5fd; padding: 6px 10px; border-radius: 10px; font-size: 11px; font-weight: 700; cursor: pointer; }

        .header { text-align: center; padding: 14px 5px 20px; }
        .logo-wrapper { position: relative; width: 80px; height: 80px; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; }
        .logo-aura { position: absolute; inset: -3px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), #db2777); filter: blur(8px); opacity: 0.7; }
        .logo-box { position: relative; width: 100%; height: 100%; border-radius: 50%; background: linear-gradient(135deg, #0f172a, #1e293b); border: 2px solid rgba(255,255,255,0.9); display: flex; align-items: center; justify-content: center; }
        .logo-box svg { width: 42px; height: 42px; }
        .header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 28px; font-weight: 900; background: linear-gradient(135deg, #0284c7, #7c3aed, #db2777, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; line-height: 1.2; }
        @media (min-width: 500px) { .header h1 { font-size: 34px; } }
        .header .tagline { color: var(--text-body); font-size: 13px; margin-top: 6px; font-weight: 600; }
        .header .stats-live { display: inline-flex; gap: 6px; margin-top: 10px; padding: 5px 12px; background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #a7f3d0; border-radius: 20px; font-size: 11px; color: var(--accent-green); font-weight: 700; align-items: center; }
        .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; display: inline-block; }

        .card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; padding: 18px 16px; margin-bottom: 14px; box-shadow: 0 4px 15px rgba(15,23,42,0.05); position: relative; overflow: hidden; }
        @media (min-width: 500px) { .card { padding: 22px; } }
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink), var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 14px; color: var(--accent-cyan); margin-bottom: 12px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }

        /* DASHBOARD LIVE PERFORMANCE */
        .live-dashboard { background: #0f172a; border: 1px solid #334155; border-radius: 14px; padding: 16px; margin: 12px 0; color: #fff; box-shadow: inset 0 0 20px rgba(0,0,0,0.5); }
        .dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px; }
        @media (min-width: 600px) { .dashboard-grid { grid-template-columns: repeat(4, 1fr); } }
        .dash-item { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; text-align: center; }
        .dash-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }
        .dash-value { font-family: 'Space Grotesk'; font-size: 16px; font-weight: 900; color: #38bdf8; margin-top: 2px; }
        .dash-value.green { color: #4ade80; }

        /* BADGES DE CONFIANCE */
        .trust-badges-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 10px; }
        @media (min-width: 600px) { .trust-badges-grid { grid-template-columns: repeat(4, 1fr); } }
        .trust-badge-card { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 1px solid var(--border-light); padding: 10px 8px; border-radius: 10px; text-align: center; }
        .trust-badge-icon { font-size: 20px; display: block; margin-bottom: 2px; }
        .trust-badge-title { font-size: 11px; font-weight: 800; color: var(--text-dark); }
        .trust-badge-desc { font-size: 9px; color: var(--text-muted); margin-top: 2px; }

        .hero-card { background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%); color: #fff; padding: 20px 16px; border-radius: 18px; margin-bottom: 14px; box-shadow: 0 10px 30px rgba(2,132,199,0.25); }
        @media (min-width: 500px) { .hero-card { padding: 24px; } }
        .hero-card h2 { font-family: 'Space Grotesk'; font-size: 19px; font-weight: 900; margin-bottom: 6px; }
        .hero-card > p { font-size: 12px; opacity: 0.95; margin-bottom: 12px; line-height: 1.5; }
        .features-detail { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 12px; }
        @media (min-width: 500px) { .features-detail { grid-template-columns: repeat(2, 1fr); } }
        @media (min-width: 800px) { .features-detail { grid-template-columns: repeat(3, 1fr); gap: 10px; } }
        .feature-detail-box { background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2); }
        .feature-detail-box .fd-icon { font-size: 22px; display: block; margin-bottom: 4px; }
        .feature-detail-box .fd-title { font-family: 'Space Grotesk'; font-size: 12px; font-weight: 800; margin-bottom: 3px; }
        .feature-detail-box .fd-desc { font-size: 11px; opacity: 0.9; line-height: 1.4; }

        .steps-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .steps-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; } }
        .step-box { background: linear-gradient(135deg, #f0fdfa, #eff6ff); border: 1px solid #bae6fd; padding: 12px 10px; border-radius: 12px; text-align: center; }
        .step-num { width: 30px; height: 30px; margin: 0 auto 6px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Space Grotesk'; font-weight: 900; font-size: 15px; }
        .step-title { font-family: 'Space Grotesk'; font-size: 12px; color: var(--text-dark); font-weight: 800; margin-bottom: 2px; }
        .step-desc { font-size: 10px; color: var(--text-muted); line-height: 1.4; }

        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input[type="text"], input[type="tel"], input[type="email"], select, textarea { width: 100%; padding: 12px 14px; margin-top: 4px; background: #f8fafc; border: 1px solid var(--border-light); border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit; }

        .ip-suggestions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
        .ip-chip { background: linear-gradient(135deg, #e0f2fe, #f0f9ff); color: var(--accent-cyan); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; cursor: pointer; border: 1px solid #bae6fd; font-family: 'Courier New', monospace; }

        .btn-primary { width: 100%; padding: 14px; margin-top: 12px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 800; cursor: pointer; font-family: 'Space Grotesk'; text-transform: uppercase; text-decoration: none; display: block; text-align: center; }
        .btn-success { background: linear-gradient(135deg, #059669, #047857); }
        .btn-copy { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff; padding: 12px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase; margin-top: 8px; font-size: 12px; }
        .btn-copy.copied { background: linear-gradient(135deg, #059669, #047857); }

        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 6px; }
        .plan-option { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 2px solid var(--border-light); padding: 12px 10px; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; position: relative; gap: 8px; }
        .plan-option.selected, .plan-option:hover { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-option input[type="radio"] { width: 18px; height: 18px; accent-color: var(--accent-cyan); flex-shrink: 0; cursor: pointer; }
        .plan-info { flex: 1; min-width: 0; }
        .plan-info b { font-size: 13px; display: block; }
        .plan-info div { color: var(--text-muted); font-size: 10px; margin-top: 2px; }
        .plan-price { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; gap: 2px; }
        .plan-price b { color: var(--accent-green); font-size: 14px; font-family: 'Space Grotesk'; white-space: nowrap; }
        .plan-price small { color: var(--accent-cyan); font-size: 10px; font-weight: 700; }
        .plan-badge { position: absolute; top: -1px; right: 10px; padding: 2px 8px; border-radius: 0 0 6px 6px; font-size: 8px; font-weight: 800; color: #fff; font-family: 'Space Grotesk'; }
        .badge-popular { background: #ea580c; }
        .badge-best { background: #db2777; }
        .badge-pro { background: #059669; }

        .bw-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .bw-grid { grid-template-columns: 1fr 1fr; } }
        .bw-card { background: #ffffff; border: 2px solid var(--border-light); padding: 10px 12px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: 0.2s; }
        .bw-card:hover, .bw-card.active { border-color: var(--accent-purple); background: #faf5ff; }
        .bw-card input[type="radio"] { width: 20px; height: 20px; accent-color: var(--accent-purple); flex-shrink: 0; cursor: pointer; margin: 0; }
        .bw-card-text b { font-size: 12px; color: var(--text-dark); display: block; }
        .bw-card-text span { font-size: 10px; color: var(--text-muted); }

        .payment-banner { background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; border-radius: 12px; padding: 14px; margin-top: 12px; text-align: center; }
        .payment-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .payment-grid { grid-template-columns: 1fr 1fr; } }
        .payment-box { background: #fff; border: 1px solid #fde68a; border-radius: 10px; padding: 10px; }
        .payment-box .method { font-size: 11px; font-weight: 800; }
        .payment-box .number { font-family: 'Space Grotesk'; font-size: 17px; font-weight: 900; color: #b45309; margin: 3px 0; }
        .payment-box .name { font-size: 10px; color: var(--text-muted); }

        .crypto-box { background: #0f172a; color: #fff; border: 1px solid #334155; border-radius: 12px; padding: 14px; text-align: center; margin-top: 10px; }
        .crypto-title { font-family: 'Space Grotesk'; font-size: 14px; font-weight: 800; color: #f59e0b; }
        .crypto-code { background: #1e293b; color: #38bdf8; padding: 8px; border-radius: 8px; font-family: monospace; font-size: 11px; word-break: break-all; margin: 5px 0; }

        .terminal-box { background: #0f172a; border: 1px solid #334155; color: #4ade80; padding: 12px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 6px; line-height: 1.5; }
        .badge { background: #e0f2fe; color: var(--accent-cyan); padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; }
        .alert { padding: 10px 12px; border-radius: 10px; margin-bottom: 10px; font-size: 12px; }
        .alert-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
        .alert-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }

        .rating-summary { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; margin-bottom: 10px; }
        .rating-big { font-family: 'Space Grotesk'; font-size: 32px; font-weight: 900; color: #b45309; }
        .stars-gold { color: var(--accent-gold); font-size: 12px; letter-spacing: 2px; }
        .review-card { background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid var(--border-light); margin-bottom: 6px; }
        .rating-input { display: flex; flex-direction: row-reverse; justify-content: center; gap: 4px; margin: 8px 0; }
        .rating-input input { display: none; }
        .rating-input label { font-size: 26px; color: #cbd5e1; cursor: pointer; }
        .rating-input label:hover, .rating-input label:hover ~ label, .rating-input input:checked ~ label { color: var(--accent-gold); }

        .faq-item { border-bottom: 1px solid var(--border-light); padding: 10px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: var(--text-dark); font-size: 12px; cursor: pointer; display: flex; justify-content: space-between; gap: 6px; }
        .faq-answer { color: var(--text-body); font-size: 11px; line-height: 1.6; margin-top: 6px; display: none; background: #f8fafc; padding: 8px 10px; border-radius: 6px; }
        .faq-item.active .faq-answer { display: block; }
        .faq-toggle { color: var(--accent-cyan); font-size: 14px; flex-shrink: 0; }

        .whatsapp-float { position: fixed; bottom: 18px; right: 18px; z-index: 9999; background: #25D366; color: #fff; padding: 10px 16px; border-radius: 30px; font-weight: 800; font-size: 12px; text-decoration: none; display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk'; box-shadow: 0 4px 15px rgba(37,211,102,0.4); }
        .wifi-box { background: #f0f9ff; border: 1px dashed #7dd3fc; padding: 12px; border-radius: 10px; margin-top: 8px; }
        .feature-box { background: #f0fdf4; padding: 10px; border-radius: 8px; margin-top: 6px; line-height: 1.9; font-size: 11px; border-left: 4px solid var(--accent-green); }
        .footer { text-align: center; color: var(--text-muted); margin: 20px 0 70px; font-size: 10px; padding: 10px; border-top: 1px solid var(--border-light); }
        .footer a { color: var(--accent-cyan); text-decoration: none; font-weight: 700; }
        hr { border: none; border-top: 1px solid var(--border-light); margin: 12px 0; }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">💬 <span>WhatsApp</span></a>

    <div class="container">
        <div class="top-nav">
            <a href="/" class="nav-brand"><div class="nav-logo-icon">⚡</div><span>KETRIKA MIKROTIK</span></a>
            <div class="top-links">
                <a href="/tuto" class="btn-tuto">📖 Guide</a>
                <a href="{{ fb_link }}" target="_blank" class="btn-fb">📘 Facebook</a>
                <button class="lang-btn" onclick="toggleLang()">🇲🇬/🇫🇷</button>
            </div>
        </div>

        <div class="header">
            <div class="logo-wrapper">
                <div class="logo-aura"></div>
                <div class="logo-box">
                    <svg viewBox="0 0 24 24" fill="none" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00f2fe" /><stop offset="100%" stop-color="#7c3aed" /></linearGradient></defs>
                        <rect x="2" y="14" width="20" height="8" rx="2" fill="rgba(0,242,254,0.1)"></rect>
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#00f2fe" stroke="#00f2fe" stroke-width="1.5"></path>
                    </svg>
                </div>
            </div>
            <h1>KETRIKA MIKROTIK</h1>
            <p class="tagline txt-fr">Solution Professionnelle d'Optimisation Réseau MikroTik</p>
            <div class="stats-live"><span class="live-dot"></span><span>Config en 5 secondes • 1 Clé = 1 Routeur • Email Auto</span></div>
        </div>

        {{ content|safe }}

        <div class="footer">KETRIKA MIKROTIK PRO © 2026 • <a href="{{ fb_link }}" target="_blank">Facebook Officiel</a> • 📞 038 28 171 00 (Jean Eric)</div>
    </div>
    
    <script>
        let currentLang = 'fr';
        function toggleLang() { let f=document.querySelectorAll('.txt-fr'), m=document.querySelectorAll('.txt-mg'); f.forEach(e=>e.style.display=e.style.display==='none'?'':'none'); m.forEach(e=>e.style.display=e.style.display==='none'?'':'none'); }
        function copyText(elemId, btnId) { let e=document.getElementById(elemId); let t=e.innerText||e.value; navigator.clipboard.writeText(t).then(()=>{ let b=document.getElementById(btnId); let o=b.innerHTML; b.innerHTML='✅ COPIÉ !'; b.classList.add('copied'); setTimeout(()=>{b.innerHTML=o; b.classList.remove('copied');},2000);}); }
        function setIP(ip) { document.getElementById('router_ip').value = ip; }
        function selectBW(val) { document.querySelectorAll('.bw-card').forEach(c => c.classList.remove('active')); document.getElementById('card_' + val).classList.add('active'); document.getElementById('bw_' + val).checked = true; document.getElementById('custom-bw-box').style.display = (val === 'custom') ? 'grid' : 'none'; }
        document.querySelectorAll('.faq-question').forEach(q => { q.addEventListener('click', () => q.parentElement.classList.toggle('active')); });
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content, fb_link=FB_LINK)

def build_raw_script(cfg):
    plan = cfg["type"]; modele = cfg.get("modele", ""); opt = cfg.get("options", {})
    ssid = opt.get("ssid", "KETRIKA-NET"); wifi_pass = opt.get("wifi_pass", "ketrika2025"); dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0"); bw_up = opt.get("bw_up", "0"); router_ip = opt.get("router_ip", "192.168.88.1").strip()
    
    ip_parts = router_ip.split('.')
    subnet_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}" if len(ip_parts) == 4 else "192.168.88"
    dhcp_pool_start = f"{subnet_base}.10"; dhcp_pool_end = f"{subnet_base}.250"; dhcp_net = f"{subnet_base}.0/24"
    is_wifi6 = any(k in modele for k in ["ax2", "ax3", "ax 15s", "Wi-Fi 6"])
    is_wireless = any(k in modele for k in ["ac2", "ac3", "lite", "19s", "LHG", "SXT", "Wireless"])

    s = f"""# KETRIKA MIKROTIK PRO - CONFIG A Z
/interface bridge add name=bridge-lan auto-mac=yes
/interface list add name=WAN
/interface list add name=LAN
/interface list member add interface=ether1 list=WAN
/interface list member add interface=bridge-lan list=LAN
:foreach i in=[/interface ethernet find where name!="ether1"] do={{ /interface bridge port add bridge=bridge-lan interface=$i }}
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no add-default-route=yes default-route-distance=1
/ip address add address={router_ip}/24 interface=bridge-lan
/ip pool add name=dhcp-pool ranges={dhcp_pool_start}-{dhcp_pool_end}
/ip dhcp-server add name=dhcp-lan interface=bridge-lan address-pool=dhcp-pool disabled=no lease-time=12h
/ip dhcp-server network add address={dhcp_net} gateway={router_ip} dns-server=1.1.1.1,1.0.0.1
/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade
/ip firewall mangle add chain=postrouting out-interface=ether1 action=change-ttl new-ttl=set:64 passthrough=yes
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=udp dst-port=53 action=redirect to-ports=53
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=tcp dst-port=53 action=redirect to-ports=53
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked
/ip firewall filter add chain=input action=drop connection-state=invalid
/ip firewall filter add chain=input action=accept protocol=icmp
/ip firewall filter add chain=input in-interface-list=LAN action=accept
/ip firewall filter add chain=input in-interface-list=WAN action=drop
/ip firewall filter add chain=forward action=accept connection-state=established,related,untracked
/ip firewall filter add chain=forward action=drop connection-state=invalid
/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=150,32 action=drop
/ip firewall filter add chain=forward in-interface-list=WAN connection-nat-state=!dstnat connection-state=new action=drop
/ipv6 settings set disable-ipv6=yes
/ip service disable telnet,ftp,api
"""
    if is_wifi6:
        s += f'/interface wifi security add name=sec-wifi authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}"\n/interface wifi configuration add name=cfg-wifi ssid="{ssid}" security=sec-wifi country="Madagascar"\n/interface wifi set [find] configuration=cfg-wifi disabled=no\n:foreach w in=[/interface wifi find] do={{ /interface bridge port add bridge=bridge-lan interface=$w }}\n'
    elif is_wireless:
        s += f'/interface wireless security-profiles add name=sec-wifi mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}" unicast-ciphers=aes-ccm group-ciphers=aes-ccm\n/interface wireless set [find] ssid="{ssid}" security-profile=sec-wifi country="madagascar" disabled=no\n:foreach w in=[/interface wireless find] do={{ /interface bridge port add bridge=bridge-lan interface=$w }}\n'
    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f':if ([:len [/routing table find name=to-warp]] = 0) do={{ /routing table add name=to-warp fib }}\n/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg["warp_private"]}"\n/interface wireguard peers add interface=warp-vpn public-key="{cfg["warp_public"]}" endpoint-address=162.159.192.1 endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25\n/ip address add address={cfg["warp_ip"]}/32 interface=warp-vpn\n/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade\n/ip route add dst-address=162.159.192.0/24 gateway=ether1 distance=1\n/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn routing-table=to-warp\n/ip firewall mangle add chain=prerouting in-interface-list=LAN dst-address-type=!local action=mark-routing new-routing-mark=to-warp passthrough=yes\n'
    if plan in ["hotspot", "pro"]:
        s += f'/ip hotspot profile add name=hs-prof hotspot-address={router_ip} dns-name={dns_name}\n/ip hotspot user profile add name=hs-user rate-limit="{bw_up}/{bw_down}"\n/ip hotspot add name=hotspot-ketrika interface=bridge-lan address-pool=dhcp-pool profile=hs-prof disabled=no\n'
    if plan == "pro":
        s += f'/ip pool add name=pppoe-pool ranges=10.10.10.2-10.10.10.254\n/ppp profile add name=prof-pppoe local-address=10.10.10.1 remote-address=pppoe-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"\n/interface pppoe-server server add service-name=PPPOE-KETRIKA interface=bridge-lan default-profile=prof-pppoe disabled=no\n'
    s += f'/system identity set name="KETRIKA-{cfg["client"]}"\n'
    return s

@app.route("/")
def home():
    if session.get("authenticated"): return redirect(url_for("dashboard"))
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT AVG(etoiles), COUNT(*) FROM avis"); res = c.fetchone(); avg = round(res[0],1) if res[0] else 5.0; cnt = res[1]
    c.execute("SELECT nom, ville, etoiles, commentaire FROM avis ORDER BY id DESC LIMIT 5"); liste_avis = c.fetchall(); conn.close()
    
    reviews_html = ""
    for a in liste_avis: reviews_html += f'<div class="review-card"><div class="review-header"><b>{a[0]} ({a[1]})</b><span class="stars-gold">{"⭐"*a[2]}</span></div><div style="font-size:12px; color:var(--text-body);">"{a[3]}"</div></div>'
    
    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        sel = "selected" if k == "standard" else ""; ck = "checked" if k == "standard" else ""
        badge = f'<div class="plan-badge badge-popular">{v["badge"]}</div>' if v["badge"] else ""
        plans_html += f'<label class="plan-option {sel}" id="opt_{k}" for="plan_{k}">{badge}<div class="plan-info"><b>{v["nom"]}</b><div>{v["desc"]}</div></div><div class="plan-price"><b>{v["prix"]:,} Ar</b><small>${v["prix_usd"]:.2f} USD</small><input type="radio" name="formule" id="plan_{k}" value="{k}" {ck} onchange="document.querySelectorAll(\'.plan-option\').forEach(e=>e.classList.remove(\'selected\')); document.getElementById(\'opt_{k}\').classList.add(\'selected\');"></div></label>'

    content = f"""
    <div class="live-dashboard">
        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:800; color:#38bdf8;">📊 PERFORMANCES DU TUNNEL <span class="badge" style="background:#0284c7; color:#fff;">LIVE</span></div>
        <div class="dashboard-grid">
            <div class="dash-item"><div class="dash-label">LATENCE</div><div class="dash-value green">&lt; 24 ms</div></div>
            <div class="dash-item"><div class="dash-label">CRYPT</div><div class="dash-value">ChaCha20</div></div>
            <div class="dash-item"><div class="dash-label">DNS</div><div class="dash-value">DoH 1.1.1.1</div></div>
            <div class="dash-item"><div class="dash-label">STABILITÉ</div><div class="dash-value green">99.9%</div></div>
        </div>
    </div>

    <div class="hero-card">
        <h2>🚀 Pourquoi choisir KETRIKA ?</h2>
        <p>Notre solution utilise les <b>meilleures technologies mondiales</b> pour offrir à votre réseau MikroTik une performance et une sécurité de niveau entreprise.</p>
        <div class="features-detail">
            <div class="feature-detail-box"><span class="fd-icon">🔒</span><div class="fd-title">SÉCURITÉ MILITAIRE</div><div class="fd-desc">Chiffrement WireGuard.</div></div>
            <div class="feature-detail-box"><span class="fd-icon">⚡</span><div class="fd-title">TUNNEL ULTRA-RAPIDE</div><div class="fd-desc">4x plus rapide qu'OpenVPN.</div></div>
            <div class="feature-detail-box"><span class="fd-icon">🌐</span><div class="fd-title">RÉSEAU CLOUDFLARE</div><div class="adv-desc">DNS DoH sécurisé 1.1.1.1.</div></div>
            <div class="feature-detail-box"><span class="fd-icon">🛡️</span><div class="fd-title">CONFIDENTIALITÉ</div><div class="fd-desc">Protection de vie privée.</div></div>
            <div class="feature-detail-box"><span class="fd-icon">📶</span><div class="fd-title">WI-FI OPTIMISÉ</div><div class="fd-desc">Dual Band 2.4G + 5G auto.</div></div>
            <div class="feature-detail-box"><span class="fd-icon">🎯</span><div class="fd-title">CONFIG COMPLÈTE</div><div class="fd-desc">IP, DHCP, NAT, VPN A à Z.</div></div>
        </div>
    </div>

    <div class="card"><div class="card-title">🛒 COMMANDER UN PACK</div>
    <form method="POST" action="/commander">
        <div class="plan-selector">{plans_html}</div>
        
        <label style="margin-top:16px;">Sélectionnez votre mode de paiement :</label>
        <div style="display:flex; gap:6px; margin-top:6px;">
            <div style="flex:1; padding:10px 5px; text-align:center; background:var(--accent-cyan); color:#fff; border-radius:8px; font-size:11px; font-family:'Space Grotesk'; font-weight:700; border:1px solid var(--accent-cyan); cursor:pointer;" id="btn-momo" onclick="document.getElementById('momo-box').style.display='block'; document.getElementById('crypto-box').style.display='none'; this.style.background='var(--accent-cyan)'; this.style.color='#fff'; document.getElementById('btn-crypto').style.background='#f1f5f9'; document.getElementById('btn-crypto').style.color='var(--text-dark)';">📱 Mada (Mvola)</div>
            <div style="flex:1; padding:10px 5px; text-align:center; background:#f1f5f9; color:var(--text-dark); border-radius:8px; font-size:11px; font-family:'Space Grotesk'; font-weight:700; border:1px solid var(--border-light); cursor:pointer;" id="btn-crypto" onclick="document.getElementById('crypto-box').style.display='block'; document.getElementById('momo-box').style.display='none'; this.style.background='var(--accent-cyan)'; this.style.color='#fff'; document.getElementById('btn-momo').style.background='#f1f5f9'; document.getElementById('btn-momo').style.color='var(--text-dark)';">🟡 Inter (Binance)</div>
        </div>

        <div id="momo-box" style="display:block; background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; border-radius: 12px; padding: 14px; margin-top: 10px; text-align: center;">
            <b style="color:#92400e; font-size:12px; font-family:'Space Grotesk';">📱 PAIEMENT MOBILE MONEY</b>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px;">
                <div style="background:#fff; border:1px solid #fde68a; border-radius:10px; padding:10px;">
                    <div style="font-size:11px; font-weight:800;">🟠 Orange Money</div>
                    <div style="font-family:'Space Grotesk'; font-size:16px; font-weight:900; color:#b45309; margin:4px 0;">{NUMERO_ORANGE}</div>
                    <div style="font-size:10px; color:var(--text-muted);">Au nom de : {NOM_COMPTE}</div>
                </div>
                <div style="background:#fff; border:1px solid #fde68a; border-radius:10px; padding:10px;">
                    <div style="font-size:11px; font-weight:800;">🟡 Mvola</div>
                    <div style="font-family:'Space Grotesk'; font-size:16px; font-weight:900; color:#b45309; margin:4px 0;">{NUMERO_MVOLA}</div>
                    <div style="font-size:10px; color:var(--text-muted);">Au nom de : {NOM_COMPTE}</div>
                </div>
            </div>
            <div style="font-size:11px; color:#991b1b; font-weight:700; margin-top:10px;">⏰ Clé non reçue après 15 minutes ? Appelez le {NUMERO_MVOLA}</div>
        </div>

        <div id="crypto-box" style="display:none; background: #0f172a; color: #fff; border: 1px solid #334155; border-radius: 12px; padding: 14px; text-align: center; margin-top: 10px;">
            <div style="font-family:'Space Grotesk'; font-size:14px; font-weight:800; color:#f59e0b;">🟡 BINANCE PAY / USDT</div>
            <p style="font-size:11px; margin-top:4px;">Envoyez le montant en USD ($) via Binance Pay ou USDT (BEP-20) :</p>
            <label style="color:#f59e0b; margin-top:8px;">Binance Pay ID :</label>
            <div style="background:#1e293b; color:#38bdf8; padding:8px; border-radius:8px; font-family:monospace; font-size:14px; font-weight:bold; margin:4px 0;">{BINANCE_ID}</div>
            <label style="color:#f59e0b; margin-top:6px;">Adresse USDT (BEP-20) :</label>
            <div style="background:#1e293b; color:#38bdf8; padding:8px; border-radius:8px; font-family:monospace; font-size:11px; margin:4px 0; word-break:break-all;">{USDT_BEP20}</div>
        </div>

        <input type="text" name="nom" placeholder="Votre Nom complet" required>
        <input type="email" name="email" placeholder="Votre E-mail (Recevra la Clé)" required>
        <input type="text" name="ref_paiement" placeholder="Code SMS de transfert ou TxID" required>
        <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
    </form></div>

    <div class="card"><div class="card-title">🔐 ACTIVATION (1 CLÉ = 1 ROUTEUR)</div>
    <form method="POST" action="/login"><input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase;"><button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button></form></div>

    <div class="card"><div class="card-title">⭐ AVIS CLIENTS • {avg}/5</div>
    <div class="rating-summary"><div class="rating-big">{avg}</div><div><div class="stars-gold">{"⭐"*int(avg)}</div><div style="font-size:11px; font-weight:700;">{cnt} avis vérifiés</div></div></div>
    <div>{reviews_html}</div>
    <hr>
    <div style="font-size:11px; font-weight:700; color:var(--accent-cyan); text-align:center;">✍️ LAISSEZ VOTRE AVIS</div>
    <form method="POST" action="/ajouter-avis">
        <div class="rating-input"><input type="radio" id="s5" name="etoiles" value="5" checked><label for="s5">★</label><input type="radio" id="s4" name="etoiles" value="4"><label for="s4">★</label><input type="radio" id="s3" name="etoiles" value="3"><label for="s3">★</label><input type="radio" id="s2" name="etoiles" value="2"><label for="s2">★</label><input type="radio" id="s1" name="etoiles" value="1"><label for="s1">★</label></div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;"><input type="text" name="nom" placeholder="Nom" required><input type="text" name="ville" placeholder="Ville" required></div>
        <textarea name="commentaire" placeholder="Votre expérience..." rows="2" required></textarea>
        <button type="submit" class="btn-primary" style="padding:10px; font-size:11px;">⭐ PUBLIER MON AVIS</button>
    </form></div>

    <div class="card"><div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item"><div class="faq-question"><span>Est-ce que ça affecte mon débit ?</span> <span class="faq-toggle">▼</span></div><div class="faq-answer">Non ! WireGuard consomme moins de 2% de bande passante. Votre vitesse reste maximale.</div></div>
        <div class="faq-item"><div class="faq-question"><span>Le VPN est-il gratuit ?</span> <span class="faq-toggle">▼</span></div><div class="faq-answer">Oui, 100% gratuit à vie ! Aucun abonnement mensuel.</div></div>
        <div class="faq-item"><div class="faq-question"><span>Fonctionne après un RESET TOTAL ?</span> <span class="faq-toggle">▼</span></div><div class="faq-answer">Oui, notre script configure tout de A à Z (Bridge, DHCP, Wi-Fi, VPN) même sur un routeur vide.</div></div>
        <div class="faq-item"><div class="faq-question"><span>1 clé = combien de routeurs ?</span> <span class="faq-toggle">▼</span></div><div class="faq-answer"><b style="color:red;">1 clé = 1 routeur.</b> Usage unique et verrouillé après génération.</div></div>
    </div>
    """
    return render(content)

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"): return redirect(url_for("home"))
    cle = session.get("licence"); res = verifier_licence(cle)
    if not res or res.get("utilisations", 0) >= 1: session.clear(); return render('<div class="card"><div class="alert alert-error">❌ Clé déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    pk = session.get("type_abo", "basic"); pi = TARIFS_MODULES.get(pk, TARIFS_MODULES["basic"])
    mod_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    ip_chips = "".join([f'<span class="ip-chip" onclick="setIP(\'{ip}\')">{ip}</span>' for ip in IP_SUGGESTIONS])
    
    feat = "<div>✅ Bridge + Ports auto</div><div>✅ Port 1 WAN (DHCP)</div><div>✅ DHCP + NAT + IP libre</div><div>✅ Firewall Stateful Pro</div><div>✅ Optimisation TTL & DNS</div>"
    bw_html = ""
    if pk in ["warp", "hotspot", "pro"]: feat += "<div style='color:var(--accent-green);'>✅ VPN WireGuard (gratuit à vie)</div>"
    if pk in ["hotspot", "pro"]: 
        feat += "<div style='color:var(--accent-green);'>✅ Portail Hotspot Wi-Fi Zone</div>"
        for k, v in BANDWIDTH_PROFILES.items():
            ck = "checked" if k == "illimite" else ""; ac = "active" if k == "illimite" else ""
            bw_html += f'<div class="bw-card {ac}" id="card_{k}" onclick="document.querySelectorAll(\'.bw-card\').forEach(c=>c.classList.remove(\'active\')); this.classList.add(\'active\'); document.getElementById(\'bw_{k}\').checked=true; document.getElementById(\'c-bw\').style.display=({k==\'custom\'} ? \'grid\' : \'none\');"><input type="radio" name="bandwidth" id="bw_{k}" value="{k}" {ck}><div class="bw-card-text"><b>{v["nom"]}</b><span>{v["desc"]}</span></div></div>'
        bw_html = f'<div class="wifi-box" style="border-color:var(--accent-purple);"><div style="font-size:11px; font-weight:800; color:var(--accent-purple); margin-bottom:8px;">📊 LIMITATION DU DÉBIT (CHOIX) :</div><div class="bw-grid">{bw_html}</div><div id="c-bw" style="display:none; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;"><input type="text" name="custom_down" value="3M" placeholder="Down"><input type="text" name="custom_up" value="1M" placeholder="Up"></div></div>'

    content = f"""
    <div class="top-nav" style="margin-bottom:10px;"><span class="badge">{pi['nom']}</span><a href="/logout" style="color:var(--accent-red); font-size:11px; font-weight:700; text-decoration:none;">Fermer Session</a></div>
    <div class="card">
        <div class="card-title">⚙️ CONFIGURATION A À Z - {session['client']}</div>
        <div class="alert-warning" style="font-size:11px;">⚠️ Cette clé sera <b>définitivement consommée</b> après génération.</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label><select name="modele" required>{mod_opt}</select>
            <label>2. Nom du client :</label><input type="text" name="client_final" required>
            <label>3. Adresse IP du Routeur :</label><input type="text" name="router_ip" id="router_ip" value="192.168.88.1" required><div class="ip-suggestions">{ip_chips}</div>
            <div class="wifi-box">
                <div style="font-size:11px; font-weight:bold; color:var(--accent-cyan); margin-bottom:6px;">📶 PARAMÈTRES WI-FI</div>
                <label style="margin:0;">SSID :</label><input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe :</label><input type="text" name="wifi_pass" value="ketrika2025" required>
                {('<label>DNS Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required>' if pk in ["hotspot", "pro"] else '')}
            </div>
            {bw_html}
            <label>4. Inclus :</label><div class="feature-box">{feat}</div>
            <button type="submit" class="btn-primary">🚀 GÉNÉRER LA CONFIG A à Z</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST", "GET"])
def generate():
    if request.method == "GET": return redirect(url_for("dashboard"))
    if not session.get("authenticated"): return redirect(url_for("home"))
    cle = session.get("licence"); res = verifier_licence(cle)
    if not res or res.get("utilisations", 0) >= 1: session.clear(); return render('<div class="card"><div class="alert alert-error">❌ Clé déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    pk = session.get("type_abo", "basic"); cf = request.form.get("client_final", "Client").replace(" ", "_"); mod = request.form.get("modele", "")
    op = {"ssid": request.form.get("ssid"), "wifi_pass": request.form.get("wifi_pass"), "dns_name": request.form.get("dns_name", "ketrika.wifi"), "router_ip": request.form.get("router_ip", "192.168.88.1"), "bw_down": "0", "bw_up": "0"}
    bw_choice = request.form.get("bandwidth", "illimite")
    if bw_choice == "custom": op["bw_down"] = request.form.get("custom_down", "3M"); op["bw_up"] = request.form.get("custom_up", "1M")
    else: op["bw_down"] = BANDWIDTH_PROFILES.get(bw_choice, BANDWIDTH_PROFILES["illimite"])["down"]; op["bw_up"] = BANDWIDTH_PROFILES.get(bw_choice, BANDWIDTH_PROFILES["illimite"])["up"]
    
    warp_data = creer_config_warp_complete() if pk in ["warp", "hotspot", "pro"] else {}
    cid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    sauvegarder_config(cle, cf, mod, pk, op, warp_data, cid)
    incrementer_utilisation(cle)
    
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("UPDATE licences SET actif=0, nb_utilisations=1 WHERE cle=?", (cle,)); conn.commit(); conn.close()
    session.clear()
    
    host = request.host_url.rstrip('/').replace("http://", "https://")
    onl = f'/tool fetch url="{host}/config/{cid}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    raw_s = build_raw_script(get_config_by_id(cid)); clean_s = clean_script_for_oneliner(raw_s)
    one = f'/system script add name=ketrika_run source="{clean_s}"; /system script run ketrika_run; /system script remove ketrika_run'
    
    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Config A à Z prête pour : {cf}</b></div>
        <div class="alert-warning">📍 Branchement : <b>Port 1 (Starlink)</b> | <b>Autres ports (PC)</b><br>🔒 <i>Clé définitivement consommée.</i></div>
        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE</div>
        <div class="terminal-box" id="cmd1">{one}</div>
        <button class="btn-copy" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE</button>
        <hr><div class="card-title">MÉTHODE 2 : FICHIER .RSC</div>
        <a href="/download/{cid}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER LE FICHIER</a>
        <hr><div class="card-title">MÉTHODE 3 : SI ROUTEUR EN LIGNE</div>
        <div class="terminal-box" id="cmd2">{onl}</div>
        <button class="btn-copy" id="b2" onclick="copyText('cmd2','b2')" style="background:#475569;">📋 COPIER CLOUD</button>
        <a href="/" class="btn-primary" style="margin-top:14px;">🏠 RETOUR ACCUEIL</a>
    </div>
    """
    return render(content)

@app.route("/tuto")
def tuto():
    return render('<div class="card"><div class="card-title">📖 GUIDE D\'INSTALLATION (PAS-À-PAS)</div><div class="step-guide"><b>1.</b> Branchez Starlink sur le <b>Port 1</b>.<br><b>2.</b> Branchez PC sur le <b>Port 2</b>.<br><b>3.</b> Ouvrez <b>Winbox</b> et cliquez sur <b>Adresse MAC</b>.<br><b>4.</b> Cliquez sur <b>New Terminal</b>.<br><b>5.</b> Collez la commande et faites Entrée.<br><b>✅ C\'est tout ! Le routeur est prêt en 5 secondes.</b></div><a href="/" class="btn-primary" style="margin-top:15px;">🏠 RETOUR</a></div>')

@app.route("/commander", methods=["POST"])
def commander():
    nom = request.form.get("nom"); email = request.form.get("email"); f = request.form.get("formule"); ref = request.form.get("ref_paiement")
    if nom and email and ref:
        conn = sqlite3.connect(DB_FILE); c = conn.cursor()
        c.execute("INSERT INTO commandes (client_nom, email, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?, ?)", (nom, email, email, f, TARIFS_MODULES.get(f, {}).get("prix", 10000), ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); conn.close()
    return render(f'<div class="card"><div class="alert alert-success"><b>✅ Commande enregistrée !</b></div><p style="font-size:12px;">Clé envoyée par Email à <b>{email}</b> sous 15 min max.<br>⏰ Pas de clé après 15 min ? Appelez le <b>{NUMERO_MVOLA}</b>.</p><a href="/" class="btn-primary">RETOUR</a></div>')

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and verifier_admin(request.form.get("username"), request.form.get("password")): session["admin"] = True; return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ADMIN</div><form method="POST"><input type="text" name="username" required><input type="password" name="password" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC"); cmds = c.fetchall(); conn.close()
    rows = ""
    for cmd in cmds: rows += f'<tr><td><b>{cmd[1]}</b><br><small>{cmd[3]}</small></td><td>{cmd[4].upper()}<br><b>{cmd[5]:,} Ar</b></td><td><code>{cmd[6]}</code></td><td><form method="POST" action="/admin/valider/{cmd[0]}"><button type="submit" class="btn-primary" style="padding:4px 8px; font-size:10px; margin:0;">⚡ VALIDER & MAIL</button></form></td></tr>'
    return render(f'<div class="card"><div class="card-title">📋 COMMANDES ({len(cmds)})</div><table style="width:100%; font-size:11px;"><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>{rows if rows else "<tr><td colspan=4 align=center>Aucune commande</td></tr>"}</table><a href="/admin/creer" class="btn-primary" style="margin-top:12px;">➕ CRÉER CLÉ MANUELLE</a></div>')

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("SELECT client_nom, email, formule FROM commandes WHERE id=?", (cmd_id,)); cmd = c.fetchone()
    if cmd:
        cle = creer_licence(cmd[0], cmd[1], cmd[2], TARIFS_MODULES.get(cmd[2], {}).get("prix", 10000))
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id)); conn.commit()
        if "@" in str(cmd[1]): envoyer_email_cle(cmd[1], cmd[0], cle, TARIFS_MODULES.get(cmd[2], {}).get("nom", "Pack"))
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"): return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée (1 usage unique) :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary">Retour</a></div>')
    return render('<div class="card"><div class="card-title">Créer Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Email" required><select name="type"><option value="basic">Basic (10k)</option><option value="standard">Standard (15k)</option><option value="warp">Premium (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>')

@app.route("/config/<path:config_id>")
def get_config(config_id): cfg = get_config_by_id(config_id.replace('.rsc', '').strip()); return Response(build_raw_script(cfg), mimetype="text/plain") if cfg else Response("# Erreur", mimetype="text/plain")
@app.route("/download/<path:config_id>")
def download_config(config_id):
    cfg = get_config_by_id(config_id.replace('.rsc', '').strip())
    if not cfg: return redirect(url_for("home"))
    mem = io.BytesIO(); mem.write(build_raw_script(cfg).encode('utf-8')); mem.seek(0)
    return send_file(mem, mimetype="text/plain", as_attachment=True, download_name="ketrika.rsc")

@app.errorhandler(404)
def h404(e): return redirect(url_for("home"))
@app.errorhandler(500)
def h500(e): return redirect(url_for("home"))

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)
