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

# ==========================================
# CONFIGURATIONS OFFICIELLES
# ==========================================
FB_LINK = "https://www.facebook.com/loza.nama.376"
NUMERO_MVOLA = "038 28 171 00"
NUMERO_ORANGE = "037 39 755 72"
NOM_COMPTE = "Jean Eric"
BINANCE_ID = "1229612637"
USDT_BEP20 = "0x0c4bcb1beabbff154f7d445a549f1e5b42de9088"

# ==========================================
# CONFIGURATION EMAIL (À REMPLIR)
# ==========================================
SMTP_EMAIL = "votre.email@gmail.com"  # Mettez votre adresse Gmail ici
SMTP_PASSWORD = "votre_mot_de_passe_application"  # Mettez votre "Mot de passe d'application" Google ici

def envoyer_email_cle(destinataire, nom, cle, pack_nom):
    if not destinataire or "@" not in destinataire or SMTP_EMAIL == "votre.email@gmail.com":
        return False
    try:
        sujet = "✅ Votre Clé d'Activation KETRIKA MIKROTIK"
        message_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #0284c7, #059669); color: white; padding: 20px; text-align: center;">
                    <h2 style="margin: 0;">⚡ KETRIKA MIKROTIK ⚡</h2>
                </div>
                <div style="padding: 20px;">
                    <p>Bonjour <b>{nom}</b>,</p>
                    <p>Merci pour votre confiance. Votre commande pour le pack <b>{pack_nom}</b> a été validée avec succès !</p>
                    <p>Voici votre clé d'activation à usage unique (1 Clé = 1 Routeur) :</p>
                    <div style="background: #f1f5f9; border-left: 4px solid #0284c7; padding: 15px; font-size: 18px; font-weight: bold; text-align: center; letter-spacing: 2px;">
                        {cle}
                    </div>
                    <br>
                    <p><b>Comment l'utiliser ?</b></p>
                    <ol>
                        <li>Allez sur le site : <a href="https://ketrika-mikrotik.onrender.com" style="color: #0284c7;">ketrika-mikrotik.onrender.com</a></li>
                        <li>Entrez cette clé dans la section "Activation".</li>
                        <li>Générez votre script et collez-le dans Winbox !</li>
                    </ol>
                    <p>Si vous avez besoin d'aide, n'hésitez pas à nous contacter sur <a href="https://wa.me/261382817100" style="color: #059669;">WhatsApp (038 28 171 00)</a>.</p>
                </div>
                <div style="background: #f8fafc; text-align: center; padding: 10px; font-size: 11px; color: #64748b;">
                    © 2026 KETRIKA MIKROTIK PRO - Madagascar
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

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
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
        
        # Mise a jour automatique de la table commandes pour ajouter la colonne email
        c.execute('''CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY AUTOINCREMENT, client_nom TEXT, telephone TEXT, email TEXT, formule TEXT, montant REAL, reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE', cle_generee TEXT, date_commande TEXT)''')
        try: c.execute("ALTER TABLE commandes ADD COLUMN email TEXT") 
        except: pass

        c.execute('''CREATE TABLE IF NOT EXISTS avis (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, ville TEXT, etoiles INTEGER NOT NULL, commentaire TEXT NOT NULL, date_avis TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT)''')
        import hashlib
        c.execute("INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)", ("admin", hashlib.sha256("ketrika2025".encode()).hexdigest()))

        c.execute("SELECT COUNT(*) FROM avis")
        if c.fetchone()[0] < 3:
            c.executemany("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", [
                ("Mamy R.", "Antananarivo", 5, "Script injecté après reset total sur mon hAP ax2. Configuration parfaite du premier coup !", "2026-01-15"),
                ("Jean Luc", "Tamatave", 5, "Configuration propre sur hAP ac2. Wi-Fi et pare-feu impeccables.", "2026-01-20"),
                ("Boutique Alpha", "Majunga", 5, "Pack Wi-Fi Zone parfait avec gestion de débit pour mon business.", "2026-01-28"),
                ("David M.", "La Réunion", 5, "Paiement USDT par Binance Pay instantané. Clé reçue par mail en 5 min. Excellent !", "2026-02-01"),
                ("Toky N.", "Diego Suarez", 5, "Très satisfait de l'optimisation réseau et de la réactivité WhatsApp.", "2026-02-02")
            ])
        conn.commit()
        conn.close()
    except Exception as e: print(f"Erreur init DB: {e}")

init_all_tables()

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "prix_usd": 2.50, "desc": "Config A à Z + IP Libre + Optimisation + Wi-Fi", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "prix_usd": 3.75, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Premium VPN", "prix": 20000, "prix_usd": 5.00, "desc": "Standard + Tunnel WireGuard confidentiel gratuit", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "prix_usd": 7.50, "desc": "Premium + Portail Hotspot + Débit contrôlé + DNS", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "prix_usd": 12.50, "desc": "Solution intégrale + Multi-WAN + PPPoE + QoS", "badge": "PRO STUDIO"}
}

MODELES_MIKROTIK = ["hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)", "hAP ac2 (Dual Band Wireless)", "hAP ac3 (Dual Band Wireless)", "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (Wireless)", "LHG 5", "SXTsq", "hAP lite (Wireless 2.4G)", "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)", "CCR1009", "CCR2004", "CCR2116", "Chateau LTE/5G", "Autre RouterOS v7"]

BANDWIDTH_PROFILES = {"illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Plein débit sans restriction"},"ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10 Mbps ↓ / 5 Mbps ↑"},"rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5 Mbps ↓ / 2 Mbps ↑"},"standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2 Mbps ↓ / 1 Mbps ↑"},"eco": {"nom": "🔒 ÉCO (1M/512K)", "down": "1M", "up": "512k", "desc": "1 Mbps ↓ / 512 Kbps ↑"},"custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Entrez vos limites"}}

