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
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "desc": "Studio Total : Multi-WAN + PPPoE + QoS + Toutes Options", "badge": "STUDIO PRO"}
}

MODELES_MIKROTIK = [
    "hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)",
    "hAP ac2 (Dual Band Wireless)", "hAP ac3 (Dual Band Wireless)",
    "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (Wireless)", "LHG 5", "SXTsq", "hAP lite (Wireless 2.4G)",
    "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)",
    "CCR1009", "CCR2004", "CCR2116",
    "Chateau LTE/5G", "Autre RouterOS v7"
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
    <title>KETRIKA MIKROTIK STUDIO • Générateur RouterOS v7</title>
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
        .logo-wrapper { position: relative; width: 80px; height: 80px; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; }
        .logo-aura { position: absolute; inset: -3px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink)); filter: blur(8px); opacity: 0.7; }
        .logo-box { position: relative; width: 100%; height: 100%; border-radius: 50%; background: linear-gradient(135deg, #0f172a, #1e293b); border: 2px solid rgba(255,255,255,0.9); display: flex; align-items: center; justify-content: center; }
        .logo-box svg { width: 42px; height: 42px; }
        .header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 28px; font-weight: 900; background: linear-gradient(135deg, #0284c7, #7c3aed, #db2777, #059669); background-size: 300% 100%; -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; line-height: 1.2; }
        @media (min-width: 500px) { .header h1 { font-size: 34px; } }
        .header .tagline { color: var(--text-body); font-size: 13px; margin-top: 6px; font-weight: 600; }
        .stats-live { display: inline-flex; gap: 6px; margin-top: 10px; padding: 5px 12px; background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1px solid #a7f3d0; border-radius: 20px; font-size: 11px; color: var(--accent-green); font-weight: 700; align-items: center; }
        .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; display: inline-block; }

        /* CARDS */
        .card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; padding: 18px 16px; margin-bottom: 14px; box-shadow: 0 4px 15px rgba(15,23,42,0.05); position: relative; overflow: hidden; }
        @media (min-width: 500px) { .card { padding: 22px; } }
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink), var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 14px; color: var(--accent-cyan); margin-bottom: 12px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }
        @media (min-width: 500px) { .card-title { font-size: 15px; } }

        /* ACCORDÉONS STUDIO (MODULES DÉROULANTS) */
        .module-card {
            background: #f8fafc; border: 1px solid var(--border-light); border-radius: 12px;
            margin-bottom: 10px; overflow: hidden; transition: 0.3s;
        }
        .module-header {
            padding: 12px 14px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;
            background: linear-gradient(135deg, #f8fafc, #f1f5f9); font-weight: 800; font-size: 13px; font-family: 'Space Grotesk';
        }
        .module-header span { display: flex; align-items: center; gap: 8px; }
        .module-body { padding: 14px; display: none; background: #ffffff; border-top: 1px solid var(--border-light); }
        .module-card.open .module-body { display: block; }
        .module-card.open .module-arrow { transform: rotate(180deg); color: var(--accent-cyan); }
        .module-arrow { transition: 0.3s; font-size: 14px; }

        /* CHECKBOXES & TOGGLES */
        .toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-light); }
        .toggle-row:last-child { border-bottom: none; }
        .toggle-label { font-size: 12px; font-weight: 700; color: var(--text-dark); }
        .toggle-desc { font-size: 10px; color: var(--text-muted); }
        .switch-input { width: 20px !important; height: 20px !important; accent-color: var(--accent-cyan); margin: 0; cursor: pointer; }

        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input[type="text"], input[type="tel"], input[type="password"], input[type="number"], select, textarea { 
            width: 100%; padding: 12px 14px; margin-top: 4px; 
            background: #f8fafc; border: 1px solid var(--border-light); 
            border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit;
        }

        .ip-suggestions { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
        .ip-chip { background: linear-gradient(135deg, #e0f2fe, #f0f9ff); color: var(--accent-cyan); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; cursor: pointer; border: 1px solid #bae6fd; font-family: 'Courier New', monospace; }

        .btn-primary { width: 100%; padding: 14px; margin-top: 12px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 800; cursor: pointer; font-family: 'Space Grotesk'; text-transform: uppercase; text-decoration: none; display: block; text-align: center; }
        .btn-success { background: linear-gradient(135deg, #059669, #047857); }
        .btn-copy { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff; padding: 12px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase; margin-top: 8px; font-size: 12px; }
        .btn-copy.copied { background: linear-gradient(135deg, #059669, #047857); }

        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 6px; }
        .plan-option { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 2px solid var(--border-light); padding: 12px 10px; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; position: relative; gap: 8px; }
        .plan-option.selected, .plan-option:hover { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-option input[type="radio"] { width: 18px; height: 18px; accent-color: var(--accent-cyan); flex-shrink: 0; }
        .plan-info { flex: 1; min-width: 0; }
        .plan-info b { font-size: 13px; display: block; }
        .plan-info div { color: var(--text-muted); font-size: 10px; margin-top: 2px; }
        .plan-price { text-align: right; flex-shrink: 0; }
        .plan-price b { color: var(--accent-green); font-size: 14px; font-family: 'Space Grotesk'; white-space: nowrap; }
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

        .faq-item { border-bottom: 1px solid var(--border-light); padding: 10px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: var(--text-dark); font-size: 12px; cursor: pointer; display: flex; justify-content: space-between; gap: 6px; }
        .faq-answer { color: var(--text-body); font-size: 11px; line-height: 1.6; margin-top: 6px; display: none; background: #f8fafc; padding: 8px 10px; border-radius: 6px; }
        .faq-item.active .faq-answer { display: block; }

        .whatsapp-float { position: fixed; bottom: 18px; right: 18px; z-index: 9999; background: #25D366; color: #fff; padding: 10px 16px; border-radius: 30px; font-weight: 800; font-size: 12px; text-decoration: none; display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk'; box-shadow: 0 4px 15px rgba(37,211,102,0.4); }
        .footer { text-align: center; color: var(--text-muted); margin: 20px 0 70px; font-size: 10px; padding: 10px; border-top: 1px solid var(--border-light); }
        .footer a { color: var(--accent-cyan); text-decoration: none; font-weight: 700; }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">💬 <span>WhatsApp</span></a>

    <div class="container">
        <!-- TOP NAV -->
        <div class="top-nav">
            <a href="/" class="nav-brand">
                <div class="nav-logo-icon">⚡</div>
                <span>KETRIKA MIKROTIK STUDIO</span>
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
            <p class="tagline txt-fr">Générateur Modulaire de Configurations MikroTik RouterOS v7</p>
            <p class="tagline txt-mg" style="display:none;">Fitaovana matihanina hanamboarana ny MikroTik rehetra</p>
            <div class="stats-live"><span class="live-dot"></span><span>Studio Modulaire Pro • 1 Clé = 1 Routeur</span></div>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK STUDIO © 2026 • <a href="{{ fb_link }}" target="_blank">📘 Facebook Officiel</a> • <a href="/tuto">📖 Guide d'Installation</a><br>📞 038 28 171 00 (Jean Eric)
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
                btn.innerHTML = '✅ COPIÉ !'; 
                btn.classList.add('copied'); 
                setTimeout(() => { btn.innerHTML = o; btn.classList.remove('copied'); }, 2500); 
            }); 
        }
        function setIP(ip) { document.getElementById('router_ip').value = ip; }
        function toggleModule(id) { document.getElementById(id).classList.toggle('open'); }
        document.querySelectorAll('.faq-question').forEach(q => { q.addEventListener('click', () => q.parentElement.classList.toggle('active')); });
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
    
    router_ip = opt.get("router_ip", "192.168.88.1").strip()
    ssid = opt.get("ssid", "KETRIKA-NET")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    
    # Options Expertes Modulaires
    enable_load_balancing = opt.get("enable_load_balancing", False)
    enable_site_blocking = opt.get("enable_site_blocking", True)
    enable_auto_reboot = opt.get("enable_auto_reboot", True)
    enable_port_forward = opt.get("enable_port_forward", False)
    forward_port = opt.get("forward_port", "8080")
    forward_target = opt.get("forward_target", "192.168.88.200")
    
    dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0")
    bw_up = opt.get("bw_up", "0")

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

    # SCRIPT ROUTEROS V7 MODULAIRE COMPLET
    s = f"""# =========================================================================
# KETRIKA MIKROTIK STUDIO - CONFIGURATION TOTALE PERSONNALISÉE
# Modèle : {modele} | Formule : {plan.upper()} | Client : {cfg['client']}
# =========================================================================

# --- 1. BRIDGE & INTERFACES LAN ---
:if ([:len [/interface bridge find name=bridge-lan]] = 0) do={{ /interface bridge add name=bridge-lan auto-mac=yes comment="defconf-LAN" }}
:if ([:len [/interface list find name=WAN]] = 0) do={{ /interface list add name=WAN }}
:if ([:len [/interface list find name=LAN]] = 0) do={{ /interface list add name=LAN }}
/interface list member remove [find interface=ether1]
/interface list member add interface=ether1 list=WAN
/interface list member remove [find interface=bridge-lan]
/interface list member add interface=bridge-lan list=LAN

# Ajout dynamique des ports LAN existants (sauf ether1 et ether2 si Load Balancing)
:foreach i in=[/interface ethernet find where name!="ether1" {'and name!="ether2"' if enable_load_balancing else ''}] do={{
    :if ([:len [/interface bridge port find interface=$i]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$i comment="LAN-PORT" }}
}}

# --- 2. WAN & INTERNET ---
/ip dhcp-client remove [find interface=ether1]
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no use-peer-ntp=yes add-default-route=yes default-route-distance=1 comment="WAN-STARLINK-1"

# Option Load Balancing 2 Antennes Starlink (Port 1 + Port 2)
"""
    if enable_load_balancing:
        s += """/interface list member remove [find interface=ether2]
/interface list member add interface=ether2 list=WAN
/ip dhcp-client remove [find interface=ether2]
/ip dhcp-client add interface=ether2 disabled=no use-peer-dns=no use-peer-ntp=yes add-default-route=yes default-route-distance=2 comment="WAN-STARLINK-2"
/ip firewall nat add chain=srcnat out-interface=ether2 action=masquerade comment="NAT-WAN2"
"""

    s += f"""# --- 3. ADRESSAGE IP ET SERVEUR DHCP ---
/ip address remove [find interface=bridge-lan]
/ip address add address={router_ip}/24 interface=bridge-lan comment="LAN-IP"
/ip pool remove [find name=dhcp-pool]
/ip pool add name=dhcp-pool ranges={dhcp_pool_start}-{dhcp_pool_end}
/ip dhcp-server remove [find interface=bridge-lan]
/ip dhcp-server add name=dhcp-lan interface=bridge-lan address-pool=dhcp-pool disabled=no lease-time=12h
/ip dhcp-server network remove [find address={dhcp_net}]
/ip dhcp-server network add address={dhcp_net} gateway={router_ip} dns-server=1.1.1.1,1.0.0.1 comment="LAN-NET"

# --- 4. ACCÈS INTERNET (NAT) ---
/ip firewall nat remove [find comment="NAT-INTERNET"]
/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="NAT-INTERNET"

# --- 5. OPTIMISATION RÉSEAU (MANGLE TTL = 64) ---
/ip firewall mangle remove [find comment="STARLINK-TTL-64"]
/ip firewall mangle add chain=postrouting out-interface=ether1 action=change-ttl new-ttl=set:64 passthrough=yes comment="STARLINK-TTL-64"

# --- 6. DNS DO-H CLOUDFLARE 1.1.1.1 SÉCURISÉ ---
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
"""

    if enable_site_blocking:
        s += """# Filtrage de contenu & protection de la bande passante
/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-BLOCK-TORRENT-TCP"
/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-BLOCK-TORRENT-UDP"
"""

    if enable_port_forward:
        s += f"""# Redirection de port (Port Forwarding pour caméras/serveurs)
/ip firewall nat add chain=dstnat in-interface-list=WAN protocol=tcp dst-port={forward_port} action=dst-nat to-addresses={forward_target} to-ports={forward_port} comment="KETRIKA-PORT-FWD"
"""

    s += """/ipv6 settings set disable-ipv6=yes
/ip service disable telnet,ftp,api
"""

    # --- 8. WI-FI MODERNE / CLASSIQUE ---
    if is_wifi6:
        s += f"""# Configuration Wi-Fi 6 Moderne Wave2
/interface wifi security remove [find name=sec-wifi]
/interface wifi security add name=sec-wifi authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}"
/interface wifi configuration remove [find name=cfg-wifi]
/interface wifi configuration add name=cfg-wifi ssid="{ssid}" security=sec-wifi country="Madagascar"
/interface wifi set [find] configuration=cfg-wifi disabled=no
:foreach w in=[/interface wifi find] do={{ :if ([:len [/interface bridge port find interface=$w]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$w }} }}
"""
    elif is_wireless:
        s += f"""# Configuration Wi-Fi Classique n/ac
/interface wireless security-profiles remove [find name=sec-wifi]
/interface wireless security-profiles add name=sec-wifi mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}" unicast-ciphers=aes-ccm group-ciphers=aes-ccm
/interface wireless set [find] ssid="{ssid}" security-profile=sec-wifi country="madagascar" disabled=no
:foreach w in=[/interface wireless find] do={{ :if ([:len [/interface bridge port find interface=$w]] = 0) do={{ /interface bridge port add bridge=bridge-lan interface=$w }} }}
"""

    # --- 9. TUNNEL WIREGUARD VPN (PBR) ---
    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f"""# Tunnel WireGuard avec Routage Dédié PBR
:if ([:len [/routing table find name=to-warp]] = 0) do={{ /routing table add name=to-warp fib }}
/interface wireguard remove [find name=warp-vpn]
/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers remove [find interface=warp-vpn]
/interface wireguard peers add interface=warp-vpn public-key="{cfg['warp_public']}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address remove [find interface=warp-vpn]
/ip address add address={cfg['warp_ip']}/32 interface=warp-vpn
/ip firewall nat remove [find comment="WARP-NAT"]
/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade comment="WARP-NAT"
/ip route remove [find comment="VPN-PBR-ROUTE"]
/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn routing-table=to-warp comment="VPN-PBR-ROUTE"
/ip firewall mangle remove [find comment="MARK-ROUTING-WARP"]
/ip firewall mangle add chain=prerouting in-interface-list=LAN action=mark-routing new-routing-mark=to-warp passthrough=yes comment="MARK-ROUTING-WARP"
"""

    # --- 10. HOTSPOT WI-FI ZONE ---
    if plan in ["hotspot", "pro"]:
        s += f"""# Serveur Hotspot Wi-Fi Zone
/ip hotspot profile remove [find name=hs-prof]
/ip hotspot profile add name=hs-prof hotspot-address={router_ip} dns-name={dns_name}
/ip hotspot user profile remove [find name=hs-user]
/ip hotspot user profile add name=hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot remove [find name=hotspot-ketrika]
/ip hotspot add name=hotspot-ketrika interface=bridge-lan address-pool=dhcp-pool profile=hs-prof disabled=no
"""

    # --- 11. PPPOE & QOS ---
    if plan == "pro":
        s += f"""# Serveur PPPoE et Gestion de Bande Passante QoS
/ip pool remove [find name=pppoe-pool]
/ip pool add name=pppoe-pool ranges=10.10.10.2-10.10.10.254
/ppp profile remove [find name=prof-pppoe]
/ppp profile add name=prof-pppoe local-address=10.10.10.1 remote-address=pppoe-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"
/interface pppoe-server server remove [find service-name=PPPOE-KETRIKA]
/interface pppoe-server server add service-name=PPPOE-KETRIKA interface=bridge-lan default-profile=prof-pppoe disabled=no
"""

    # --- 12. MAINTENANCE ET REBOOT AUTOMATIQUE ---
    if enable_auto_reboot:
        s += """# Redémarrage automatique quotidien à 04h00 du matin (Nettoyage RAM)
/system scheduler remove [find name="KETRIKA-AUTO-REBOOT"]
/system scheduler add name="KETRIKA-AUTO-REBOOT" start-time=04:00:00 interval=1d on-event="/system reboot" comment="AUTO-REBOOT"
"""

    s += f"""/system identity set name="KETRIKA-{cfg['client']}"
:put "==========================================================="
:put "  KETRIKA MIKROTIK STUDIO : CONFIG APPLIQUEE AVEC SUCCES ! "
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
        reviews_html += f'<div class="review-card"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><b style="font-size:12px;">{a[0]} <span style="color:var(--text-muted); font-size:10px;">({a[1] or "MG"})</span></b><span class="stars-gold">{"⭐" * a[2]}</span></div><div style="font-size:11px; color:var(--text-body);">"{a[3]}"</div></div>'
    
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
    <!-- HERO -->
    <div class="card" style="background:linear-gradient(135deg, #0284c7, #7c3aed); color:#fff;">
        <h2 style="font-family:'Space Grotesk'; font-size:20px; font-weight:900; margin-bottom:8px;">🚀 Studio de Configuration MikroTik RouterOS v7</h2>
        <p style="font-size:13px; opacity:0.95; line-height:1.6;">
            Activez et combinez <b>toutes les options avancées de votre MikroTik</b> en quelques clics : Multi-WAN Load Balancing, Wi-Fi 6 Dual Band, Pare-feu d'entreprise, Hotspot, VPN et Redirection de ports.
        </p>
    </div>

    <!-- COMMANDER -->
    <div class="card">
        <div class="card-title">🛒 1. CHOISIR VOTRE FORMULE STUDIO</div>
        <div class="alert-warning">⚠️ <b>1 Clé = 1 Routeur uniquement.</b> Accès complet à toutes les options du pack.</div>
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
                <div class="payment-warning">⏰ Clé non reçue après <b>15 minutes</b> ? Appelez : <b>{NUMERO_MVOLA}</b></div>
            </div>
            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Téléphone (Réception clé SMS) :</label>
            <input type="tel" name="tel" placeholder="034 00 000 00" required>
            <label>Référence transaction SMS :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <!-- ACTIVER -->
    <div class="card">
        <div class="card-title">🔐 2. DÉJÀ UNE CLÉ ? OUVREZ LE STUDIO</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">OUVRIR LE STUDIO MIKROTIK</button>
        </form>
    </div>

    <!-- AVIS -->
    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS ({total_avis}) • Note : {avg_note}/5</div>
        <div class="rating-summary">
            <div class="rating-big">{avg_note}</div>
            <div style="text-align:center;">
                <div class="stars-gold" style="font-size:18px;">{"⭐" * int(round(avg_note))}</div>
                <div style="font-size:11px; font-weight:700; margin-top:2px;">Avis Vérifiés</div>
            </div>
        </div>
        <div>{reviews_html}</div>
    </div>
    """
    return render(content)

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
    
    content = f"""
    <div class="top-nav" style="margin-bottom:10px;">
        <span class="badge">{plan_info['nom']} • Studio RouterOS v7</span>
        <a href="/logout" style="color:var(--accent-red); font-size:11px; text-decoration:none; font-weight:700;">Fermer</a>
    </div>

    <div class="card">
        <div class="card-title">🎛️ STUDIO DE CONFIGURATION MIKROTIK - {session['client']}</div>
        <div class="alert-warning">⚙️ Cochez et personnalisez les modules ci-dessous selon votre architecture réseau :</div>
        
        <form method="POST" action="/generate">
            
            <!-- MODULE 1 : BASE & MATÉRIEL -->
            <div class="module-card open" id="mod_base">
                <div class="module-header" onclick="toggleModule('mod_base')">
                    <span>🔌 1. Matériel & IP Locale</span>
                    <span class="module-arrow">▼</span>
                </div>
                <div class="module-body">
                    <label>Modèle MikroTik :</label>
                    <select name="modele" required>{modeles_opt}</select>

                    <label>Nom du Routeur (Identity) :</label>
                    <input type="text" name="client_final" placeholder="Ex: Bureau_Central" required>

                    <label>Adresse IP Locale du Routeur :</label>
                    <input type="text" name="router_ip" id="router_ip" value="192.168.88.1" required>
                    <div class="ip-suggestions">{ip_chips}</div>
                </div>
            </div>

            <!-- MODULE 2 : WI-FI DUAL-BAND -->
            <div class="module-card open" id="mod_wifi">
                <div class="module-header" onclick="toggleModule('mod_wifi')">
                    <span>📶 2. Paramètres Wi-Fi (2.4G & 5G)</span>
                    <span class="module-arrow">▼</span>
                </div>
                <div class="module-body">
                    <label>Nom du Réseau Wi-Fi (SSID) :</label>
                    <input type="text" name="ssid" value="KETRIKA-NET" required>
                    <label>Mot de passe Wi-Fi :</label>
                    <input type="text" name="wifi_pass" value="ketrika2025" required>
                </div>
            </div>

            <!-- MODULE 3 : WAN & MULTI-WAN LOAD BALANCING -->
            <div class="module-card" id="mod_wan">
                <div class="module-header" onclick="toggleModule('mod_wan')">
                    <span>🌐 3. Multi-WAN & Load Balancing</span>
                    <span class="module-arrow">▼</span>
                </div>
                <div class="module-body">
                    <div class="toggle-row">
                        <div>
                            <div class="toggle-label">Load Balancing 2 Antennes Starlink (Port 1 + Port 2)</div>
                            <div class="toggle-desc">Combine 2 connexions WAN pour doubler le débit</div>
                        </div>
                        <input type="checkbox" name="enable_load_balancing" class="switch-input">
                    </div>
                </div>
            </div>

            <!-- MODULE 4 : SÉCURITÉ & CONTRÔLE DE CONTENU -->
            <div class="module-card" id="mod_sec">
                <div class="module-header" onclick="toggleModule('mod_sec')">
                    <span>🛡️ 4. Sécurité, Filtres & Redirection</span>
                    <span class="module-arrow">▼</span>
                </div>
                <div class="module-body">
                    <div class="toggle-row">
                        <div>
                            <div class="toggle-label">Bloquer Torrent / P2P</div>
                            <div class="toggle-desc">Empêche la saturation de la bande passante</div>
                        </div>
                        <input type="checkbox" name="enable_site_blocking" class="switch-input" checked>
                    </div>

                    <div class="toggle-row">
                        <div>
                            <div class="toggle-label">Redirection de Port (Port Forwarding)</div>
                            <div class="toggle-desc">Accès distant pour Caméras IP ou Serveur local</div>
                        </div>
                        <input type="checkbox" name="enable_port_forward" class="switch-input" onchange="document.getElementById('p_fwd_box').style.display = this.checked ? 'grid' : 'none';">
                    </div>

                    <div id="p_fwd_box" style="display:none; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;">
                        <input type="text" name="forward_port" value="8080" placeholder="Port externe (ex: 8080)">
                        <input type="text" name="forward_target" value="192.168.88.200" placeholder="IP cible (ex: 192.168.88.200)">
                    </div>
                </div>
            </div>

            <!-- MODULE 5 : WI-FI ZONE HOTSPOT -->
            {'<div class="module-card open" id="mod_hs"><div class="module-header" onclick="toggleModule(\'mod_hs\')"><span>🎫 5. Portail Captif Hotspot</span><span class="module-arrow">▼</span></div><div class="module-body"><label>Adresse DNS Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required><label>Limite Débit / Utilisateur :</label><select name="bandwidth"><option value="illimite">⚡ Illimité (Plein Débit)</option><option value="ultra">🚀 Ultra (10M / 5M)</option><option value="rapide" selected>⭐ Rapide (5M / 2M)</option><option value="standard">📶 Standard (2M / 1M)</option><option value="eco">🔒 Éco (1M / 512k)</option></select></div></div>' if plan_key in ["hotspot", "pro"] else ''}

            <!-- MODULE 6 : MAINTENANCE & REBOOT -->
            <div class="module-card" id="mod_maint">
                <div class="module-header" onclick="toggleModule('mod_maint')">
                    <span>⚙️ 6. Maintenance Automatique</span>
                    <span class="module-arrow">▼</span>
                </div>
                <div class="module-body">
                    <div class="toggle-row">
                        <div>
                            <div class="toggle-label">Reboot Automatique Quotidien (04h00 du matin)</div>
                            <div class="toggle-desc">Vide la mémoire RAM et évite les ralentissements</div>
                        </div>
                        <input type="checkbox" name="enable_auto_reboot" class="switch-input" checked>
                    </div>
                </div>
            </div>

            <button type="submit" class="btn-primary" style="margin-top:15px;">🚀 GÉNÉRER LA CONFIGURATION STUDIO</button>
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
    router_ip = request.form.get("router_ip", "192.168.88.1")
    
    options = {
        "ssid": ssid,
        "wifi_pass": wifi_pass,
        "router_ip": router_ip,
        "enable_load_balancing": request.form.get("enable_load_balancing") == "on",
        "enable_site_blocking": request.form.get("enable_site_blocking") == "on",
        "enable_auto_reboot": request.form.get("enable_auto_reboot") == "on",
        "enable_port_forward": request.form.get("enable_port_forward") == "on",
        "forward_port": request.form.get("forward_port", "8080"),
        "forward_target": request.form.get("forward_target", "192.168.88.200"),
        "dns_name": request.form.get("dns_name", "wifizone.wifi"),
        "bw_down": BANDWIDTH_PROFILES.get(request.form.get("bandwidth", "illimite"), {}).get("down", "0"),
        "bw_up": BANDWIDTH_PROFILES.get(request.form.get("bandwidth", "illimite"), {}).get("up", "0")
    }
    
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
        <div class="alert alert-success"><b>✅ Configuration Studio prête pour : {client_final} ({modele})</b></div>
        <div class="alert-warning">
            📍 <b>Branchement :</b> WAN sur <b>Port 1 {'et Port 2 (Load Balancing)' if options['enable_load_balancing'] else ''}</b> | LAN sur <b>autres ports</b><br>
            📶 Wi-Fi : <b>{ssid}</b> | 🔑 Mot de passe : <b>{wifi_pass}</b> | 🌐 IP : <b>{router_ip}</b><br>
            🔒 <i>Clé définitivement consommée.</i>
        </div>

        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE (RECOMMANDÉE)</div>
        <div class="terminal-box" id="cmd1">{one_liner}</div>
        <button class="btn-copy" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE</button>
        <hr>
        <div class="card-title">MÉTHODE 2 : FICHIER .RSC</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER LE FICHIER</a>
        <hr>
        <div class="card-title">MÉTHODE 3 : SI ROUTEUR DÉJÀ EN LIGNE</div>
        <div class="terminal-box" id="cmd2">{online_cmd}</div>
        <button class="btn-copy" id="b2" onclick="copyText('cmd2','b2')" style="background:#64748b;">📋 COPIER</button>
        <a href="/" class="btn-primary" style="margin-top:14px;">🏠 RETOUR À L'ACCUEIL</a>
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

@app.route("/tuto")
def tuto():
    content = f"""
    <div class="card">
        <div class="card-title">📖 GUIDE D'INSTALLATION MIKROTIK STUDIO</div>
        <p style="font-size:13px; color:var(--text-body); line-height:1.6;">
            Suivez ce guide simple pour brancher et injecter votre configuration personnalisée en 2 minutes.
        </p>
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-cyan);">🔌 ÉTAPE 1 : BRANCHEMENT</div>
            <ol>
                <li>Starlink / WAN 1 sur <b>PORT 1 (ether1)</b>.</li>
                <li>Si Load Balancing 2ème Starlink activé : branchez la 2ème antenne sur <b>PORT 2 (ether2)</b>.</li>
                <li>Votre Ordinateur ou Switch sur n'importe quel autre port.</li>
            </ol>
        </div>
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-purple);">💻 ÉTAPE 2 : CONNEXION WINBOX</div>
            <ol>
                <li>Ouvrez Winbox, allez dans l'onglet <b>Neighbors</b>.</li>
                <li>Cliquez sur l'<b>Adresse MAC</b> (ex: CC:2D:E0:...) pour vous connecter sans déconnexion.</li>
            </ol>
        </div>
        <div class="step-guide" style="margin-top:15px;">
            <div style="font-size:13px; font-weight:800; color:var(--accent-green);">⚡ ÉTAPE 3 : INJECTION DU SCRIPT</div>
            <ol>
                <li>Ouvrez <b>New Terminal</b> dans Winbox.</li>
                <li>Faites <b>Clic droit &gt; Paste (Coller)</b> et appuyez sur Entrée. Configuration terminée en 5s !</li>
            </ol>
        </div>
        <div style="text-align:center; margin-top:20px;">
            <a href="/" class="btn-primary" style="display:inline-block; width:auto; padding:12px 25px;">🛒 COMMANDER OU ACTIVER MON ROUTEUR</a>
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

@app.errorhandler(500)
def server_error(e):
    return f"<h1>Erreur 500</h1><pre>{traceback.format_exc()}</pre>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
