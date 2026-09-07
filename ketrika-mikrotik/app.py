from flask import Flask, request, Response, render_template_string, session, redirect, url_for, send_file
from database import *
from warp_api import creer_config_warp_complete
import sqlite3, secrets, string, random, io, traceback
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
init_db()

FB_LINK = "https://www.facebook.com/loza.nama.376"
NUMERO_MVOLA = "038 28 171 00"
NUMERO_ORANGE = "037 39 755 72"
NOM_COMPTE = "Jean Eric"

def init_extra_tables():
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY AUTOINCREMENT, client_nom TEXT, telephone TEXT, formule TEXT, montant REAL, reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE', cle_generee TEXT, date_commande TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS avis (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, ville TEXT, etoiles INTEGER NOT NULL, commentaire TEXT NOT NULL, date_avis TEXT)''')
    c.execute("SELECT COUNT(*) FROM avis")
    if c.fetchone()[0] < 3:
        avis_initiaux = [
            ("Mamy R.", "Antananarivo", 5, "Script injecté après reset total sur mon hAP ax2. Configuration parfaite du premier coup !", "2026-01-15"),
            ("Jean Luc", "Tamatave", 5, "Configuration propre sur hAP ac2. Wi-Fi et pare-feu impeccables.", "2026-01-20"),
            ("Boutique Alpha", "Majunga", 5, "Pack Wi-Fi Zone parfait avec gestion de débit pour mon business.", "2026-01-28"),
            ("Toky N.", "Diego Suarez", 5, "Excellente qualité de service. Support WhatsApp très réactif.", "2026-02-02")
        ]
        c.executemany("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", avis_initiaux)
    test_keys = [("KTR-BASIC-10K", "Test Basic", "0382817100", "basic", 10000),("KTR-STANDARD-15K", "Test Standard", "0382817100", "standard", 15000),("KTR-WARP-20K", "Test Warp", "0382817100", "warp", 20000),("KTR-HOTSPOT-30K", "Test Hotspot", "0382817100", "hotspot", 30000),("KTR-PRO-50K", "Test Pro", "0382817100", "pro", 50000)]
    for k in test_keys:
        c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, actif, nb_utilisations, prix_paye) VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?)", (k[0], k[1], k[2], k[3], datetime.now().isoformat(), "2027-01-01", k[4]))
    conn.commit()
    conn.close()

init_extra_tables()

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "desc": "Config complète A à Z + Wi-Fi + Optimisation", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Premium VPN", "prix": 20000, "desc": "Standard + Tunnel WireGuard confidentiel gratuit", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "desc": "Premium + Portail Hotspot + Contrôle Débit", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "desc": "Solution intégrale + PPPoE + QoS avancé", "badge": "PRO"}
}