IP_SUGGESTIONS = ["192.168.88.1", "192.168.1.1", "192.168.0.1", "192.168.10.1", "192.168.100.1", "10.0.0.1", "10.0.1.1", "10.10.10.1", "172.16.0.1", "172.16.1.1", "172.20.0.1"]

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="google-site-verification" content="a8G-WaLOM4cff6QkaeNJSjm6eavmu0DPif8RBdUnjLI" />
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
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), #db2777, var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 14px; color: var(--accent-cyan); margin-bottom: 12px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }
        .hero-card { background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%); color: #fff; padding: 20px 16px; border-radius: 18px; margin-bottom: 14px; box-shadow: 0 10px 30px rgba(2,132,199,0.25); }
        .hero-card h2 { font-family: 'Space Grotesk'; font-size: 19px; font-weight: 900; margin-bottom: 6px; }
        .hero-card > p { font-size: 12px; opacity: 0.95; margin-bottom: 12px; line-height: 1.5; }
        .features-detail { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 12px; }
        @media (min-width: 500px) { .features-detail { grid-template-columns: repeat(2, 1fr); } }
        @media (min-width: 800px) { .features-detail { grid-template-columns: repeat(3, 1fr); gap: 10px; } }
        .feature-detail-box { background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2); }
        .feature-detail-box .fd-icon { font-size: 22px; display: block; margin-bottom: 4px; }
        .feature-detail-box .fd-title { font-family: 'Space Grotesk'; font-size: 12px; font-weight: 800; margin-bottom: 3px; }
        .feature-detail-box .fd-desc { font-size: 11px; opacity: 0.9; line-height: 1.4; }
        .advantages-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        @media (min-width: 500px) { .advantages-grid { grid-template-columns: repeat(4, 1fr); gap: 10px; } }
        .adv-box { background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 12px 6px; border-radius: 10px; text-align: center; border: 1px solid var(--border-light); }
        .adv-icon { font-size: 22px; display: block; margin-bottom: 3px; }
        .adv-title { font-family: 'Space Grotesk'; font-size: 11px; color: var(--text-dark); font-weight: 800; }
        .adv-desc { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
        .steps-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .steps-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; } }
        .step-box { background: linear-gradient(135deg, #f0fdfa, #eff6ff); border: 1px solid #bae6fd; padding: 12px 10px; border-radius: 12px; text-align: center; }
        .step-num { width: 30px; height: 30px; margin: 0 auto 6px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Space Grotesk'; font-weight: 900; font-size: 15px; }
        .step-title { font-family: 'Space Grotesk'; font-size: 12px; color: var(--text-dark); font-weight: 800; margin-bottom: 2px; }
        .step-desc { font-size: 10px; color: var(--text-muted); line-height: 1.4; }
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input[type="text"], input[type="tel"], input[type="password"], input[type="email"], select, textarea { width: 100%; padding: 12px 14px; margin-top: 4px; background: #f8fafc; border: 1px solid var(--border-light); border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit; }
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
        .payment-banner { background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; border-radius: 12px; padding: 14px; margin-top: 12px; text-align: center; }
        .payment-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .payment-grid { grid-template-columns: 1fr 1fr; } }
        .payment-box { background: #fff; border: 1px solid #fde68a; border-radius: 10px; padding: 10px; }
        .payment-box .method { font-size: 11px; font-weight: 800; }
        .payment-box .number { font-family: 'Space Grotesk'; font-size: 17px; font-weight: 900; color: #b45309; margin: 3px 0; }
        .payment-box .name { font-size: 10px; color: var(--text-muted); }
        .terminal-box { background: #0f172a; border: 1px solid #334155; color: #4ade80; padding: 12px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 6px; line-height: 1.5; }
        .alert { padding: 10px 12px; border-radius: 10px; margin-bottom: 10px; font-size: 12px; }
        .alert-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
        .alert-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
        .whatsapp-float { position: fixed; bottom: 18px; right: 18px; z-index: 9999; background: #25D366; color: #fff; padding: 10px 16px; border-radius: 30px; font-weight: 800; font-size: 12px; text-decoration: none; display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk'; box-shadow: 0 4px 15px rgba(37,211,102,0.4); }
        .footer { text-align: center; color: var(--text-muted); margin: 20px 0 70px; font-size: 10px; padding: 10px; border-top: 1px solid var(--border-light); }
        .footer a { color: var(--accent-cyan); text-decoration: none; font-weight: 700; }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">💬 <span>WhatsApp</span></a>

    <div class="container">
        <div class="top-nav">
            <a href="/" class="nav-brand">
                <div class="nav-logo-icon">⚡</div><span>KETRIKA MIKROTIK</span>
            </a>
            <div class="top-links">
                <a href="/tuto" class="btn-tuto">📖 Guide &amp; Tuto</a>
                <a href="{{ fb_link }}" target="_blank" class="btn-fb">📘 Facebook</a>
            </div>
        </div>

        <div class="header">
            <div class="logo-wrapper">
                <div class="logo-aura"></div>
                <div class="logo-box">
                    <svg viewBox="0 0 24 24" fill="none" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00f2fe" /><stop offset="100%" stop-color="#7c3aed" /></linearGradient></defs>
                        <rect x="2" y="14" width="20" height="8" rx="2" fill="rgba(0,242,254,0.1)"></rect>
                        <path d="M6 18h.01"></path><path d="M10 18h.01"></path><path d="M14 18h.01"></path><path d="M18 18h.01"></path>
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#00f2fe" stroke="#00f2fe" stroke-width="1.5"></path>
                    </svg>
                </div>
            </div>
            <h1>KETRIKA MIKROTIK</h1>
            <p class="tagline txt-fr">Solution Professionnelle d'Optimisation Réseau MikroTik</p>
            <div class="stats-live"><span class="live-dot"></span><span>Config en 5 secondes • 1 Clé = 1 Routeur • Support 7j/7</span></div>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • <a href="{{ fb_link }}" target="_blank">📘 Facebook Officiel</a> • 📞 038 28 171 00 (Jean Eric)
        </div>
    </div>

    <script>
        function copyText(elemId, btnId) { 
            const el = document.getElementById(elemId);
            const text = el.innerText || el.value; 
            navigator.clipboard.writeText(text).then(() => { 
                const btn = document.getElementById(btnId); 
                const o = btn.innerHTML; 
                btn.innerHTML = '✅ COPIÉ DANS LE PRESSE-PAPIER !'; 
                btn.classList.add('copied'); 
                setTimeout(() => { btn.innerHTML = o; btn.classList.remove('copied'); }, 2500); 
            }); 
        }
        function setIP(ip) { document.getElementById('router_ip').value = ip; }
        
        function selectPayTab(tabName) {
            document.querySelectorAll('.pay-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.pay-tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById('tab_btn_' + tabName).classList.add('active');
            document.getElementById('tab_content_' + tabName).classList.add('active');
        }
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content, fb_link=FB_LINK)

def build_raw_script(cfg):
    plan = cfg["type"]
    modele = cfg.get("modele", "")
    opt = cfg.get("options", {})
    ssid = opt.get("ssid", "KETRIKA-NET")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0")
    bw_up = opt.get("bw_up", "0")
    router_ip = opt.get("router_ip", "192.168.88.1").strip()
    
    ip_parts = router_ip.split('.')
    if len(ip_parts) == 4:
        subnet_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        dhcp_pool_start = f"{subnet_base}.10"
        dhcp_pool_end = f"{subnet_base}.250"
        dhcp_net = f"{subnet_base}.0/24"
    else:
        router_ip = "192.168.88.1"
        dhcp_pool_start = "192.168.88.10"
        dhcp_pool_end = "192.168.88.250"
        dhcp_net = "192.168.88.0/24"

    is_wifi6 = any(k in modele for k in ["ax2", "ax3", "ax 15s", "Wi-Fi 6"])
    is_wireless = any(k in modele for k in ["ac2", "ac3", "lite", "19s", "LHG", "SXT", "Wireless"])

    s = f"""# =========================================================================
# KETRIKA MIKROTIK - ARCHITECTURE INDUSTRIELLE DE A A Z
# Modele : {modele} | Formule : {plan.upper()} | Client : {cfg['client']}
# IP Locale : {router_ip} ({dhcp_net})
# =========================================================================

# --- 1. BRIDGE & LISTES D'INTERFACES ---
:if ([:len [/interface bridge find name=bridge-lan]] = 0) do={{ /interface bridge add name=bridge-lan auto-mac=yes comment="defconf-LAN" }}
:if ([:len [/interface list find name=WAN]] = 0) do={{ /interface list add name=WAN }}
:if ([:len [/interface list find name=LAN]] = 0) do={{ /interface list add name=LAN }}
/interface list member remove [find interface=ether1]
/interface list member add interface=ether1 list=WAN
/interface list member remove [find interface=bridge-lan]
/interface list member add interface=bridge-lan list=LAN

:foreach i in=[/interface ethernet find where name!="ether1"] do={{
    :if ([:len [/interface bridge port find interface=$i]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$i comment="LAN-PORT" }}
}}

# --- 2. WAN (PORT 1 VIA DHCP-CLIENT DYNAMIQUE) ---
/ip dhcp-client remove [find interface=ether1]
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no use-peer-ntp=yes add-default-route=yes default-route-distance=1 comment="WAN-MAIN"

# --- 3. ADRESSAGE IP ET SERVEUR DHCP LOCAL ---
/ip address remove [find interface=bridge-lan]
/ip address add address={router_ip}/24 interface=bridge-lan comment="LAN-IP"
/ip pool remove [find name=dhcp-pool]
/ip pool add name=dhcp-pool ranges={dhcp_pool_start}-{dhcp_pool_end}
/ip dhcp-server remove [find interface=bridge-lan]
/ip dhcp-server add name=dhcp-lan interface=bridge-lan address-pool=dhcp-pool disabled=no lease-time=12h
/ip dhcp-server network remove [find address={dhcp_net}]
/ip dhcp-server network add address={dhcp_net} gateway={router_ip} dns-server=1.1.1.1,1.0.0.1 comment="LAN-NET"

# --- 4. ACCES INTERNET (NAT PRINCIPAL) ---
/ip firewall nat remove [find comment="NAT-INTERNET"]
/ip firewall nat add chain=srcnat out-interface-list=WAN action=masquerade comment="NAT-INTERNET"

# --- 5. OPTIMISATION RESEAU (MANGLE TTL = 64) ---
/ip firewall mangle remove [find comment="STARLINK-TTL-64"]
/ip firewall mangle add chain=postrouting out-interface-list=WAN action=change-ttl new-ttl=set:64 passthrough=yes comment="STARLINK-TTL-64"

# --- 6. DNS SECURISE DOH (CLOUDFLARE 1.1.1.1) ---
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no
/ip firewall nat remove [find comment="DNS-REDIRECT-UDP"]
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=udp dst-port=53 action=redirect to-ports=53 comment="DNS-REDIRECT-UDP"
/ip firewall nat remove [find comment="DNS-REDIRECT-TCP"]
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=tcp dst-port=53 action=redirect to-ports=53 comment="DNS-REDIRECT-TCP"

# --- 7. PARE-FEU D'ENTREPRISE (STATEFUL FIREWALL) ---
/ip firewall filter remove [find comment~"KETRIKA"]
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked comment="KETRIKA-ESTABLISHED"
/ip firewall filter add chain=input action=drop connection-state=invalid comment="KETRIKA-INVALID"
/ip firewall filter add chain=input action=accept protocol=icmp comment="KETRIKA-PING"
/ip firewall filter add chain=input in-interface-list=LAN action=accept comment="KETRIKA-LAN-IN"
/ip firewall filter add chain=input in-interface-list=WAN action=drop comment="KETRIKA-WAN-DROP"

/ip firewall filter add chain=forward action=accept connection-state=established,related,untracked comment="KETRIKA-FWD-EST"
/ip firewall filter add chain=forward action=drop connection-state=invalid comment="KETRIKA-FWD-INV"
/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=150,32 action=drop comment="KETRIKA-P2P-LIMIT"
/ip firewall filter add chain=forward in-interface-list=WAN connection-nat-state=!dstnat connection-state=new action=drop comment="KETRIKA-WAN-FWD-DROP"

/ipv6 settings set disable-ipv6=yes
/ip service disable telnet,ftp,api
"""

    if is_wifi6:
        s += f"""
# --- 8. WI-FI 6 DEDIE (ROUTEROS V7 WIFI WAVE2) ---
:do {{
    /interface wifi security remove [find name=sec-wifi]
    /interface wifi security add name=sec-wifi authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}"
    /interface wifi configuration remove [find name=cfg-wifi]
    /interface wifi configuration add name=cfg-wifi ssid="{ssid}" security=sec-wifi country="Madagascar"
    /interface wifi set [find] configuration=cfg-wifi disabled=no
    :foreach w in=[/interface wifi find] do={{ :if ([:len [/interface bridge port find interface=$w]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$w }} }}
}} on-error={{}};
"""
    elif is_wireless:
        s += f"""
# --- 8. WI-FI CLASSIQUE DEDIE (ROUTEROS WIRELESS N/AC) ---
:do {{
    /interface wireless security-profiles remove [find name=sec-wifi]
    /interface wireless security-profiles add name=sec-wifi mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}" unicast-ciphers=aes-ccm group-ciphers=aes-ccm
    /interface wireless set [find] ssid="{ssid}" security-profile=sec-wifi country="madagascar" disabled=no
    :foreach w in=[/interface wireless find] do={{ :if ([:len [/interface bridge port find interface=$w]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$w }} }}
}} on-error={{}};
"""

    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f"""
# --- 9. TUNNEL WIREGUARD VPN AVEC ROUTAGE PBR SÉCURISÉ ---
:if ([:len [/routing table find name=to-warp]] = 0) do={{ /routing table add name=to-warp fib }}
/ip firewall address-list remove [find list=CONNECTED-NETS]
/ip firewall address-list add list=CONNECTED-NETS address={dhcp_net}
/ip firewall address-list add list=CONNECTED-NETS address=172.16.0.0/12
/ip firewall address-list add list=CONNECTED-NETS address=10.0.0.0/8
/ip firewall address-list add list=CONNECTED-NETS address=192.168.0.0/16

/interface wireguard remove [find name=warp-vpn]
/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers remove [find interface=warp-vpn]
/interface wireguard peers add interface=warp-vpn public-key="{cfg['warp_public']}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address remove [find interface=warp-vpn]
/ip address add address={cfg['warp_ip']}/32 interface=warp-vpn
/interface list member remove [find interface=warp-vpn]
/interface list member add interface=warp-vpn list=WAN
/ip firewall nat remove [find comment="WARP-NAT"]
/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade comment="WARP-NAT"

/ip route remove [find comment="WARP-ENDPOINT-ROUTE"]
/ip route add dst-address=162.159.192.0/24 gateway=ether1 distance=1 comment="WARP-ENDPOINT-ROUTE"
/ip route remove [find comment="VPN-PBR-ROUTE"]
/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn routing-table=to-warp comment="VPN-PBR-ROUTE"

/ip firewall mangle remove [find comment="MARK-ROUTING-WARP"]
/ip firewall mangle add chain=prerouting in-interface-list=LAN dst-address-list=!CONNECTED-NETS dst-address-type=!local action=mark-routing new-routing-mark=to-warp passthrough=yes comment="MARK-ROUTING-WARP"
"""

    if plan in ["hotspot", "pro"]:
        s += f"""
# --- 10. SERVEUR HOTSPOT WI-FI ZONE SUR LE RESEAU LOCAL ---
/ip hotspot profile remove [find name=hs-prof]
/ip hotspot profile add name=hs-prof hotspot-address={router_ip} dns-name={dns_name}
/ip hotspot user profile remove [find name=hs-user]
/ip hotspot user profile add name=hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot remove [find name=hotspot-ketrika]
/ip hotspot add name=hotspot-ketrika interface=bridge-lan address-pool=dhcp-pool profile=hs-prof disabled=no
"""

    if plan == "pro":
        s += f"""
# --- 11. SERVEUR PPPOE & GESTION DE BANDE PASSANTE ---
/ip pool remove [find name=pppoe-pool]
/ip pool add name=pppoe-pool ranges=10.10.10.2-10.10.10.254
/ppp profile remove [find name=prof-pppoe]
/ppp profile add name=prof-pppoe local-address=10.10.10.1 remote-address=pppoe-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"
/interface pppoe-server server remove [find service-name=PPPOE-KETRIKA]
/interface pppoe-server server add service-name=PPPOE-KETRIKA interface=bridge-lan default-profile=prof-pppoe disabled=no
"""

    s += f"""
# --- 12. IDENTITE DU ROUTEUR ---
/system identity set name="KETRIKA-{cfg['client']}"
:put "==========================================================="
:put "  KETRIKA MIKROTIK : INSTALLATION PRO DE A A Z TERMINEE !  "
:put "  IP ROUTEUR : {router_ip} | PORTS LAN & WIFI ACTIFS      "
:put "==========================================================="
"""
    return s

def clean_script_for_oneliner(raw_script):
    lines = []
    for line in raw_script.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        lines.append(line)
    return " ".join(lines).replace('"', '\\"')

@app.route("/", methods=["GET", "POST"])
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT AVG(etoiles), COUNT(*) FROM avis")
    avg_stat, total_avis = c.fetchone()
    avg_note = round(avg_stat, 1) if avg_stat else 5.0
    c.execute("SELECT nom, ville, etoiles, commentaire, date_avis FROM avis ORDER BY id DESC LIMIT 5")
    liste_avis = c.fetchall()
    conn.close()
    
    reviews_html = ""
    for a in liste_avis:
        reviews_html += f'<div class="review-card"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><b style="font-size:12px;">{a[0]} <span style="color:var(--text-muted); font-size:10px;">({a[1] or "MG"})</span></b><span style="color:var(--accent-gold); font-size:12px; letter-spacing:2px;">{"⭐" * a[2]}</span></div><div style="font-size:12px; color:var(--text-body);">"{a[3]}"</div></div>'
    
    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "standard" else ""
        selected_class = "selected" if k == "standard" else ""
        badge_html = ""
        if v.get("badge"):
            bc = "badge-popular" if v["badge"] == "POPULAIRE" else ("badge-best" if v["badge"] == "MEILLEUR CHOIX" else "badge-pro")
            badge_html = f'<div class="plan-badge {bc}">{v["badge"]}</div>'
        plans_html += f"""
        <label class="plan-option {selected_class}" id="opt_{k}" for="plan_{k}">
            {badge_html}
            <div class="plan-info">
                <b>{v["nom"]}</b>
                <div>{v["desc"]}</div>
            </div>
            <div class="plan-price">
                <b>{v["prix"]:,} Ar</b>
                <small style="color:var(--accent-cyan); font-weight:700; font-size:10px;">${v["prix_usd"]:.2f} USD</small>
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked} onchange="document.querySelectorAll('.plan-option').forEach(e=>e.classList.remove('selected')); document.getElementById('opt_{k}').classList.add('selected');">
            </div>
        </label>
        """
    
    content = f"""
    <!-- HERO CONVAINCANT -->
    <div class="hero-card">
        <h2>🚀 Pourquoi choisir KETRIKA ?</h2>
        <p>Notre solution utilise les <b>meilleures technologies mondiales</b> pour offrir à votre réseau MikroTik une performance et une sécurité de niveau entreprise.</p>
        <div class="features-detail">
            <div class="feature-detail-box">
                <span class="fd-icon">🔒</span>
                <div class="fd-title">SÉCURITÉ MILITAIRE</div>
                <div class="fd-desc">Chiffrement <b>ChaCha20-Poly1305</b> (WireGuard), utilisé par les banques et gouvernements.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">⚡</span>
                <div class="fd-title">TUNNEL ULTRA-RAPIDE</div>
                <div class="fd-desc">WireGuard est <b>4x plus rapide qu'OpenVPN</b>. Latence &lt; 2ms. Débit maximal en toutes circonstances.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🌐</span>
                <div class="fd-title">RÉSEAU CLOUDFLARE</div>
                <div class="fd-desc">Serveurs dans <b>300+ villes mondiales</b>. DNS DoH sécurisé 1.1.1.1 : navigation privée garantie.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🛡️</span>
                <div class="fd-title">CONFIDENTIALITÉ</div>
                <div class="fd-desc">Routage intelligent, filtrage du trafic P2P, gestion optimale des connexions et de la vie privée.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">📶</span>
                <div class="fd-title">WI-FI OPTIMISÉ</div>
                <div class="fd-desc">Configuration Dual Band <b>2.4G + 5G</b> automatique. Wi-Fi 6 supporté pour vitesses maximales.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🎯</span>
                <div class="fd-title">CONFIG COMPLÈTE</div>
                <div class="fd-desc">IP, DHCP, NAT, Firewall Pro, Wi-Fi, VPN : <b>tout configuré automatiquement</b>. Même après reset total.</div>
            </div>
        </div>
    </div>

    <!-- COMMANDER -->
    <div class="card">
        <div class="card-title">🛒 CHOISIR VOTRE FORMULE & PAIEMENT</div>
        <div class="alert-warning" style="font-size:12px;">⚠️ <b>1 Clé = 1 Routeur uniquement.</b> Chaque clé configure intégralement un seul boîtier MikroTik.</div>
        
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            
            <label style="margin-top:16px;">SÉLECTIONNEZ VOTRE MODE DE PAIEMENT :</label>
            <div style="display:flex; gap:6px; margin-top:6px;">
                <div style="flex:1; padding:10px 5px; text-align:center; background:var(--accent-cyan); color:#fff; border-radius:8px; font-size:11px; font-family:'Space Grotesk'; font-weight:700; border:1px solid var(--accent-cyan); cursor:pointer;" id="btn-momo" onclick="document.getElementById('momo-box').style.display='block'; document.getElementById('crypto-box').style.display='none'; document.getElementById('card-box').style.display='none'; this.style.background='var(--accent-cyan)'; this.style.color='#fff'; document.getElementById('btn-crypto').style.background='#f1f5f9'; document.getElementById('btn-crypto').style.color='var(--text-dark)'; document.getElementById('btn-card').style.background='#f1f5f9'; document.getElementById('btn-card').style.color='var(--text-dark)';">📱 Mobile Money</div>
                <div style="flex:1; padding:10px 5px; text-align:center; background:#f1f5f9; color:var(--text-dark); border-radius:8px; font-size:11px; font-family:'Space Grotesk'; font-weight:700; border:1px solid var(--border-light); cursor:pointer;" id="btn-crypto" onclick="document.getElementById('crypto-box').style.display='block'; document.getElementById('momo-box').style.display='none'; document.getElementById('card-box').style.display='none'; this.style.background='var(--accent-cyan)'; this.style.color='#fff'; document.getElementById('btn-momo').style.background='#f1f5f9'; document.getElementById('btn-momo').style.color='var(--text-dark)'; document.getElementById('btn-card').style.background='#f1f5f9'; document.getElementById('btn-card').style.color='var(--text-dark)';">🟡 Binance / USDT</div>
                <div style="flex:1; padding:10px 5px; text-align:center; background:#f1f5f9; color:var(--text-dark); border-radius:8px; font-size:11px; font-family:'Space Grotesk'; font-weight:700; border:1px solid var(--border-light); cursor:pointer;" id="btn-card" onclick="document.getElementById('card-box').style.display='block'; document.getElementById('momo-box').style.display='none'; document.getElementById('crypto-box').style.display='none'; this.style.background='var(--accent-cyan)'; this.style.color='#fff'; document.getElementById('btn-momo').style.background='#f1f5f9'; document.getElementById('btn-momo').style.color='var(--text-dark)'; document.getElementById('btn-crypto').style.background='#f1f5f9'; document.getElementById('btn-crypto').style.color='var(--text-dark)';">💳 Carte Bancaire</div>
            </div>

            <!-- MOMO BOX -->
            <div id="momo-box" style="display:block; background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; border-radius: 12px; padding: 14px; margin-top: 10px; text-align: center;">
                <b style="color:#92400e; font-size:12px; font-family:'Space Grotesk';">📱 PAIEMENT MADAGASCAR</b>
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
            </div>

            <!-- CRYPTO BOX -->
            <div id="crypto-box" style="display:none; background: #0f172a; color: #fff; border: 1px solid #334155; border-radius: 12px; padding: 14px; text-align: center; margin-top: 10px;">
                <div style="font-family:'Space Grotesk'; font-size:14px; font-weight:800; color:#f59e0b;">🟡 PAIEMENT INTERNATIONAL BINANCE / USDT</div>
                <p style="font-size:11px; margin-top:4px;">Envoyez le montant exact en USD ($) via Binance Pay ou USDT (BEP-20) :</p>
                <label style="color:#f59e0b; margin-top:8px;">Binance Pay ID :</label>
                <div style="background:#1e293b; color:#38bdf8; padding:8px; border-radius:8px; font-family:monospace; font-size:14px; font-weight:bold; margin:4px 0;">{BINANCE_ID}</div>
                <label style="color:#f59e0b; margin-top:6px;">Adresse USDT (Réseau BEP-20 BSC) :</label>
                <div style="background:#1e293b; color:#38bdf8; padding:8px; border-radius:8px; font-family:monospace; font-size:11px; margin:4px 0; word-break:break-all;">{USDT_BEP20}</div>
            </div>

            <!-- CARD BOX -->
            <div id="card-box" style="display:none; background: #f0f9ff; border: 1px dashed #0ea5e9; border-radius: 12px; padding: 14px; text-align: center; margin-top: 10px;">
                <div style="font-family:'Space Grotesk'; font-size:14px; font-weight:800; color:#0369a1;">💳 PAIEMENT PAR CARTE BANCAIRE</div>
                <p style="font-size:11px; margin-top:6px; line-height:1.5;">Pour payer par carte Visa ou Mastercard (Via Stripe), veuillez nous contacter directement sur WhatsApp pour recevoir votre lien de paiement sécurisé en USD.</p>
            </div>

            <div style="background:linear-gradient(135deg, #fef2f2, #fee2e2); border:1px solid #fecaca; border-radius:8px; padding:8px; margin-top:10px; font-size:11px; color:#991b1b; font-weight:700; text-align:center;">
                ⏰ Clé non reçue après 15 minutes ? Appelez : <b>{NUMERO_MVOLA}</b> ou WhatsApp.
            </div>

            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Ex: Rakoto Jean" required>
            <label>Téléphone (Pour recevoir la clé SMS) :</label>
            <input type="text" name="tel" placeholder="034 00 000 00 / Ou Adresse Email" required>
            <label>Référence de transaction (Preuve de paiement) :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transfert, ou TxID Binance" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE & RECEVOIR MA CLÉ</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">🔐 ACTIVATION (1 Clé = 1 Routeur)</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/commander", methods=["POST"])
def commander():
    nom = request.form.get("nom")
    tel = request.form.get("tel")
    formule = request.form.get("formule")
    ref = request.form.get("ref_paiement")
    montant = TARIFS_MODULES.get(formule, {}).get("prix", 10000)
    usd = TARIFS_MODULES.get(formule, {}).get("prix_usd", 2.5)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)", (nom, tel, formule, montant, ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    # Envoi de l'email si renseigné
    if "@" in tel:
        envoyer_email_cle(tel, nom, "VOTRE CLÉ SERA ENVOYÉE DÈS VALIDATION DE VOTRE PAIEMENT", TARIFS_MODULES[formule]["nom"])
    
    content = f"""
    <div class="card">
        <div style="background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; padding:12px 15px; border-radius:10px; font-size:13px; margin-bottom:12px;"><b>✅ Commande enregistrée avec succès !</b></div>
        <p style="font-size:13px; line-height:1.6; color:var(--text-body);">
            Merci <b>{nom}</b>.<br>Votre demande pour le pack <b>{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar / ${usd:.2f} USD) a bien été transmise.<br><br>
            Notre équipe va vérifier immédiatement la référence de transaction <code style="color:var(--accent-cyan); font-weight:bold;">{ref}</code>.<br><br>
            Dès validation (généralement en moins de 5 minutes), votre clé d'activation vous sera expédiée directement au <b>{tel}</b>.
        </p>
        <div style="background:linear-gradient(135deg, #fef2f2, #fee2e2); border:1px solid #fecaca; border-radius:8px; padding:10px; margin-top:15px; font-size:11px; color:#991b1b; font-weight:700; text-align:center;">
            ⏰ Si vous n'avez pas reçu votre clé après <b>15 minutes</b>, n'hésitez pas à nous appeler directement au <b>{NUMERO_MVOLA}</b> ou nous écrire sur WhatsApp.
        </div>
        <a href="/" class="btn-primary" style="margin-top:15px;">RETOUR À L'ACCUEIL</a>
    </div>
    """
    return render(content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:12px 15px; border-radius:10px; font-size:13px; margin-bottom:12px;">❌ Clé incorrecte ou expirée !</div><a href="/" class="btn-primary">Retour</a></div>')
    if result.get("utilisations", 0) >= 1:
        return render('<div class="card"><div style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:12px 15px; border-radius:10px; font-size:13px; margin-bottom:12px;">❌ Clé déjà consommée. 1 Clé = 1 Routeur.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    session["authenticated"] = True
    session["licence"] = cle
    session["client"] = result["client"]
    session["type_abo"] = result["type"]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    cle = session.get("licence")
    result = verifier_licence(cle)
    if not result or result.get("utilisations", 0) >= 1:
        session.clear()
        return render('<div class="card"><div style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:12px 15px; border-radius:10px; font-size:13px; margin-bottom:12px;">❌ Clé déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    plan_key = session.get("type_abo", "basic")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["basic"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    ip_chips = "".join([f'<span class="ip-chip" onclick="setIP(\'{ip}\')">{ip}</span>' for ip in IP_SUGGESTIONS])
    
    feat_html = "<div style='background:#f0fdf4; padding:8px 12px; border-radius:8px; font-size:11px; border-left:4px solid #10b981; margin-bottom:4px;'>✅ <b>Réseau A à Z</b> : Bridge, Ports Auto, WAN Port 1, DHCP, NAT</div><div style='background:#f0fdf4; padding:8px 12px; border-radius:8px; font-size:11px; border-left:4px solid #10b981; margin-bottom:4px;'>✅ <b>Sécurité Pro</b> : Pare-feu Stateful, Blocage IPv6 & P2P, DNS DoH Cloudflare</div>"
    
    dns_input_html = ""
    bandwidth_html = ""
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='background:#f0f9ff; padding:8px 12px; border-radius:8px; font-size:11px; border-left:4px solid #0284c7; margin-bottom:4px;'>🚀 <b>VPN WireGuard Inclus</b> : Tunnel ultra-sécurisé, gratuit à vie.</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='background:#fffbeb; padding:8px 12px; border-radius:8px; font-size:11px; border-left:4px solid #f59e0b; margin-bottom:4px;'>🎫 <b>Hotspot Wi-Fi Zone</b> : Portail captif et contrôle de débit.</div>"
        dns_input_html = '<label>🔗 Adresse de la page Hotspot (ex: wifizone.wifi) :</label><input type="text" name="dns_name" value="wifizone.wifi" required>'
        
        bw_cards_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            ck = "checked" if k == "illimite" else ""
            active_class = "active" if k == "illimite" else ""
            bw_cards_html += f"""
            <div style="background:#ffffff; border:2px solid {'#a855f7' if k=='illimite' else 'var(--border-light)'}; padding:10px; border-radius:10px; cursor:pointer; display:flex; align-items:center; gap:8px;" onclick="document.querySelectorAll('input[name=bandwidth]').forEach(r=>r.parentElement.style.borderColor='var(--border-light)'); this.style.borderColor='#a855f7'; this.querySelector('input').checked=true; document.getElementById('custom-bw-box').style.display=('{k}'==='custom'?'grid':'none');">
                <input type="radio" name="bandwidth" value="{k}" {ck} style="width:16px;height:16px;margin:0;">
                <div><b style="font-size:11px; display:block;">{v['nom']}</b><span style="font-size:9px; color:var(--text-muted);">{v['desc']}</span></div>
            </div>
            """
        
        bandwidth_html = f"""
        <div style="background:linear-gradient(135deg, #f8fafc, #f1f5f9); border:1px dashed #c4b5fd; padding:14px; border-radius:12px; margin-top:12px;">
            <div style="font-size:11px; font-weight:800; color:var(--accent-purple); margin-bottom:8px;">📊 LIMITATION DU DÉBIT (CLIQUEZ SUR VOTRE CHOIX) :</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">{bw_cards_html}</div>
            <div id="custom-bw-box" style="display:none; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px;">
                <div><label style="margin-top:0;">Download (ex: 5M)</label><input type="text" name="custom_down" value="3M"></div>
                <div><label style="margin-top:0;">Upload (ex: 1M)</label><input type="text" name="custom_up" value="1M"></div>
            </div>
        </div>
        """
        
    if plan_key == "pro":
        feat_html += "<div style='background:#fef2f2; padding:8px 12px; border-radius:8px; font-size:11px; border-left:4px solid #dc2626; margin-bottom:4px;'>🏢 <b>Pack Pro WISP</b> : Serveur PPPoE + QoS Bandwidth (PCQ).</div>"
        
    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding:10px; background:rgba(255,255,255,0.8); border-radius:12px; border:1px solid var(--border-light);">
        <span style="background:linear-gradient(135deg, #0284c7, #7c3aed); color:#fff; padding:4px 10px; border-radius:20px; font-size:10px; font-weight:700;">{plan_info['nom']} • 1 Clé = 1 Routeur</span>
        <a href="/logout" style="color:var(--accent-red); font-size:11px; text-decoration:none; font-weight:800;">Fermer Session ✕</a>
    </div>
    <div class="card">
        <div class="card-title">⚙️ GÉNÉRATEUR MIKROTIK - {session['client']}</div>
        <div style="background:#fffbeb; border:1px solid #fde68a; color:#92400e; padding:10px; border-radius:8px; font-size:11px; margin-bottom:15px;">⚠️ Cette clé sera <b>définitivement consommée</b> et verrouillée après l'appui sur le bouton "Générer".</div>
        <form method="POST" action="/generate">
            <label>1. Votre Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Nom de l'équipement (Identity) :</label>
            <input type="text" name="client_final" placeholder="Ex: Boutique_Rasoa" required>

            <label>3. Adresse IP Locale du Routeur :</label>
            <input type="text" name="router_ip" id="router_ip" value="192.168.88.1" placeholder="Tapez votre IP ou choisissez ci-dessous" required>
            <div class="ip-suggestions">{ip_chips}</div>
            <small style="color:var(--text-muted); font-size:10px; display:block; margin-top:6px;">💡 Le Serveur DHCP et le sous-réseau seront calculés et configurés automatiquement en fonction de cette IP.</small>

            <div style="background:linear-gradient(135deg, #f0f9ff, #e0f2fe); border:1px dashed #7dd3fc; padding:15px; border-radius:12px; margin-top:15px;">
                <div style="font-size:12px; font-weight:800; color:var(--accent-cyan); margin-bottom:10px;">📶 PARAMÈTRES WI-FI (DUAL BAND 2.4G & 5G)</div>
                <label style="margin-top:0;">Nom du réseau (SSID) :</label>
                <input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe Wi-Fi :</label>
                <input type="text" name="wifi_pass" value="ketrika2025" required>
                {dns_input_html}
            </div>
            
            {bandwidth_html}
            
            <label style="margin-top:20px;">4. Récapitulatif des inclusions de votre clé :</label>
            <div style="margin-top:8px;">{feat_html}</div>
            
            <button type="submit" class="btn-primary" style="margin-top:20px; padding:16px; font-size:15px;">🚀 GÉNÉRER LA CONFIGURATION UNIQUE</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["GET", "POST"])
def generate():
    if request.method == "GET":
        return redirect(url_for("dashboard"))
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    cle = session.get("licence")
    result = verifier_licence(cle)
    if not result or result.get("utilisations", 0) >= 1:
        session.clear()
        return render('<div class="card"><div style="background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:12px; border-radius:10px; font-size:13px; margin-bottom:12px;">❌ Cette clé a déjà été consommée.</div><a href="/" class="btn-primary">Retour à l\'Accueil</a></div>')
    
    modele = request.form.get("modele", "")
    plan_key = session.get("type_abo", "basic")
    client_final = request.form.get("client_final", "Client").replace(" ", "_")
    ssid = request.form.get("ssid", "KETRIKA-NET")
    wifi_pass = request.form.get("wifi_pass", "ketrika2025")
    dns_name = request.form.get("dns_name", "ketrika.wifi")
    router_ip = request.form.get("router_ip", "192.168.88.1")
    
    bw_choice = request.form.get("bandwidth", "illimite")
    if bw_choice == "custom":
        bw_down = request.form.get("custom_down", "3M")
        bw_up = request.form.get("custom_up", "1M")
    else:
        bp = BANDWIDTH_PROFILES.get(bw_choice, BANDWIDTH_PROFILES["illimite"])
        bw_down = bp["down"]
        bw_up = bp["up"]
    
    options = {"ssid": ssid, "wifi_pass": wifi_pass, "dns_name": dns_name, "bw_down": bw_down, "bw_up": bw_up, "router_ip": router_ip}
    warp_data = creer_config_warp_complete() if plan_key in ["warp", "hotspot", "pro"] else {}
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    sauvegarder_config(cle, client_final, modele, plan_key, options, warp_data, config_id)
    incrementer_utilisation(cle)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE licences SET actif=0, nb_utilisations=1 WHERE cle=?", (cle,))
    
    # Envoi de l'email si renseigné lors de la commande !
    c.execute("SELECT email, client_nom, formule FROM commandes WHERE cle_generee=?", (cle,))
    cmd_data = c.fetchone()
    if cmd_data and cmd_data[0] and "@" in cmd_data[0]:
        envoyer_email_cle(cmd_data[0], cmd_data[1], cle, TARIFS_MODULES.get(cmd_data[2], {}).get("nom", "Pack"))
    
    conn.commit()
    conn.close()
    session.clear()
    
    host = request.host_url.rstrip('/').replace("http://", "https://")
    online_cmd = f'/tool fetch url="{host}/config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    cfg = get_config_by_id(config_id)
    raw_s = build_raw_script(cfg)
    clean_s = clean_script_for_oneliner(raw_s)
    one_liner = f'/system script add name=ketrika_run source="{clean_s}"; /system script run ketrika_run; /system script remove ketrika_run'
    
    content = f"""
    <div class="card">
        <div style="background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; padding:12px 16px; border-radius:12px; margin-bottom:15px; font-size:14px; font-weight:bold; display:flex; align-items:center; gap:8px;">
            ✅ Configuration générée avec succès pour : {client_final}
        </div>
        
        <div style="background:#fffbeb; border:1px solid #fde68a; color:#92400e; padding:15px; border-radius:12px; margin-bottom:20px; font-size:12px; line-height:1.6;">
            📍 <b>Rappel de Branchement :</b> Câble Starlink sur le <b>Port 1 (ether1)</b> | PC ou Switch sur les <b>autres ports LAN</b>.<br>
            📶 Wi-Fi configuré : <b>{ssid}</b> | 🔑 <b>{wifi_pass}</b> | 🌐 IP du Routeur : <b>{router_ip}</b><br>
            <span style="color:#dc2626; font-weight:bold; display:block; margin-top:8px;">🔒 Cette clé d'activation est maintenant définitivement consommée et verrouillée en base de données.</span>
        </div>

        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE (RECOMMANDÉE)</div>
        <div style="background:#f8fafc; border:1px solid var(--border-light); border-radius:10px; padding:12px; margin-top:10px; margin-bottom:10px; font-size:12px; line-height:1.6;">
            <b>📖 Mode d'emploi pas-à-pas :</b>
            <ol style="margin-left:20px; margin-top:5px; color:var(--text-body);">
                <li style="margin-bottom:4px;">Ouvrez <b>Winbox</b> et connectez-vous sur votre MikroTik en cliquant sur l'<b>Adresse MAC</b> (onglet <i>Neighbors</i>).</li>
                <li style="margin-bottom:4px;">Cliquez sur <b>New Terminal</b> dans le menu de gauche.</li>
                <li style="margin-bottom:4px;">Cliquez sur le bouton violet ci-dessous pour copier la commande, puis <b>collez-la (Clic droit &gt; Paste)</b> dans la fenêtre noire du terminal.</li>
                <li>Appuyez sur la touche <b>Entrée</b> : en 5 secondes, le routeur applique toute la configuration de A à Z !</li>
            </ol>
        </div>
        
        <div style="background:#0f172a; border:1px solid #10b981; color:#4ade80; padding:15px; border-radius:10px; font-family:'Courier New', monospace; font-size:11px; word-break:break-all; box-shadow:inset 0 0 20px rgba(16,185,129,0.1);" id="cmd1">{one_liner}</div>
        <button style="background:linear-gradient(135deg, #7c3aed, #6d28d9); color:#fff; padding:14px; border-radius:10px; border:none; font-weight:800; cursor:pointer; width:100%; font-family:'Space Grotesk'; font-size:13px; margin-top:10px; box-shadow:0 4px 15px rgba(124,58,237,0.3); transition:0.3s;" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE UNIQUE</button>

        <hr style="border:none; border-top:1px solid var(--border-light); margin:25px 0;">

        <div class="card-title">MÉTHODE 2 : TÉLÉCHARGER LE FICHIER (.RSC)</div>
        <div style="font-size:11px; color:var(--text-muted); margin-bottom:10px;">Téléchargez le fichier, glissez-déposez le dans le menu <b>Files</b> de Winbox, puis tapez <code>/import file-name=ketrika.rsc</code> dans le terminal.</div>
        <a href="/download/{config_id}.rsc" style="display:block; text-align:center; text-decoration:none; background:linear-gradient(135deg, #059669, #047857); color:#fff; padding:14px; border-radius:10px; font-family:'Space Grotesk'; font-weight:800; font-size:13px; box-shadow:0 4px 15px rgba(5,150,105,0.3);">📥 TÉLÉCHARGER LE FICHIER KETRIKA.RSC</a>
        
        <hr style="border:none; border-top:1px solid var(--border-light); margin:25px 0;">
        
        <a href="/" style="display:block; text-align:center; text-decoration:none; background:linear-gradient(135deg, #0284c7, #0369a1); color:#fff; padding:14px; border-radius:10px; font-family:'Space Grotesk'; font-weight:800; font-size:13px;">🏠 TERMINER ET RETOURNER À L'ACCUEIL</a>
    </div>
    """
    return render(content)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ACCÈS ADMINISTRATEUR</div><form method="POST"><input type="text" name="username" placeholder="Identifiant" required><input type="password" name="password" placeholder="Mot de passe" required><button type="submit" class="btn-primary">CONNEXION SÉCURISÉE</button></form></div>')

@app.route("/admin/dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC")
    cmds = c.fetchall()
    conn.close()
    
    rows = ""
    for cmd in cmds:
        # cmd[0]=id, cmd[1]=nom, cmd[2]=tel, cmd[3]=email, cmd[4]=formule, cmd[5]=montant, cmd[6]=ref, cmd[8]=date
        email_str = f"<br><small style='color:var(--accent-cyan);'>{cmd[3]}</small>" if cmd[3] else ""
        rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid var(--border-light);">
                <b>{cmd[1]}</b><br>
                <small>{cmd[2]}</small>{email_str}
            </td>
            <td style="padding:10px; border-bottom:1px solid var(--border-light);">
                <span style="background:var(--accent-purple); color:#fff; padding:3px 6px; border-radius:4px; font-size:9px; font-weight:bold;">{cmd[4].upper()}</span><br>
                <b style="color:var(--accent-green); font-size:12px; display:block; margin-top:4px;">{cmd[5]:,} Ar</b>
            </td>
            <td style="padding:10px; border-bottom:1px solid var(--border-light);">
                <code style="background:#f1f5f9; padding:4px; border-radius:4px; border:1px solid #cbd5e1; font-size:10px; color:#b45309; font-weight:bold;">{cmd[6]}</code>
            </td>
            <td style="padding:10px; border-bottom:1px solid var(--border-light);">
                <form method="POST" action="/admin/valider/{cmd[0]}">
                    <button type="submit" style="background:linear-gradient(135deg, #10b981, #059669); color:#fff; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; font-size:10px; cursor:pointer; box-shadow:0 2px 5px rgba(16,185,129,0.3);">⚡ VALIDER</button>
                </form>
            </td>
        </tr>
        """
        
    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
        <div class="card-title" style="margin:0;">📋 COMMANDES EN ATTENTE ({len(cmds)})</div>
        <a href="/admin/creer" style="background:var(--accent-cyan); color:#fff; text-decoration:none; padding:6px 12px; border-radius:20px; font-size:11px; font-weight:bold;">➕ Créer Clé Manuelle</a>
    </div>
    
    <div class="card" style="padding:10px;">
        <div style="overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse; font-size:11px;">
                <thead>
                    <tr>
                        <th style="text-align:left; padding:10px; border-bottom:2px solid var(--border-light); color:var(--text-muted); text-transform:uppercase;">Client / Contacts</th>
                        <th style="text-align:left; padding:10px; border-bottom:2px solid var(--border-light); color:var(--text-muted); text-transform:uppercase;">Pack / Prix</th>
                        <th style="text-align:left; padding:10px; border-bottom:2px solid var(--border-light); color:var(--text-muted); text-transform:uppercase;">Réf Paiement</th>
                        <th style="text-align:left; padding:10px; border-bottom:2px solid var(--border-light); color:var(--text-muted); text-transform:uppercase;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else "<tr><td colspan='4' style='text-align:center; padding:20px; color:var(--text-muted); font-size:12px;'>Aucune commande en attente.</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>
    """
    return render(content)

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,))
    cmd = c.fetchone()
    
    email_status = ""
    if cmd:
        cle = creer_licence(cmd[1], cmd[2], cmd[4], cmd[5])
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id))
        conn.commit()
        
        # Envoi Automatique par Email si le champ contient un @
        email_client = cmd[3]
        if email_client and "@" in email_client:
            pack_nom = TARIFS_MODULES.get(cmd[4], {}).get("nom", "Pack KETRIKA")
            sent = envoyer_email_cle(email_client, cmd[1], cle, pack_nom)
            if sent:
                email_status = f"<br>📧 <b>Un email a été envoyé automatiquement à {email_client} !</b>"
            else:
                email_status = f"<br>⚠️ <i>Note : Le compte Gmail n'est pas encore configuré dans le code. Email non envoyé.</i>"
                
    conn.close()
    
    return render(f"""
    <div class="card">
        <div style="background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; padding:15px; border-radius:10px; font-size:13px; line-height:1.5;">
            ✅ <b>Commande validée avec succès pour {cmd[1]} !</b>{email_status}
        </div>
        <div class="card-title" style="margin-top:20px;">🔑 CLÉ D'ACTIVATION À ENVOYER (Si pas d'email) :</div>
        <div style="background:#0f172a; color:#38bdf8; font-family:'Courier New', monospace; font-size:18px; font-weight:bold; padding:20px; text-align:center; border-radius:10px; letter-spacing:3px; margin:15px 0; border:1px solid #0284c7;" id="cle_box">{cle}</div>
        <button onclick="copyText('cle_box','bcp')" id="bcp" style="background:var(--accent-purple); color:#fff; border:none; padding:12px; width:100%; border-radius:8px; font-weight:bold; cursor:pointer;">📋 COPIER LA CLÉ POUR ENVOYER PAR SMS / WHATSAPP</button>
        <a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">RETOUR AU TABLEAU DE BORD</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"): return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f"""
        <div class="card">
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; color:#065f46; padding:15px; border-radius:10px; font-size:13px;">✅ <b>Clé générée avec succès (1 usage unique).</b></div>
            <div style="background:#0f172a; color:#38bdf8; font-family:'Courier New', monospace; font-size:18px; font-weight:bold; padding:20px; text-align:center; border-radius:10px; letter-spacing:3px; margin:15px 0; border:1px solid #0284c7;" id="cle_box">{cle}</div>
            <button onclick="copyText('cle_box','bcp')" id="bcp" style="background:var(--accent-purple); color:#fff; border:none; padding:12px; width:100%; border-radius:8px; font-weight:bold; cursor:pointer;">📋 COPIER LA CLÉ</button>
            <a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">RETOUR AU DASHBOARD</a>
        </div>
        """)
    
    return render("""
    <div class="card">
        <div class="card-title">➕ CRÉATION DE CLÉ MANUELLE</div>
        <form method="POST">
            <label>Nom du client :</label>
            <input type="text" name="client" placeholder="Ex: Rakoto" required>
            <label>Téléphone ou Email :</label>
            <input type="text" name="tel" placeholder="Ex: 034 00 000 00" required>
            <label>Formule / Pack :</label>
            <select name="type" required>
                <option value="basic">🛡️ Pack Basic (10 000 Ar)</option>
                <option value="standard">⭐ Pack Standard (15 000 Ar)</option>
                <option value="warp">🚀 Premium VPN (20 000 Ar)</option>
                <option value="hotspot">🎫 Wi-Fi Zone Hotspot (30 000 Ar)</option>
                <option value="pro">🏢 Pro WISP (50 000 Ar)</option>
            </select>
            <button type="submit" class="btn-primary" style="margin-top:20px;">GÉNÉRER LA CLÉ</button>
            <a href="/admin/dashboard" style="display:block; text-align:center; margin-top:15px; font-size:12px; color:var(--text-muted); text-decoration:none;">Annuler et retourner</a>
        </form>
    </div>
    """)

@app.errorhandler(404)
def handle_404(e):
    return redirect(url_for("home"))

@app.errorhandler(500)
def handle_500(e):
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