MODELES_MIKROTIK = ["hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)", "hAP ac2 (Dual Band Wireless)", "hAP ac3 (Dual Band Wireless)", "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (Wireless)", "LHG 5", "SXTsq", "hAP lite (Wireless 2.4G)", "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)", "CCR1009", "CCR2004", "CCR2116", "Chateau LTE/5G", "Autre RouterOS v7"]

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
    <title>KETRIKA MIKROTIK PRO • Optimisation Réseau Professionnelle</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #eef2ff;
            --bg-card: #ffffff;
            --accent-cyan: #0284c7;
            --accent-green: #059669;
            --accent-purple: #7c3aed;
            --accent-orange: #ea580c;
            --accent-gold: #f59e0b;
            --accent-red: #dc2626;
            --accent-pink: #db2777;
            --text-dark: #0f172a;
            --text-body: #334155;
            --text-muted: #64748b;
            --border-light: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: linear-gradient(135deg, #eef2ff 0%, #f1f5f9 100%);
            color: var(--text-dark); min-height: 100vh; padding: 10px;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 860px; margin: auto; }

        /* NAVBAR */
        .top-nav { 
            display: flex; justify-content: space-between; align-items: center; 
            margin-bottom: 12px; padding: 10px 14px; 
            background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
            border: 1px solid var(--border-light); border-radius: 14px; 
            box-shadow: 0 4px 15px rgba(2,132,199,0.06); gap: 6px; flex-wrap: wrap;
        }
        .nav-brand { display: flex; align-items: center; gap: 8px; font-family: 'Space Grotesk'; font-weight: 800; font-size: 13px; color: var(--text-dark); text-decoration: none; }
        .nav-logo-icon { width: 26px; height: 26px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; }
        .top-links { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
        .top-links a { font-size: 11px; color: #fff; text-decoration: none; font-weight: 700; padding: 6px 11px; border-radius: 10px; transition: 0.2s; white-space: nowrap; }
        .btn-fb { background: linear-gradient(135deg, #1877f2, #0d6efd); }
        .btn-tuto { background: linear-gradient(135deg, #7c3aed, #6d28d9); }
        .lang-btn { background: linear-gradient(135deg, #ede9fe, #ddd6fe); color: var(--accent-purple); border: 1px solid #c4b5fd; padding: 6px 10px; border-radius: 10px; font-size: 11px; font-weight: 700; cursor: pointer; }

        /* HEADER */
        .header { text-align: center; padding: 14px 5px 20px; }
        .logo-wrapper {
            position: relative; width: 80px; height: 80px; margin: 0 auto 10px;
            display: flex; align-items: center; justify-content: center;
        }
        .logo-aura {
            position: absolute; inset: -3px; border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink));
            filter: blur(8px); opacity: 0.7;
        }
        .logo-box {
            position: relative; width: 100%; height: 100%; border-radius: 50%;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            border: 2px solid rgba(255,255,255,0.9);
            display: flex; align-items: center; justify-content: center;
        }
        .logo-box svg { width: 42px; height: 42px; }

        .header h1 { 
            font-family: 'Space Grotesk', sans-serif; font-size: 28px; font-weight: 900; 
            background: linear-gradient(135deg, #0284c7, #7c3aed, #db2777, #059669); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
            letter-spacing: 1px; line-height: 1.2;
        }
        @media (min-width: 500px) { .header h1 { font-size: 34px; } }
        .header .tagline { color: var(--text-body); font-size: 13px; margin-top: 6px; font-weight: 600; }
        .header .stats-live { 
            display: inline-flex; gap: 6px; margin-top: 10px; padding: 5px 12px; 
            background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #a7f3d0; 
            border-radius: 20px; font-size: 11px; color: var(--accent-green); font-weight: 700; 
            align-items: center;
        }
        .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; display: inline-block; }

        /* CARDS */
        .card { 
            background: var(--bg-card); border: 1px solid var(--border-light); 
            border-radius: 16px; padding: 18px 16px; margin-bottom: 14px; 
            box-shadow: 0 4px 15px rgba(15,23,42,0.05); position: relative; overflow: hidden;
        }
        @media (min-width: 500px) { .card { padding: 22px; } }
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink), var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 14px; color: var(--accent-cyan); margin-bottom: 12px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }
        @media (min-width: 500px) { .card-title { font-size: 15px; } }

        /* 🎛️ DASHBOARD DE PERFORMANCE VISUEL */
        .live-dashboard {
            background: #0f172a; border: 1px solid #334155; border-radius: 14px;
            padding: 16px; margin: 12px 0; color: #fff; box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
        }
        .dashboard-grid {
            display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;
        }
        @media (min-width: 600px) { .dashboard-grid { grid-template-columns: repeat(4, 1fr); } }
        .dash-item {
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            padding: 10px; border-radius: 10px; text-align: center;
        }
        .dash-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700; }
        .dash-value { font-family: 'Space Grotesk'; font-size: 16px; font-weight: 900; color: #38bdf8; margin-top: 2px; }
        .dash-value.green { color: #4ade80; }

        /* 🏆 BADGES DE CONFIANCE & CERTIFICATIONS */
        .trust-badges-grid {
            display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 10px;
        }
        @media (min-width: 600px) { .trust-badges-grid { grid-template-columns: repeat(4, 1fr); } }
        .trust-badge-card {
            background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 1px solid var(--border-light);
            padding: 10px 8px; border-radius: 10px; text-align: center;
        }
        .trust-badge-icon { font-size: 20px; display: block; margin-bottom: 2px; }
        .trust-badge-title { font-size: 11px; font-weight: 800; color: var(--text-dark); }
        .trust-badge-desc { font-size: 9px; color: var(--text-muted); margin-top: 2px; }

        .hero-card {
            background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%);
            color: #fff; padding: 20px 16px; border-radius: 18px; margin-bottom: 14px;
            box-shadow: 0 10px 30px rgba(2,132,199,0.25);
        }
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

        .visual-container {
            background: #0f172a; border-radius: 12px; padding: 16px; margin: 12px 0;
            border: 1px solid #334155; color: #fff; text-align: center;
        }
        .ports-bar {
            display: flex; justify-content: center; gap: 6px; margin: 14px 0; flex-wrap: wrap;
        }
        .port-indicator {
            background: #1e293b; border: 2px solid #475569; border-radius: 8px;
            padding: 8px 12px; font-family: 'Space Grotesk'; font-size: 11px; min-width: 70px;
        }
        .port-indicator.wan { border-color: #0284c7; background: rgba(2,132,199,0.2); }
        .port-indicator.wan b { color: #38bdf8; display: block; }
        .port-indicator.lan { border-color: #10b981; background: rgba(16,185,129,0.15); }
        .port-indicator.lan b { color: #4ade80; display: block; }

        .winbox-mockup {
            background: #1e293b; border-radius: 8px; border: 1px solid #475569;
            text-align: left; overflow: hidden; margin: 10px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }
        .winbox-top {
            background: #334155; padding: 6px 12px; display: flex; justify-content: space-between;
            font-size: 11px; font-weight: 700; color: #cbd5e1;
        }
        .winbox-body { padding: 12px; font-family: 'Courier New', monospace; font-size: 11px; }
        .winbox-item {
            background: rgba(2,132,199,0.25); border: 1px solid #0284c7; padding: 6px 10px;
            border-radius: 4px; display: flex; justify-content: space-between; color: #38bdf8;
            font-weight: bold; margin-top: 6px;
        }

        .step-guide { background: #f8fafc; border: 1px solid var(--border-light); border-radius: 10px; padding: 14px; margin-top: 10px; }
        .step-guide ol { padding-left: 18px; margin: 6px 0; font-size: 12px; color: var(--text-body); line-height: 1.6; }
        .step-guide li { margin-bottom: 4px; }
        .step-guide b { color: var(--accent-cyan); }

        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input[type="text"], input[type="tel"], input[type="password"], select, textarea { 
            width: 100%; padding: 12px 14px; margin-top: 4px; 
            background: #f8fafc; border: 1px solid var(--border-light); 
            border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit;
        }

        .ip-suggestions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
        .ip-chip { background: linear-gradient(135deg, #e0f2fe, #f0f9ff); color: var(--accent-cyan); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; cursor: pointer; border: 1px solid #bae6fd; font-family: 'Courier New', monospace; }

        .btn-primary { 
            width: 100%; padding: 14px; margin-top: 12px; 
            background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; 
            border: none; border-radius: 10px; font-size: 13px; font-weight: 800; 
            cursor: pointer; font-family: 'Space Grotesk'; text-transform: uppercase; 
            text-decoration: none; display: block; text-align: center;
        }
        .btn-success { background: linear-gradient(135deg, #059669, #047857); }
        .btn-copy { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff; padding: 12px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase; margin-top: 8px; font-size: 12px; }
        .btn-copy.copied { background: linear-gradient(135deg, #059669, #047857); }

        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 6px; }
        .plan-option { 
            background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 2px solid var(--border-light); 
            padding: 12px 10px; border-radius: 12px; cursor: pointer; 
            display: flex; justify-content: space-between; align-items: center; 
            position: relative; gap: 8px;
        }
        .plan-option.selected, .plan-option:hover { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-option input[type="radio"] { width: 18px; height: 18px; accent-color: var(--accent-cyan); flex-shrink: 0; cursor: pointer; }
        .plan-info { flex: 1; min-width: 0; }
        .plan-info b { font-size: 13px; display: block; }
        @media (min-width: 500px) { .plan-info b { font-size: 14px; } }
        .plan-info div { color: var(--text-muted); font-size: 10px; margin-top: 2px; }
        .plan-price { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; gap: 2px; }
        .plan-price b { color: var(--accent-green); font-size: 14px; font-family: 'Space Grotesk'; white-space: nowrap; }
        .plan-badge { position: absolute; top: -1px; right: 10px; padding: 2px 8px; border-radius: 0 0 6px 6px; font-size: 8px; font-weight: 800; color: #fff; font-family: 'Space Grotesk'; }
        .badge-popular { background: #ea580c; }
        .badge-best { background: #db2777; }
        .badge-pro { background: #059669; }

        .bw-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .bw-grid { grid-template-columns: 1fr 1fr; } }
        .bw-card {
            background: #ffffff; border: 2px solid var(--border-light);
            padding: 10px 12px; border-radius: 10px; cursor: pointer;
            display: flex; align-items: center; gap: 10px; transition: 0.2s;
        }
        .bw-card:hover, .bw-card.active { border-color: var(--accent-purple); background: #faf5ff; }
        .bw-card input[type="radio"] { width: 20px; height: 20px; accent-color: var(--accent-purple); flex-shrink: 0; cursor: pointer; margin: 0; }
        .bw-card-text b { font-size: 12px; color: var(--text-dark); display: block; }
        .bw-card-text span { font-size: 10px; color: var(--text-muted); }

        .payment-banner { background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #fde68a; border-radius: 12px; padding: 14px; margin-top: 12px; text-align: center; }
        .payment-title { color:#92400e; font-size: 12px; font-family:'Space Grotesk'; font-weight: 800; }
        .payment-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 8px; }
        @media (min-width: 500px) { .payment-grid { grid-template-columns: 1fr 1fr; } }
        .payment-box { background: #fff; border: 1px solid #fde68a; border-radius: 10px; padding: 10px; }
        .payment-box .method { font-size: 11px; font-weight: 800; }
        .payment-box .number { font-family: 'Space Grotesk'; font-size: 17px; font-weight: 900; color: #b45309; margin: 3px 0; }
        .payment-box .name { font-size: 10px; color: var(--text-muted); }
        .payment-warning { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 8px; margin-top: 8px; font-size: 11px; color: #991b1b; font-weight: 700; line-height: 1.4; }

        .terminal-box { background: #0f172a; border: 1px solid #334155; color: #4ade80; padding: 12px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 6px; line-height: 1.5; }
        .badge { background: #e0f2fe; color: var(--accent-cyan); padding: 4px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; }
        .alert { padding: 10px 12px; border-radius: 10px; margin-bottom: 10px; font-size: 12px; }
        .alert-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
        .alert-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
        .alert-warning { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }

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
        <!-- TOP NAV -->
        <div class="top-nav">
            <a href="/" class="nav-brand">
                <div class="nav-logo-icon">⚡</div>
                <span>KETRIKA MIKROTIK</span>
            </a>
            <div class="top-links">
                <a href="/tuto" class="btn-tuto">📖 Guide &amp; Tuto</a>
                <a href="{{ fb_link }}" target="_blank" class="btn-fb">📘 Facebook</a>
                <button class="lang-btn" onclick="toggleLang()">🇲🇬/🇫🇷</button>
            </div>
        </div>

        <!-- HEADER -->
        <div class="header">
            <div class="logo-wrapper">
                <div class="logo-aura"></div>
                <div class="logo-box">
                    <svg viewBox="0 0 24 24" fill="none" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <defs>
                            <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#00f2fe" />
                                <stop offset="100%" stop-color="#7c3aed" />
                            </linearGradient>
                        </defs>
                        <rect x="2" y="14" width="20" height="8" rx="2" fill="rgba(0,242,254,0.1)"></rect>
                        <path d="M6 18h.01"></path><path d="M10 18h.01"></path><path d="M14 18h.01"></path><path d="M18 18h.01"></path>
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#00f2fe" stroke="#00f2fe" stroke-width="1.5"></path>
                    </svg>
                </div>
            </div>
            <h1>KETRIKA MIKROTIK</h1>
            <p class="tagline txt-fr">Solution Professionnelle d'Optimisation Réseau MikroTik</p>
            <p class="tagline txt-mg" style="display:none;">Fitaovana matihanina hanatsarana ny MikroTik</p>
            <div class="stats-live"><span class="live-dot"></span><span>Config en 5 secondes • Support 7j/7 • 1 Clé = 1 Routeur</span></div>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • <a href="{{ fb_link }}" target="_blank">📘 Facebook Officiel</a> • <a href="/tuto">📖 Guide d'Installation</a><br>📞 038 28 171 00 (Jean Eric)
        </div>
    </div>

    <script>
        let currentLang = 'fr';
        function toggleLang() { 
            currentLang = currentLang === 'fr' ? 'mg' : 'fr'; 
            document.querySelectorAll('.txt-fr').forEach(e => e.style.display = currentLang === 'fr' ? '' : 'none'); 
            document.querySelectorAll('.txt-mg').forEach(e => e.style.display = currentLang === 'mg' ? '' : 'none'); 
        }
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
        
        function selectBW(val) {
            document.querySelectorAll('.bw-card').forEach(c => c.classList.remove('active'));
            const targetCard = document.getElementById('card_' + val);
            if(targetCard) targetCard.classList.add('active');
            const radio = document.getElementById('bw_' + val);
            if(radio) radio.checked = true;
            
            const customDiv = document.getElementById('custom-bw-box');
            if(customDiv) {
                customDiv.style.display = (val === 'custom') ? 'grid' : 'none';
            }
        }

        document.querySelectorAll('.faq-question').forEach(q => { 
            q.addEventListener('click', () => q.parentElement.classList.toggle('active')); 
        });
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

# --- 1. BRIDGE & INTERFACES LAN ---
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

# --- 2. WAN (PORT 1 VIA DHCP-CLIENT) ---
/ip dhcp-client remove [find interface=ether1]
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no use-peer-ntp=yes add-default-route=yes default-route-distance=2 comment="WAN-STARLINK"

# --- 3. ADRESSAGE IP ET SERVEUR DHCP LOCAL ---
/ip address remove [find interface=bridge-lan]
/ip address add address={router_ip}/24 interface=bridge-lan comment="LAN-IP"
/ip pool remove [find name=dhcp-pool]
/ip pool add name=dhcp-pool ranges={dhcp_pool_start}-{dhcp_pool_end}
/ip dhcp-server remove [find interface=bridge-lan]
/ip dhcp-server add name=dhcp-lan interface=bridge-lan address-pool=dhcp-pool disabled=no lease-time=12h
/ip dhcp-server network remove [find address={dhcp_net}]
/ip dhcp-server network add address={dhcp_net} gateway={router_ip} dns-server=1.1.1.1,1.0.0.1 comment="LAN-NET"

# --- 4. ACCES INTERNET (NAT) ---
/ip firewall nat remove [find comment="NAT-INTERNET"]
/ip firewall nat add chain=srcnat out-interface-list=WAN action=masquerade comment="NAT-INTERNET"

# --- 5. OPTIMISATION RESEAU (MANGLE TTL = 64) ---
/ip firewall mangle remove [find comment="STARLINK-TTL-64"]
/ip firewall mangle add chain=postrouting out-interface-list=WAN action=change-ttl new-ttl=set:64 passthrough=yes comment="STARLINK-TTL-64"

# --- 6. DNS SECURISE DOH (CLOUDFLARE) ---
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
# --- 8. WI-FI 6 DEDIE (ROUTEROS V7 WIFI) ---
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
# --- 9. TUNNEL WIREGUARD VPN (CLOUDFLARE WARP) ---
/ip route remove [find comment="WARP-ENDPOINT-ROUTE"]
/ip route add dst-address=162.159.192.0/24 gateway=ether1 distance=1 comment="WARP-ENDPOINT-ROUTE"
/interface wireguard remove [find name=warp-vpn]
/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers remove [find interface="warp-vpn"]
/interface wireguard peers add interface=warp-vpn public-key="{cfg['warp_public']}" endpoint-address=162.159.192.1 endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address remove [find interface="warp-vpn"]
/ip address add address={cfg['warp_ip']}/32 interface=warp-vpn
/interface list member remove [find interface=warp-vpn]
/interface list member add interface=warp-vpn list=WAN
/ip firewall nat remove [find comment="WARP-NAT"]
/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade comment="WARP-NAT"
/ip route remove [find comment="VPN-DEFAULT-ROUTE"]
/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn distance=1 comment="VPN-DEFAULT-ROUTE"
"""

    if plan in ["hotspot", "pro"]:
        s += f"""
# --- 10. SERVEUR HOTSPOT WI-FI ZONE ---
/ip pool remove [find name=hs-pool]
/ip pool add name=hs-pool ranges=10.5.50.10-10.5.50.250
/ip dhcp-server remove [find name=dhcp-hs]
/ip dhcp-server add name=dhcp-hs interface=bridge-lan address-pool=hs-pool disabled=no
/ip hotspot profile remove [find name=hs-prof]
/ip hotspot profile add name=hs-prof hotspot-address=10.5.50.1 dns-name={dns_name}
/ip hotspot user profile remove [find name=hs-user]
/ip hotspot user profile add name=hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot remove [find name=hotspot-ketrika]
/ip hotspot add name=hotspot-ketrika interface=bridge-lan address-pool=hs-pool profile=hs-prof disabled=no
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

@app.route("/")
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT AVG(etoiles), COUNT(*) FROM avis")
    avg_stat, total_avis = c.fetchone()
    avg_note = round(avg_stat, 1) if avg_stat else 5.0
    c.execute("SELECT nom, ville, etoiles, commentaire, date_avis FROM avis ORDER BY id DESC LIMIT 5")
    liste_avis = c.fetchall()
    conn.close()
    
    reviews_html = ""
    for a in liste_avis:
        reviews_html += f'<div class="review-card"><div class="review-header"><span class="review-name">{a[0]} <span class="review-city">({a[1] or "MG"})</span></span><span class="stars-gold">{"⭐" * a[2]}</span></div><div class="review-text">"{a[3]}"</div></div>'
    
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
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked} onchange="document.querySelectorAll('.plan-option').forEach(e=>e.classList.remove('selected')); document.getElementById('opt_{k}').classList.add('selected');">
            </div>
        </label>
        """
    
    content = f"""
    <!-- 🎛️ DASHBOARD DE PERFORMANCE VISUEL EN DIRECT -->
    <div class="live-dashboard">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
            <span style="font-family:'Space Grotesk'; font-weight:800; font-size:12px; color:#38bdf8;">📊 ÉTAT DU PROTOCOLE KETRIKA</span>
            <span class="badge" style="background:#0284c7; color:#fff;">EN LIGNE (300+ VILLES)</span>
        </div>
        <div class="dashboard-grid">
            <div class="dash-item">
                <div class="dash-label">LATENCE / PING</div>
                <div class="dash-value green">&lt; 24 ms</div>
            </div>
            <div class="dash-item">
                <div class="dash-label">CHIFFREMENT</div>
                <div class="dash-value">ChaCha20</div>
            </div>
            <div class="dash-item">
                <div class="dash-label">RÉSOLVEUR DNS</div>
                <div class="dash-value">1.1.1.1 DoH</div>
            </div>
            <div class="dash-item">
                <div class="dash-label">STABILITÉ</div>
                <div class="dash-value green">99.9%</div>
            </div>
        </div>
    </div>

    <!-- 🏆 BADGES DE CONFIANCE & CERTIFICATIONS -->
    <div class="card">
        <div class="trust-badges-grid">
            <div class="trust-badge-card">
                <span class="trust-badge-icon">🛡️</span>
                <div class="trust-badge-title">RouterOS v7 Certifié</div>
                <div class="trust-badge-desc">Compatible tous modèles</div>
            </div>
            <div class="trust-badge-card">
                <span class="trust-badge-icon">🔒</span>
                <div class="trust-badge-title">Zéro Journalisation</div>
                <div class="trust-badge-desc">Confidentialité totale</div>
            </div>
            <div class="trust-badge-card">
                <span class="trust-badge-icon">⚡</span>
                <div class="trust-badge-title">Injection 5s</div>
                <div class="trust-badge-desc">Sans redémarrage</div>
            </div>
            <div class="trust-badge-card">
                <span class="trust-badge-icon">🇲🇬</span>
                <div class="trust-badge-title">Support 7j/7</div>
                <div class="trust-badge-desc">Assistance Madagascar</div>
            </div>
        </div>
    </div>

    <!-- HERO CONVAINCANT -->
    <div class="hero-card">
        <h2>🚀 Pourquoi choisir KETRIKA ?</h2>
        <p>Notre solution utilise les <b>meilleures technologies mondiales</b> pour offrir à votre réseau MikroTik une performance et une sécurité de niveau entreprise.</p>
        <div class="features-detail">
            <div class="feature-detail-box">
                <span class="fd-icon">🔒</span>
                <div class="fd-title">SÉCURITÉ MILITAIRE</div>
                <div class="fd-desc">Chiffrement <b>ChaCha20-Poly1305</b> (WireGuard), le même utilisé par les banques et gouvernements. Vos données sont indéchiffrables.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">⚡</span>
                <div class="fd-title">TUNNEL ULTRA-RAPIDE</div>
                <div class="fd-desc">WireGuard est <b>4x plus rapide qu'OpenVPN</b>. Latence &lt; 2ms. Votre débit reste maximal en toutes circonstances.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🌐</span>
                <div class="fd-title">RÉSEAU CLOUDFLARE</div>
                <div class="fd-desc">Serveurs présents dans <b>300+ villes mondiales</b>. DNS DoH sécurisé 1.1.1.1 : navigation privée garantie.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🛡️</span>
                <div class="fd-title">CONFIDENTIALITÉ</div>
                <div class="fd-desc">Protection de votre vie privée. Routage intelligent, filtrage du trafic P2P, gestion optimale des connexions.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">📶</span>
                <div class="fd-title">WI-FI OPTIMISÉ</div>
                <div class="fd-desc">Configuration Dual Band <b>2.4G + 5G</b> automatique. Wi-Fi 6 supporté pour vitesses maximales.</div>
            </div>
            <div class="feature-detail-box">
                <span class="fd-icon">🎯</span>
                <div class="fd-title">CONFIG COMPLÈTE</div>
                <div class="fd-desc">IP, DHCP, NAT, Firewall Pro, Wi-Fi, VPN : <b>tout configuré automatiquement</b>. Même après un reset total.</div>
            </div>
        </div>
    </div>

    <!-- AVANTAGES CLÉS -->
    <div class="card">
        <div class="card-title">💎 AVANTAGES CLÉS</div>
        <div class="advantages-grid">
            <div class="adv-box"><span class="adv-icon">🔒</span><div class="adv-title">WireGuard</div><div class="adv-desc">ChaCha20</div></div>
            <div class="adv-box"><span class="adv-icon">⚡</span><div class="adv-title">Vitesse Max</div><div class="adv-desc">Latence réduite</div></div>
            <div class="adv-box"><span class="adv-icon">🌐</span><div class="adv-title">DNS Cloudflare</div><div class="adv-desc">DoH 1.1.1.1</div></div>
            <div class="adv-box"><span class="adv-icon">📶</span><div class="adv-title">Config A à Z</div><div class="adv-desc">Après Reset</div></div>
        </div>
    </div>

    <!-- COMMENT ÇA MARCHE -->
    <div class="card">
        <div class="card-title">🚀 COMMENT ÇA MARCHE ?</div>
        <div class="steps-grid">
            <div class="step-box"><div class="step-num">1</div><div class="step-title">Choisir le Pack</div><div class="step-desc">Sélectionnez la formule adaptée à vos besoins</div></div>
            <div class="step-box"><div class="step-num">2</div><div class="step-title">Payer &amp; Recevoir</div><div class="step-desc">Mobile Money → Clé par SMS en 15 min max</div></div>
            <div class="step-box"><div class="step-num">3</div><div class="step-title">Configurer</div><div class="step-desc">1 commande dans Winbox = Config complète</div></div>
        </div>
        <div style="text-align:center; margin-top:14px;">
            <a href="/tuto" class="btn-primary btn-success" style="display:inline-block; width:auto; padding:10px 20px; font-size:12px;">📖 VOIR LE GUIDE D'INSTALLATION DÉTAILLÉ</a>
        </div>
    </div>

    <!-- COMMANDER -->
    <div class="card">
        <div class="card-title">🛒 CHOISIR VOTRE FORMULE</div>
        <div class="alert-warning">⚠️ <b>1 Clé = 1 Routeur uniquement.</b> Chaque clé configure intégralement un seul boîtier MikroTik.</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            <div class="payment-banner">
                <div class="payment-title">📱 PAIEMENT MOBILE MONEY</div>
                <div class="payment-grid">
                    <div class="payment-box">
                        <div class="method">🟠 Orange Money</div>
                        <div class="number">{NUMERO_ORANGE}</div>
                        <div class="name">Au nom de : {NOM_COMPTE}</div>
                    </div>
                    <div class="payment-box">
                        <div class="method">🟡 Mvola</div>
                        <div class="number">{NUMERO_MVOLA}</div>
                        <div class="name">Au nom de : {NOM_COMPTE}</div>
                    </div>
                </div>
                <div class="payment-warning">
                    ⏰ Clé non reçue après <b>15 minutes</b> ?<br>Appelez directement : <b>{NUMERO_MVOLA}</b>
                </div>
            </div>
            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Téléphone (Réception clé SMS) :</label>
            <input type="tel" name="tel" placeholder="034 00 000 00" required>
            <label>Référence de transaction :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <!-- ACTIVER -->
    <div class="card">
        <div class="card-title">🔐 ACTIVATION AVEC VOTRE CLÉ</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button>
        </form>
    </div>

    <!-- AVIS CLIENTS -->
    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS ({total_avis}) • Note : {avg_note}/5</div>
        <div class="rating-summary">
            <div class="rating-big">{avg_note}</div>
            <div style="text-align:center;">
                <div class="stars-gold" style="font-size:18px;">{"⭐" * int(round(avg_note))}</div>
                <div style="font-size:11px; font-weight:700; margin-top:2px;">Avis Vérifiés</div>
                <div style="color:var(--text-muted); font-size:10px;">Basé sur {total_avis} retours</div>
            </div>
        </div>
        <div>{reviews_html}</div>
        <hr>
        <div style="font-size:11px; font-weight:700; color:var(--accent-cyan); text-align:center; margin-bottom:6px;">✍️ LAISSEZ VOTRE AVIS</div>
        <form method="POST" action="/ajouter-avis">
            <div class="rating-input">
                <input type="radio" id="s5" name="etoiles" value="5" checked><label for="s5">★</label>
                <input type="radio" id="s4" name="etoiles" value="4"><label for="s4">★</label>
                <input type="radio" id="s3" name="etoiles" value="3"><label for="s3">★</label>
                <input type="radio" id="s2" name="etoiles" value="2"><label for="s2">★</label>
                <input type="radio" id="s1" name="etoiles" value="1"><label for="s1">★</label>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                <input type="text" name="nom" placeholder="Votre Nom" required>
                <input type="text" name="ville" placeholder="Votre Ville" required>
            </div>
            <textarea name="commentaire" placeholder="Partagez votre expérience..." rows="2" required style="margin-top:4px;"></textarea>
            <button type="submit" class="btn-primary" style="padding:10px; font-size:11px;">⭐ PUBLIER MON AVIS</button>
        </form>
    </div>

    <!-- FAQ -->
    <div class="card">
        <div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item">
            <div class="faq-question"><span>Est-ce que la configuration affecte mon débit Internet ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, au contraire !</b> Notre optimisation améliore votre débit. WireGuard consomme moins de <b>2% de bande passante</b>. Votre vitesse reste maximale grâce à l'optimisation TTL, DNS et au routage intelligent.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Le tunnel VPN a-t-il un abonnement mensuel ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, 100% gratuit à vie !</b> Cloudflare WARP est entièrement gratuit. Vous payez uniquement notre configuration une seule fois. Le VPN fonctionne pour toujours sans frais mensuel.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Configuration complète même après un RESET TOTAL ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Oui, absolument à 100% !</b> Notre script recrée tout de A à Z : Bridge, DHCP, NAT, IP, Wi-Fi avec mot de passe, Firewall Pro, Optimisation Réseau, VPN. Même sur un routeur vide et réinitialisé.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Puis-je choisir mon adresse IP ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-cyan);">Oui !</b> Dans le générateur, vous pouvez taper <b>n'importe quelle IP</b> (192.168.88.1, 10.0.0.1, 172.16.1.1...) ou cliquer sur une suggestion. Le DHCP et le sous-réseau s'adaptent automatiquement.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>1 clé = combien de routeurs ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-red);">1 clé = 1 seul routeur.</b> Après génération, la clé est définitivement consommée et verrouillée. Pour configurer un autre routeur, il faut acheter une nouvelle clé.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Combien de temps prend l'installation ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Moins de <b>5 secondes chrono</b> ! Une seule commande à coller dans Winbox Terminal et tout s'applique automatiquement.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Quels modèles MikroTik sont compatibles ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Compatible avec <b>tous les modèles RouterOS v7</b> : hAP ax2/ax3, hAP ac2/ac3, RB750/760/2011/3011/4011/1100, CCR1009/2004/2116, mANTBox, LHG, SXTsq, Chateau LTE/5G. Le script s'adapte à chaque modèle.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Comment payer et recevoir ma clé ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Paiement Mobile Money au nom de <b>{NOM_COMPTE}</b> :<br>🟠 Orange Money : <b>{NUMERO_ORANGE}</b><br>🟡 Mvola : <b>{NUMERO_MVOLA}</b><br>Votre clé est envoyée par SMS après validation (max 15 min).</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Que faire si ma clé n'arrive pas après 15 min ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Si vous ne recevez pas votre clé après <b>15 minutes</b> :<br>1. Appelez directement <b>{NUMERO_MVOLA}</b> ({NOM_COMPTE})<br>2. Écrivez-nous sur notre page <a href="{FB_LINK}" target="_blank" style="color:var(--accent-cyan); font-weight:bold;">Facebook Officielle</a><br>3. Cliquez sur le bouton WhatsApp vert en bas à droite</div>
        </div>
    </div>
    """
    return render(content)

@app.route("/tuto")
def tuto():
    content = f"""
    <div class="card">
        <div class="card-title">📖 GUIDE D'INSTALLATION MIKROTIK (PAS-À-PAS)</div>
        <p style="font-size:13px; color:var(--text-body); line-height:1.6;">
            Suivez ce guide simple avec schémas visuels pour brancher et configurer votre routeur MikroTik en moins de 2 minutes chrono.
        </p>

        <!-- ETAPE 1 : BRANCHEMENT VISUEL -->
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-cyan);">🔌 ÉTAPE 1 : LE BRANCHEMENT DES CÂBLES RÉSEAU</div>
            <ol>
                <li>Prenez le câble venant de votre antenne <b>Starlink / Box Internet</b> et branchez-le sur le <b>PORT 1 (ether1)</b>.</li>
                <li>Prenez un 2ème câble réseau et reliez votre <b>Ordinateur / Switch</b> sur les <b>PORTS 2 à 13</b>.</li>
                <li>Branchez l'alimentation du MikroTik.</li>
            </ol>
            
            <div class="visual-container">
                <div style="font-size:12px; font-weight:bold; color:#94a3b8; margin-bottom:6px;">📍 SCHÉMA DES PORTS SUR LE MIKROTIK :</div>
                <div class="ports-bar">
                    <div class="port-indicator wan">
                        <b>PORT 1</b>
                        <span>Starlink (WAN)</span>
                    </div>
                    <div class="port-indicator lan">
                        <b>PORT 2</b>
                        <span>PC / LAN</span>
                    </div>
                    <div class="port-indicator lan">
                        <b>PORT 3</b>
                        <span>Switch</span>
                    </div>
                    <div class="port-indicator lan">
                        <b>PORT 4</b>
                        <span>Access Point</span>
                    </div>
                    <div class="port-indicator lan">
                        <b>PORT 5</b>
                        <span>LAN</span>
                    </div>
                </div>
                <div style="font-size:11px; color:#a7f3d0; margin-top:8px;">
                    📶 Le <b>Wi-Fi Dual Band 2.4G & 5G</b> diffuse automatiquement dès l'injection du script !
                </div>
            </div>
        </div>

        <!-- ETAPE 2 : WINBOX VISUEL -->
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-purple);">💻 ÉTAPE 2 : OUVRIR WINBOX ET SE CONNECTER EN MAC</div>
            <ol>
                <li>Téléchargez Winbox officiel : <a href="https://mikrotik.com/download" target="_blank" style="color:var(--accent-cyan); font-weight:bold;">Télécharger Winbox (MikroTik)</a></li>
                <li>Ouvrez Winbox et cliquez sur l'onglet <b>Neighbors</b> (Voisins).</li>
                <li><b>Astuce Pro Cruciale :</b> Cliquez sur la ligne affichant l'<b>Adresse MAC</b> (ex: <code>CC:2D:E0:...</code>) et JAMAIS sur l'adresse IP !</li>
            </ol>

            <div class="winbox-mockup">
                <div class="winbox-top">
                    <span>Winbox v3.41 - Neighbors Table</span>
                    <span>_ □ ✕</span>
                </div>
                <div class="winbox-body">
                    <div style="color:#94a3b8; margin-bottom:6px;">IP Address | MAC Address | Identity | Board Name</div>
                    <div class="winbox-item">
                        <span>0.0.0.0</span>
                        <span>👉 CC:2D:E0:4F:92:1A (CLIQUEZ ICI !)</span>
                        <span>MikroTik</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ETAPE 3 : TERMINAL VISUEL -->
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-green);">⚡ ÉTAPE 3 : COLLER LA COMMANDE ET VALIDER</div>
            <ol>
                <li>Dans Winbox, cliquez sur le menu <b>New Terminal</b> dans la colonne de gauche.</li>
                <li>Générez votre configuration sur notre site, puis cliquez sur <b>📋 COPIER LA COMMANDE</b>.</li>
                <li>Dans la fenêtre noire du Terminal Winbox, faites <b>Clic Droit ➔ Paste (Coller)</b>.</li>
                <li>Appuyez sur la touche <b>Entrée</b> de votre clavier : en 5 secondes, l'installation se termine sans redémarrage !</li>
            </ol>

            <div class="terminal-box" style="margin-top:8px;">
                <span style="color:#94a3b8;">[admin@MikroTik] &gt; </span><span style="color:#38bdf8;">/system script add name=ketrika_run...</span><br>
                <span style="color:#4ade80;">=== KETRIKA MIKROTIK : INSTALLATION PRO DE A A Z TERMINEE ! ===</span>
            </div>
        </div>

        <div class="alert-warning" style="margin-top:15px; font-size:12px; line-height:1.6;">
            💡 <b>Vous voulez réinitialiser le routeur à zéro avant de commencer ?</b><br>
            Dans Winbox : Allez dans <b>System ➔ Reset Configuration</b> ➔ Cochez <b>No Default Configuration</b> ➔ Cliquez sur <b>Reset Configuration</b>. Notre script KETRIKA recréera tout de A à Z !
        </div>

        <div style="text-align:center; margin-top:20px;">
            <a href="/" class="btn-primary" style="display:inline-block; width:auto; padding:12px 25px;">🛒 COMMANDER UNE CLÉ OU ACTIVER MON ROUTEUR</a>
        </div>
    </div>
    """
    return render(content)

@app.route("/ajouter-avis", methods=["POST"])
def ajouter_avis():
    nom = request.form.get("nom", "").strip()
    ville = request.form.get("ville", "").strip()
    try:
        etoiles = int(request.form.get("etoiles", 5))
    except:
        etoiles = 5
    commentaire = request.form.get("commentaire", "").strip()
    if nom and commentaire:
        conn = sqlite3.connect("ketrika.db")
        c = conn.cursor()
        c.execute("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", (nom, ville, etoiles, commentaire, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
    return redirect(url_for("home"))

@app.route("/commander", methods=["POST"])
def commander():
    nom = request.form.get("nom")
    tel = request.form.get("tel")
    formule = request.form.get("formule")
    ref = request.form.get("ref_paiement")
    montant = TARIFS_MODULES.get(formule, {}).get("prix", 10000)
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)", (nom, tel, formule, montant, ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return render(f'<div class="card"><div class="alert alert-success"><b>✅ Commande enregistrée !</b></div><p style="font-size:13px; color:var(--text-body); line-height:1.6;">Merci <b>{nom}</b>.<br>Pack <b>{TARIFS_MODULES[formule]["nom"]}</b> ({montant:,} Ar).<br>Clé envoyée par SMS au <b>{tel}</b> sous 15 min max.<br><br>⏰ <b>Pas de clé après 15 min ? Appelez le {NUMERO_MVOLA}</b></p><a href="/" class="btn-primary">RETOUR</a></div>')

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé incorrecte ou expirée !</div><a href="/" class="btn-primary">Retour</a></div>')
    if result.get("utilisations", 0) >= 1:
        return render('<div class="card"><div class="alert alert-error">❌ Clé déjà consommée. 1 Clé = 1 Routeur.</div><a href="/" class="btn-primary">Retour</a></div>')
    session["authenticated"] = True
    session["licence"] = cle
    session["client"] = result["client"]
    session["type_abo"] = result["type"]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    cle = session.get("licence")
    result = verifier_licence(cle)
    if not result or result.get("utilisations", 0) >= 1:
        session.clear()
        return render('<div class="card"><div class="alert alert-error">❌ Clé déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    plan_key = session.get("type_abo", "basic")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["basic"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    ip_chips = "".join([f'<span class="ip-chip" onclick="setIP(\'{ip}\')">{ip}</span>' for ip in IP_SUGGESTIONS])
    feat_html = "<div>✅ Bridge + Ports auto-détectés</div><div>✅ Port 1 WAN (DHCP-Client)</div><div>✅ DHCP + NAT + IP personnalisée</div><div>✅ Firewall Stateful Pro</div><div>✅ Optimisation Réseau + DNS DoH</div>"
    dns_input_html = ""
    bandwidth_html = ""
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ WireGuard VPN (gratuit à vie)</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Hotspot Wi-Fi Zone</div>"
        dns_input_html = '<label>🔗 Adresse Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required>'
        
        bw_cards_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            ck = "checked" if k == "illimite" else ""
            active_class = "active" if k == "illimite" else ""
            bw_cards_html += f"""
            <div class="bw-card {active_class}" id="card_{k}" onclick="selectBW('{k}')">
                <input type="radio" name="bandwidth" id="bw_{k}" value="{k}" {ck}>
                <div class="bw-card-text">
                    <b>{v['nom']}</b>
                    <span>{v['desc']}</span>
                </div>
            </div>
            """
        
        bandwidth_html = f"""
        <div class="wifi-box" style="border-color:rgba(124,58,237,0.3); margin-top:10px;">
            <div style="font-size:11px; font-weight:800; color:var(--accent-purple); margin-bottom:6px;">📊 LIMITATION DU DÉBIT PAR CLIENT (CLIQUEZ SUR VOTRE CHOIX) :</div>
            <div class="bw-grid">
                {bw_cards_html}
            </div>
            <div id="custom-bw-box" style="display:none; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;">
                <input type="text" name="custom_down" value="3M" placeholder="Download (ex: 5M)">
                <input type="text" name="custom_up" value="1M" placeholder="Upload (ex: 2M)">
            </div>
        </div>
        """
        
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ PPPoE + QoS Bandwidth</div>"
        
    content = f"""
    <div class="top-nav" style="margin-bottom:10px;">
        <span class="badge">{plan_info['nom']} • 1 Clé = 1 Routeur</span>
        <a href="/logout" style="color:var(--accent-red); font-size:11px; text-decoration:none; font-weight:700;">Fermer Session</a>
    </div>
    <div class="card">
        <div class="card-title">⚙️ CONFIGURATION A à Z - {session['client']}</div>
        <div class="alert-warning">⚠️ Cette clé sera <b>définitivement consommée</b> après génération.</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Nom du client / Routeur :</label>
            <input type="text" name="client_final" placeholder="Boutique_Rasoa" required>

            <label>3. Adresse IP du Routeur (Champ libre) :</label>
            <input type="text" name="router_ip" id="router_ip" value="192.168.88.1" placeholder="Tapez votre IP ou cliquez ci-dessous" required>
            <div class="ip-suggestions">{ip_chips}</div>
            <small style="color:var(--text-muted); font-size:10px; display:block; margin-top:4px;">💡 Cliquez sur une IP suggérée ou tapez la vôtre. Le DHCP s'adapte automatiquement.</small>

            <div class="wifi-box">
                <div class="wifi-box-title">📶 WI-FI (SSID + MOT DE PASSE)</div>
                <label style="margin-top:0;">Nom du Wi-Fi (SSID) :</label>
                <input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe Wi-Fi :</label>
                <input type="text" name="wifi_pass" value="ketrika2025" required>
                {dns_input_html}
            </div>
            
            {bandwidth_html}
            
            <label>4. Fonctionnalités incluses :</label>
            <div class="feature-box">{feat_html}</div>
            <button type="submit" class="btn-primary">🚀 GÉNÉRER LA CONFIG A à Z</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    cle = session.get("licence")
    result = verifier_licence(cle)
    if not result or result.get("utilisations", 0) >= 1:
        session.clear()
        return render('<div class="card"><div class="alert alert-error">❌ Clé déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    modele = request.form.get("modele")
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
    
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("UPDATE licences SET actif=0, nb_utilisations=1 WHERE cle=?", (cle,))
    conn.commit()
    conn.close()
    session.clear()
    
    host = request.host_url.replace("http://", "https://")
    online_cmd = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    cfg = get_config_by_id(config_id)
    raw_s = build_raw_script(cfg)
    clean_s = clean_script_for_oneliner(raw_s)
    one_liner = f'/system script add name=ketrika_run source="{clean_s}"; /system script run ketrika_run; /system script remove ketrika_run'
    
    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Configuration A à Z prête pour : {client_final} ({modele})</b></div>
        <div class="alert-warning">
            📍 <b>Branchement Physique :</b> Câble Internet sur le <b>Port 1 (ether1)</b> | Ordinateur sur les <b>autres ports</b>.<br>
            📶 Wi-Fi : <b>{ssid}</b> | 🔑 Mot de passe : <b>{wifi_pass}</b> | 🌐 IP du Routeur : <b>{router_ip}</b><br>
            🔒 <i>Cette clé est maintenant définitivement consommée et verrouillée.</i>
        </div>

        <!-- METHODE 1 : ONE-LINER -->
        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE (RECOMMANDÉE &amp; ULTRA-RAPIDE)</div>
        <div class="step-guide">
            <b>📖 Mode d'emploi pas-à-pas :</b>
            <ol>
                <li>Ouvrez <b>Winbox</b> et connectez-vous sur votre MikroTik en cliquant sur l'<b>Adresse MAC</b> (onglet <i>Neighbors</i>).</li>
                <li>Cliquez sur <b>New Terminal</b> dans le menu de gauche.</li>
                <li>Cliquez sur le bouton violet ci-dessous pour copier la commande, puis <b>collez-la (Clic droit &gt; Paste)</b> dans le terminal.</li>
                <li>Appuyez sur la touche <b>Entrée</b> : en 5 secondes, le routeur applique toute la configuration sans redémarrer !</li>
            </ol>
        </div>
        <div class="terminal-box" id="cmd1">{one_liner}</div>
        <button class="btn-copy" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE UNIQUE</button>

        <hr>

        <!-- METHODE 2 : FICHIER .RSC ET TEXTE BRUT -->
        <div class="card-title">MÉTHODE 2 : FICHIER SCRIPT (.RSC) OU CODE BRUT COMPLET</div>
        <div class="step-guide">
            <b>📖 Mode d'emploi pas-à-pas :</b>
            <ol>
                <li>Téléchargez le fichier <b>ketrika.rsc</b> avec le bouton vert, OU copiez tout le texte brut ci-dessous.</li>
                <li>Dans Winbox, cliquez sur le menu <b>Files</b> à gauche, puis glissez-déposez le fichier <b>ketrika.rsc</b> dedans.</li>
                <li>Ouvrez <b>New Terminal</b> et tapez : <code>/import file-name=ketrika.rsc</code> puis Entrée.</li>
            </ol>
        </div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success" style="margin-top:10px;">📥 TÉLÉCHARGER LE FICHIER KETRIKA.RSC</a>
        
        <label style="margin-top:12px;">📄 OU COPIEZ LE SCRIPT BRUT MULTI-LIGNES CI-DESSOUS :</label>
        <textarea id="raw_script_box" style="height:140px; font-family:'Courier New', monospace; font-size:11px; background:#0f172a; color:#4ade80; border:1px solid #334155;" readonly>{raw_s}</textarea>
        <button class="btn-copy" id="b_raw" onclick="copyText('raw_script_box','b_raw')" style="background:#475569;">📋 COPIER LE SCRIPT BRUT COMPLET</button>

        <hr>

        <!-- METHODE 3 : IMPORTATION DIRECTE CLOUD -->
        <div class="card-title">MÉTHODE 3 : IMPORTATION DIRECTE (SI ROUTEUR DÉJÀ CONNECTÉ AU WEB)</div>
        <div class="step-guide">
            <b>📖 Mode d'emploi :</b> Si le port 1 de votre routeur a déjà accès à Internet, collez simplement cette commande dans le terminal Winbox :
        </div>
        <div class="terminal-box" id="cmd2">{online_cmd}</div>
        <button class="btn-copy" id="b2" onclick="copyText('cmd2','b2')" style="background:linear-gradient(135deg,#64748b,#475569);">📋 COPIER LA COMMANDE CLOUD</button>

        <a href="/" class="btn-primary" style="margin-top:18px;">🏠 TERMINER &amp; RETOUR À L'ACCUEIL</a>
    </div>
    """
    return render(content)

@app.route("/download/<config_id>.rsc")
def download_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg: return Response("Introuvable", mimetype="text/plain")
    mem = io.BytesIO()
    mem.write(build_raw_script(cfg).encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype="text/plain", as_attachment=True, download_name="ketrika.rsc")

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg: return Response("# Invalide", mimetype="text/plain")
    return Response(build_raw_script(cfg), mimetype="text/plain")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ADMIN</div><form method="POST"><input type="text" name="username" placeholder="admin" required><input type="password" name="password" placeholder="mot de passe" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC")
    cmds = c.fetchall()
    conn.close()
    rows = ""
    for cmd in cmds:
        rows += f'<tr><td><b>{cmd[1]}</b><br><small>{cmd[2]}</small></td><td>{cmd[3].upper()}<br><b>{cmd[4]:,} Ar</b></td><td><code>{cmd[5]}</code></td><td><form method="POST" action="/admin/valider/{cmd[0]}"><button type="submit" class="btn-primary" style="padding:4px 8px; font-size:10px; margin:0;">⚡ VALIDER</button></form></td></tr>'
    return render(f'<div class="card"><div class="card-title">📋 COMMANDES ({len(cmds)})</div><table style="width:100%; border-collapse:collapse; font-size:12px;"><tr><th style="text-align:left; padding:8px; border-bottom:1px solid var(--border-light); color:var(--accent-cyan);">Client</th><th style="text-align:left; padding:8px; border-bottom:1px solid var(--border-light); color:var(--accent-cyan);">Pack</th><th style="text-align:left; padding:8px; border-bottom:1px solid var(--border-light); color:var(--accent-cyan);">Réf</th><th style="text-align:left; padding:8px; border-bottom:1px solid var(--border-light); color:var(--accent-cyan);">Action</th></tr>{rows if rows else "<tr><td colspan=4 style=text-align:center;padding:15px;>Aucune commande</td></tr>"}</table><a href="/admin/creer" class="btn-primary" style="margin-top:12px;">➕ CRÉER CLÉ</a></div>')

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,))
    cmd = c.fetchone()
    if cmd:
        cle = creer_licence(cmd[1], cmd[2], cmd[3], cmd[4])
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id))
        conn.commit()
    conn.close()
    return render(f'<div class="card"><div class="alert alert-success">✅ Validé !</div><div class="card-title">CLÉ POUR {cmd[2]} :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">RETOUR</a></div>')

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"): return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée (1 usage unique) :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">Dashboard</a></div>')
    return render('<div class="card"><div class="card-title">Créer Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="basic">Basic (10k)</option><option value="standard">Standard (15k)</option><option value="warp">Premium (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>')

@app.errorhandler(500)
def server_error(e):
    return f"<h1>Erreur 500</h1><pre>{traceback.format_exc()}</pre>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
