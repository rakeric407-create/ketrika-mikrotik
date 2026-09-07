from flask import Flask, request, Response, render_template_string, session, redirect, url_for, send_file
from database import *
from warp_api import creer_config_warp_complete
import sqlite3
import secrets
import string
import random
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

init_db()

def init_extra_tables():
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_nom TEXT, telephone TEXT, formule TEXT, montant REAL,
        reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE',
        cle_generee TEXT, date_commande TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS avis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL, ville TEXT,
        etoiles INTEGER NOT NULL, commentaire TEXT NOT NULL,
        date_avis TEXT
    )''')
    c.execute("SELECT COUNT(*) FROM avis")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)",
                  ("Mamy R.", "Antananarivo", 5, "Script injecté en 3 secondes sur hAP ax2. Fonctionne parfaitement !", "2026-01-15"))
    conn.commit()
    conn.close()

init_extra_tables()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "desc": "Anti-Bridage TTL + DNS Sécurisé", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Blindé VPN", "prix": 20000, "desc": "Standard + Tunnel WireGuard 100% gratuit", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "desc": "Blindé + Portail Hotspot + Débit contrôlé", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "desc": "Solution intégrale + PPPoE + QoS", "badge": "PRO"}
}

MODELES_MIKROTIK = [
    "hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)",
    "hAP ac2 (Dual Band)", "hAP ac3 (Dual Band)",
    "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s", "LHG 5", "SXTsq", "hAP lite",
    "RB750Gr3 (hEX)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)",
    "CCR1009", "CCR2004", "CCR2116",
    "Chateau LTE/5G", "Autre RouterOS v7"
]

BANDWIDTH_PROFILES = {
    "illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Plein débit"},
    "ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10 ↓ / 5 ↑"},
    "rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5 ↓ / 2 ↑"},
    "standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2 ↓ / 1 ↑"},
    "eco": {"nom": "🔒 ÉCO (1M/512K)", "down": "1M", "up": "512k", "desc": "1 ↓ / 0.5 ↑"},
    "custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Personnalisé"}
}

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #f0f4f8;
            --bg-card: #ffffff;
            --bg-dark-section: #1e293b;
            --accent-cyan: #0891b2;
            --accent-green: #059669;
            --accent-purple: #7c3aed;
            --accent-orange: #d97706;
            --accent-gold: #f59e0b;
            --accent-pink: #db2777;
            --accent-red: #dc2626;
            --text-dark: #1e293b;
            --text-body: #334155;
            --text-muted: #64748b;
            --text-light: #94a3b8;
            --border-light: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        @keyframes pulse-glow { 0%, 100% { box-shadow: 0 0 15px rgba(8, 145, 178, 0.3); } 50% { box-shadow: 0 0 25px rgba(8, 145, 178, 0.6); } }
        @keyframes border-flow { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
        @keyframes slide-in { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes badge-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        @keyframes float-particle { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
        
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg-main); 
            color: var(--text-dark); 
            min-height: 100vh; padding: 12px;
        }
        
        .container { max-width: 830px; margin: auto; animation: slide-in 0.5s ease-out; }
        
        /* TOP NAV */
        .top-nav {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 14px; padding: 10px 16px; 
            background: var(--bg-card);
            border: 1px solid var(--border-light); 
            border-radius: 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }
        .lang-btn {
            background: linear-gradient(135deg, #e0f2fe, #ede9fe); 
            color: var(--accent-cyan); border: 1px solid #bae6fd;
            padding: 5px 12px; border-radius: 15px; font-size: 11px; font-weight: 700; cursor: pointer;
        }
        
        /* HEADER */
        .header { text-align: center; padding: 20px 0 25px; }
        .header h1 { 
            font-family: 'Space Grotesk', sans-serif; font-size: 34px; font-weight: 900; 
            background: linear-gradient(135deg, #0891b2, #7c3aed, #059669); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
            letter-spacing: 2px; text-transform: uppercase;
        }
        .header .tagline { color: var(--text-muted); font-size: 14px; margin-top: 6px; }
        .header .stats-live { 
            display: inline-flex; gap: 8px; margin-top: 12px; padding: 6px 14px; 
            background: #ecfdf5; border: 1px solid #a7f3d0; 
            border-radius: 20px; font-size: 11px; color: var(--accent-green); font-weight: 600;
        }
        .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; box-shadow: 0 0 8px var(--accent-green); display: inline-block; }
        
        /* CARDS */
        .card { 
            background: var(--bg-card); 
            border: 1px solid var(--border-light); 
            border-radius: 16px; padding: 22px; margin-bottom: 16px; 
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
            position: relative; overflow: hidden;
            transition: all 0.3s ease;
        }
        .card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-green));
        }
        .card:hover { box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); transform: translateY(-2px); }
        
        .card-title { 
            font-family: 'Space Grotesk', sans-serif; font-size: 15px; color: var(--accent-cyan); 
            margin-bottom: 14px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;
            display: flex; align-items: center; gap: 8px;
        }

        /* AVANTAGES */
        .advantages-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        @media (max-width: 600px) { .advantages-grid { grid-template-columns: repeat(2, 1fr); } }
        .adv-box { 
            background: linear-gradient(135deg, #f0f9ff, #f5f3ff); 
            padding: 16px 10px; border-radius: 12px; text-align: center; 
            border: 1px solid var(--border-light); transition: all 0.3s ease;
        }
        .adv-box:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(8, 145, 178, 0.15); border-color: var(--accent-cyan); }
        .adv-icon { font-size: 28px; display: block; margin-bottom: 6px; }
        .adv-title { font-family: 'Space Grotesk'; font-size: 12px; color: var(--text-dark); font-weight: 700; }
        .adv-desc { font-size: 10px; color: var(--text-muted); margin-top: 3px; line-height: 1.3; }
        
        /* ÉTAPES */
        .steps-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }
        @media (max-width: 600px) { .steps-grid { grid-template-columns: 1fr; } }
        .step-box {
            background: linear-gradient(135deg, #f0fdfa, #eff6ff);
            border: 1px solid #bae6fd; padding: 16px; border-radius: 12px; text-align: center;
        }
        .step-num {
            width: 34px; height: 34px; margin: 0 auto 8px; 
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-family: 'Space Grotesk'; font-weight: 900; font-size: 16px;
        }
        .step-title { font-family: 'Space Grotesk'; font-size: 13px; color: var(--text-dark); font-weight: 700; margin-bottom: 4px; }
        .step-desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; }

        /* INPUTS */
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        input, select, textarea { 
            width: 100%; padding: 12px 14px; margin-top: 5px; 
            background: #f8fafc; border: 1px solid var(--border-light); 
            border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit; transition: 0.3s;
        }
        input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent-cyan); box-shadow: 0 0 10px rgba(8, 145, 178, 0.15); background: #fff; }

        /* BOUTONS */
        .btn-primary { 
            width: 100%; padding: 14px; margin-top: 15px; 
            background: linear-gradient(135deg, #0891b2, #0e7490); 
            color: #fff; border: none; border-radius: 10px; 
            font-size: 14px; font-weight: 800; cursor: pointer; 
            font-family: 'Space Grotesk'; letter-spacing: 0.5px; text-transform: uppercase;
            text-decoration: none; display: inline-block; text-align: center;
            position: relative; overflow: hidden; transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
        }
        .btn-primary::before {
            content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.6s ease;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(8, 145, 178, 0.4); }
        .btn-primary:hover::before { left: 200%; }
        .btn-success { background: linear-gradient(135deg, #059669, #047857); box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3); }
        .btn-success:hover { box-shadow: 0 8px 20px rgba(5, 150, 105, 0.4); }
        
        .btn-copy {
            background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff;
            padding: 12px; border-radius: 10px; border: none; font-weight: 700;
            cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase;
            margin-top: 8px; font-size: 12px; transition: 0.3s;
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        }
        .btn-copy:hover { transform: translateY(-2px); }
        .btn-copy.copied { background: linear-gradient(135deg, #059669, #047857); }

        /* PLANS */
        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 8px; }
        .plan-option { 
            background: #f8fafc; border: 2px solid var(--border-light); 
            padding: 14px 16px; border-radius: 12px; cursor: pointer; 
            display: flex; justify-content: space-between; align-items: center; 
            transition: all 0.3s ease; position: relative; overflow: hidden;
        }
        .plan-option:hover { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-option input { width: 18px; height: 18px; accent-color: var(--accent-cyan); }
        .plan-badge {
            position: absolute; top: -1px; right: 14px;
            padding: 3px 10px; border-radius: 0 0 8px 8px;
            font-size: 9px; font-weight: 800; letter-spacing: 0.5px; font-family: 'Space Grotesk';
            color: #fff; animation: badge-pulse 2s infinite;
        }
        .badge-popular { background: linear-gradient(135deg, #f59e0b, #ea580c); }
        .badge-best { background: linear-gradient(135deg, #db2777, #7c3aed); }
        .badge-pro { background: linear-gradient(135deg, #059669, #047857); }

        /* PAYMENT */
        .payment-banner { 
            background: linear-gradient(135deg, #fffbeb, #fef3c7); 
            border: 1px solid #fde68a; border-radius: 12px; 
            padding: 16px; margin-top: 14px; text-align: center;
        }
        .payment-phone { 
            font-family: 'Space Grotesk'; font-size: 28px; color: #b45309; 
            margin: 6px 0; font-weight: 900; letter-spacing: 2px; 
        }

        /* TERMINAL */
        .terminal-box { 
            background: #1e293b; border: 1px solid #334155; 
            color: #4ade80; padding: 14px; border-radius: 10px; 
            font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 8px;
        }

        .badge { background: #e0f2fe; color: var(--accent-cyan); padding: 5px 12px; border-radius: 15px; font-size: 11px; font-weight: 700; border: 1px solid #bae6fd; }
        .alert { padding: 12px 15px; border-radius: 10px; margin-bottom: 12px; font-size: 13px; line-height: 1.5; }
        .alert-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
        .alert-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }

        /* ÉTOILES */
        .rating-summary {
            display: flex; align-items: center; justify-content: center; gap: 15px;
            padding: 14px; background: linear-gradient(135deg, #fffbeb, #fef9c3);
            border: 1px solid #fde68a; border-radius: 12px; margin-bottom: 12px;
        }
        .rating-big { font-family: 'Space Grotesk'; font-size: 38px; font-weight: 900; color: #b45309; }
        
        .rating-input {
            display: flex; flex-direction: row-reverse; justify-content: center; gap: 6px; margin: 12px 0;
        }
        .rating-input input { display: none; }
        .rating-input label {
            font-size: 32px; color: #d1d5db; cursor: pointer; transition: 0.2s; margin: 0; padding: 0 2px;
        }
        .rating-input label:hover,
        .rating-input label:hover ~ label,
        .rating-input input:checked ~ label {
            color: var(--accent-gold);
            transform: scale(1.15);
        }

        .reviews-scroll {
            max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-top: 10px;
        }
        .reviews-scroll::-webkit-scrollbar { width: 6px; }
        .reviews-scroll::-webkit-scrollbar-thumb { background: var(--accent-cyan); border-radius: 10px; }
        .review-card { 
            background: #f8fafc; padding: 12px; border-radius: 10px; border: 1px solid var(--border-light);
        }
        .review-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .stars-gold { color: var(--accent-gold); font-size: 12px; letter-spacing: 2px; }

        /* FAQ */
        .faq-item { border-bottom: 1px solid var(--border-light); padding: 12px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: var(--text-dark); font-size: 13px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .faq-answer { color: var(--text-body); font-size: 12px; line-height: 1.7; margin-top: 8px; display: none; background: #f8fafc; padding: 12px; border-radius: 8px; }
        .faq-item.active .faq-answer { display: block; animation: slide-in 0.3s; }
        .faq-toggle { color: var(--accent-cyan); font-size: 18px; transition: 0.3s; }
        .faq-item.active .faq-toggle { transform: rotate(180deg); }

        /* WHATSAPP */
        .whatsapp-float {
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            background: linear-gradient(135deg, #25D366, #128C7E); color: #fff;
            padding: 12px 18px; border-radius: 30px; font-weight: 800; font-size: 13px;
            box-shadow: 0 8px 25px rgba(37, 211, 102, 0.4); text-decoration: none;
            display: flex; align-items: center; gap: 8px; font-family: 'Space Grotesk';
            transition: 0.3s;
        }
        .whatsapp-float:hover { transform: scale(1.08) translateY(-2px); }

        .wifi-box { background: #f0f9ff; border: 1px dashed #7dd3fc; padding: 14px; border-radius: 12px; margin-top: 10px; }
        .feature-box { background: #f0fdf4; padding: 12px; border-radius: 10px; margin-top: 8px; line-height: 2; font-size: 12px; border-left: 4px solid var(--accent-green); color: var(--text-body); }

        table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
        table th, table td { padding: 10px; border-bottom: 1px solid var(--border-light); text-align: left; }
        table th { color: var(--accent-cyan); font-family: 'Space Grotesk'; font-weight: 700; background: #f8fafc; }
        
        .footer { 
            text-align: center; color: var(--text-muted); 
            margin: 25px 0 15px; font-size: 11px; 
            padding: 12px; border-top: 1px solid var(--border-light);
        }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">
        💬 <span>Assistance</span>
    </a>

    <div class="container">
        <div class="top-nav">
            <span style="font-size:11px; color:var(--text-muted); display:flex; align-items:center; gap:6px;">
                <span class="live-dot"></span> KETRIKA OS v3.1 • Madagascar
            </span>
            <button class="lang-btn" onclick="toggleLang()">🇲🇬 MG / 🇫🇷 FR</button>
        </div>

        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p class="tagline txt-fr">Système Professionnel d'Optimisation Réseau MikroTik</p>
            <p class="tagline txt-mg" style="display:none;">Fitaovana matihanina hanatsarana ny MikroTik</p>
            <div class="stats-live">
                <span class="live-dot"></span>
                <span>🔥 Configuration en 5 secondes • Support 7j/7</span>
            </div>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • Ingénierie Réseau Avancée • Support : 038 28 171 00
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
            const text = document.getElementById(elemId).innerText;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.getElementById(btnId);
                const original = btn.innerHTML;
                btn.innerHTML = '✅ COPIÉ !';
                btn.classList.add('copied');
                setTimeout(() => { btn.innerHTML = original; btn.classList.remove('copied'); }, 2500);
            });
        }

        document.querySelectorAll('.faq-question').forEach(q => {
            q.addEventListener('click', () => q.parentElement.classList.toggle('active'));
        });
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content)

def build_raw_script(cfg):
    plan = cfg["type"]
    opt = cfg.get("options", {})
    ssid = opt.get("ssid", "KETRIKA-NET")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0")
    bw_up = opt.get("bw_up", "0")
    
    s = f"# KETRIKA MIKROTIK - {cfg['client']} ({cfg['modele']})\n# Formule : {plan.upper()}\n"
    s += '/ip firewall mangle remove [find comment="KETRIKA-TTL"]\n/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"\n'
    s += '/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes\n/ip firewall nat remove [find comment="KETRIKA-DNS"]\n/ip firewall nat add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n'
    s += '/ipv6 settings set disable-ipv6=yes\n'
    s += '/ip firewall filter remove [find comment="KETRIKA-P2P"]\n/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P"\n'
    
    if plan == "basic":
        s += f"""
:do {{ /interface wifi set [find] configuration.ssid="{ssid}" disabled=no }} on-error={{}};
:do {{ /interface wireless set [find] ssid="{ssid}" disabled=no }} on-error={{}};
"""
    else:
        s += f"""
:do {{
    /interface wifi security remove [find comment="KETRIKA-SEC"]
    /interface wifi security add name=ketrika-sec authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}" comment="KETRIKA-SEC"
    /interface wifi configuration remove [find name="cfg-2ghz"]
    /interface wifi configuration add name=cfg-2ghz ssid="{ssid}" security=ketrika-sec chains=0,1 channel.band=2ghz-ax
    /interface wifi configuration remove [find name="cfg-5ghz"]
    /interface wifi configuration add name=cfg-5ghz ssid="{ssid}" security=ketrika-sec chains=0,1 channel.band=5ghz-ax channel.width=20/40/80mhz
    /interface wifi set [find channel.band~"2ghz" or name~"wifi2"] configuration=cfg-2ghz disabled=no
    /interface wifi set [find channel.band~"5ghz" or name~"wifi1"] configuration=cfg-5ghz disabled=no
    /interface wifi set [find] configuration.ssid="{ssid}" security=ketrika-sec disabled=no
}} on-error={{}};
:do {{
    /interface wireless security-profiles remove [find name="ketrika-sec"]
    /interface wireless security-profiles add name=ketrika-sec mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}"
    /interface wireless set [find] ssid="{ssid}" security-profile=ketrika-sec disabled=no
}} on-error={{}};
"""

    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f"""/interface wireguard remove [find name="warp-ketrika"]
/interface wireguard add name=warp-ketrika listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers remove [find interface="warp-ketrika"]
/interface wireguard peers add interface=warp-ketrika public-key="{cfg['warp_public']}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address remove [find interface="warp-ketrika"]
/ip address add address={cfg['warp_ip']}/32 interface=warp-ketrika
/ip firewall nat remove [find comment="KETRIKA-WARP"]
/ip firewall nat add chain=srcnat out-interface=warp-ketrika action=masquerade comment="KETRIKA-WARP"
/ip route remove [find comment="KETRIKA-ROUTE"]
/ip route add dst-address=0.0.0.0/0 gateway=warp-ketrika distance=1 comment="KETRIKA-ROUTE"
"""

    if plan in ["hotspot", "pro"]:
        s += f"""/ip pool add name=ketrika-hs-pool ranges=10.5.50.10-10.5.50.254
/ip dhcp-server add name=ketrika-hs-dhcp interface=bridge address-pool=ketrika-hs-pool disabled=no
/ip hotspot profile add name=ketrika-hs hotspot-address=10.5.50.1 dns-name={dns_name}
/ip hotspot user profile add name=ketrika-hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot add name=hs-ketrika interface=bridge address-pool=ketrika-hs-pool profile=ketrika-hs disabled=no
"""

    if plan == "pro":
        s += f"""/ip pool add name=ketrika-ppp-pool ranges=10.10.10.2-10.10.10.254
/ppp profile add name=ketrika-ppp local-address=10.10.10.1 remote-address=ketrika-ppp-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"
/interface pppoe-server server add service-name=KETRIKA-NET interface=bridge default-profile=ketrika-ppp disabled=no
"""
    return s

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
        etoiles_str = "⭐" * a[2]
        reviews_html += f"""
        <div class="review-card">
            <div class="review-header">
                <b style="font-size:12px; color:var(--text-dark);">{a[0]} <span style="font-weight:normal; color:var(--text-muted); font-size:10px;">({a[1] or 'Madagascar'})</span></b>
                <span class="stars-gold">{etoiles_str}</span>
            </div>
            <div style="font-size:12px; color:var(--text-body); line-height:1.4;">"{a[3]}"</div>
        </div>
        """

    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "standard" else ""
        badge_html = ""
        if v.get("badge"):
            badge_class = "badge-popular" if v["badge"] == "POPULAIRE" else ("badge-best" if v["badge"] == "MEILLEUR CHOIX" else "badge-pro")
            badge_html = f'<div class="plan-badge {badge_class}">{v["badge"]}</div>'
        
        plans_html += f"""
        <label class="plan-option" for="plan_{k}">
            {badge_html}
            <div style="padding-right:10px;">
                <b style="color:var(--text-dark); font-size:14px;">{v['nom']}</b>
                <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">{v['desc']}</div>
            </div>
            <div style="text-align:right; flex-shrink:0;">
                <b style="color:var(--accent-green); font-size:16px; font-family:'Space Grotesk';">{v['prix']:,} Ar</b><br>
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked}>
            </div>
        </label>
        """
    
    content = f"""
    <div class="card">
        <div class="card-title">💎 POURQUOI NOTRE SOLUTION EST UNIQUE</div>
        <div class="advantages-grid">
            <div class="adv-box">
                <span class="adv-icon">🔒</span>
                <div class="adv-title">WireGuard Tunnel</div>
                <div class="adv-desc">Chiffrement militaire ChaCha20</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">⚡</span>
                <div class="adv-title">Vitesse Native</div>
                <div class="adv-desc">Latence ultra-réduite</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">🌐</span>
                <div class="adv-title">DNS Cloudflare</div>
                <div class="adv-desc">DoH sécurisé 1.1.1.1</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">📶</span>
                <div class="adv-title">Wi-Fi Dual Band</div>
                <div class="adv-desc">2.4G + 5G optimisés</div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">🚀 COMMENT ÇA MARCHE ?</div>
        <div class="steps-grid">
            <div class="step-box">
                <div class="step-num">1</div>
                <div class="step-title">Choisir le Pack</div>
                <div class="step-desc">Sélectionnez la formule adaptée</div>
            </div>
            <div class="step-box">
                <div class="step-num">2</div>
                <div class="step-title">Payer & Recevoir</div>
                <div class="step-desc">Mobile Money → Clé par SMS</div>
            </div>
            <div class="step-box">
                <div class="step-num">3</div>
                <div class="step-title">Injecter le Script</div>
                <div class="step-desc">1 commande dans Winbox = fini !</div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">🛒 CHOISIR VOTRE FORMULE</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            <div class="payment-banner">
                <b style="color:#92400e; font-size:12px; font-family:'Space Grotesk';">📱 PAIEMENT MOBILE MONEY</b>
                <div style="font-size:12px; color:var(--text-body); margin-top:3px;">Envoyez le montant au numéro :</div>
                <div class="payment-phone">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted); font-size:11px;">✅ Mvola | ✅ Orange Money | ✅ Airtel Money</small>
            </div>
            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Téléphone (Réception clé par SMS) :</label>
            <input type="text" name="tel" placeholder="034 00 000 00" required>
            <label>Référence de la transaction :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">🔐 ACTIVATION AVEC VOTRE CLÉ</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS ({total_avis} avis)</div>
        <div class="rating-summary">
            <div class="rating-big">{avg_note}</div>
            <div>
                <div class="stars-gold" style="font-size:18px;">{"⭐" * int(round(avg_note))}</div>
                <div style="color:var(--text-dark); font-size:12px; font-weight:700; margin-top:3px;">Note Globale</div>
                <div style="color:var(--text-muted); font-size:10px;">Basé sur {total_avis} avis vérifiés</div>
            </div>
        </div>
        <div class="reviews-scroll">{reviews_html}</div>
        <hr style="border-color:var(--border-light); margin:14px 0;">
        <div style="font-size:12px; font-weight:700; color:var(--accent-cyan); text-align:center;">✍️ LAISSEZ VOTRE AVIS</div>
        <form method="POST" action="/ajouter-avis">
            <div class="rating-input">
                <input type="radio" id="s5" name="etoiles" value="5" checked><label for="s5">★</label>
                <input type="radio" id="s4" name="etoiles" value="4"><label for="s4">★</label>
                <input type="radio" id="s3" name="etoiles" value="3"><label for="s3">★</label>
                <input type="radio" id="s2" name="etoiles" value="2"><label for="s2">★</label>
                <input type="radio" id="s1" name="etoiles" value="1"><label for="s1">★</label>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                <input type="text" name="nom" placeholder="Votre Nom" required>
                <input type="text" name="ville" placeholder="Ville" required>
            </div>
            <textarea name="commentaire" placeholder="Partagez votre expérience..." rows="2" required style="margin-top:6px;"></textarea>
            <button type="submit" class="btn-primary" style="padding:10px; font-size:11px;">⭐ PUBLIER MON AVIS</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item">
            <div class="faq-question"><span>Est-ce que la configuration affecte mon débit Internet ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, au contraire !</b> Notre optimisation <b>améliore</b> votre débit en supprimant les restrictions et les fuites de paquets. Le tunnel WireGuard est le protocole VPN le plus léger au monde : il consomme moins de 2% de votre bande passante. Votre vitesse réelle reste quasi-identique à votre vitesse native, voire meilleure grâce à l'optimisation du routage DNS et du TTL.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Le tunnel VPN a-t-il un abonnement mensuel ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, 100% gratuit et illimité à vie !</b> Le tunnel WireGuard utilise le service Cloudflare WARP qui est entièrement gratuit. Vous payez uniquement notre outil de configuration une seule fois, et le VPN fonctionne pour toujours sans aucun frais mensuel.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Quand est-ce que ma clé de licence expire ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-cyan);">Votre clé est valide 1 an à partir de la date d'achat.</b> Pendant cette période, vous pouvez générer <b>autant de configurations que vous voulez</b> pour tous vos routeurs MikroTik. Par exemple, si vous achetez une clé aujourd'hui, vous pouvez l'utiliser pour configurer 1, 5, 10 ou 50 routeurs différents pendant 12 mois complets. Après expiration, il suffit de renouveler pour continuer.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Combien de temps prend l'installation ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Moins de <b>5 secondes chrono</b> ! Une seule commande à coller dans Winbox Terminal et tout s'applique automatiquement (TTL, DNS, VPN, Wi-Fi, Hotspot).</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Quels sont les modèles MikroTik compatibles ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Compatible avec <b>tous les modèles RouterOS v7</b> : hAP ax2/ax3, hAP ac2/ac3, RB750/760/2011/3011/4011/1100, CCR1009/2004/2116, mANTBox, LHG, SXTsq, Chateau.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Comment payer et recevoir ma clé ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Paiement Mobile Money (Mvola / Orange / Airtel) au <b>038 28 171 00</b>. Votre clé est envoyée par SMS après validation (5-10 minutes).</div>
        </div>
    </div>
    """
    return render(content)

@app.route("/ajouter-avis", methods=["POST"])
def ajouter_avis():
    nom = request.form.get("nom", "").strip()
    ville = request.form.get("ville", "").strip()
    etoiles = int(request.form.get("etoiles", 5))
    commentaire = request.form.get("commentaire", "").strip()
    if nom and commentaire:
        conn = sqlite3.connect("ketrika.db")
        c = conn.cursor()
        c.execute("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)",
                  (nom, ville, etoiles, commentaire, datetime.now().strftime("%Y-%m-%d")))
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
    c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)",
              (nom, tel, formule, montant, ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Commande enregistrée !</b></div>
        <p style="font-size:13px; line-height:1.6; color:var(--text-body);">
            Merci <b>{nom}</b>. Votre commande pour <b>{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar) est validée.<br><br>
            Nous vérifions la référence <code style="color:var(--accent-cyan);">{ref}</code> et vous envoyons la clé par SMS au <b>{tel}</b>.
        </p>
        <a href="/" class="btn-primary">RETOUR</a>
    </div>
    """
    return render(content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé incorrecte ou expirée !</div><a href="/" class="btn-primary">Retour</a></div>')
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
    plan_key = session.get("type_abo", "basic")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["basic"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])

    feat_html = "<div>✅ Optimisation TTL Avancée</div><div>✅ DNS Sécurisé DoH Cloudflare</div><div>✅ Blocage IPv6 & P2P</div>"
    if plan_key == "basic":
        feat_html += "<div>✅ Wi-Fi Simple activé</div>"
    else:
        feat_html += "<div style='color:var(--accent-green);'>✅ Wi-Fi Dual Band 2.4G + 5G</div>"
    dns_input_html = ""
    bandwidth_html = ""
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel WireGuard (gratuit à vie)</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Portail Captif Hotspot</div>"
        dns_input_html = '<label>🔗 Adresse Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required>'
        bw_options_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            checked = "checked" if k == "illimite" else ""
            bw_options_html += f'<label style="background:#f8fafc; padding:8px 10px; border-radius:8px; font-size:11px; display:flex; align-items:center; gap:8px; cursor:pointer; border:1px solid var(--border-light);"><input type="radio" name="bandwidth" value="{k}" {checked} style="width:auto; margin:0;"><span><b>{v["nom"]}</b> <span style="color:var(--text-muted);">({v["desc"]})</span></span></label>'
        bandwidth_html = f'<div class="wifi-box" style="border-color: rgba(124, 58, 237, 0.3);"><div style="font-size:11px; font-weight:bold; color:var(--accent-purple); margin-bottom:8px;">📊 DÉBIT PAR CLIENT :</div><div style="display:grid; gap:6px;">{bw_options_html}</div><div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;"><input type="text" name="custom_down" value="3M" placeholder="Download"><input type="text" name="custom_up" value="1M" placeholder="Upload"></div></div>'
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ Serveur PPPoE + QoS</div>"
    wifi_pass_html = '<input type="text" name="wifi_pass" value="ketrika2025" placeholder="Mot de passe" required style="margin-top:6px;">' if plan_key != "basic" else '<input type="hidden" name="wifi_pass" value="ketrika2025">'

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge">{plan_info['nom']}</span>
        <a href="/logout" style="color:var(--accent-red); font-size:11px; text-decoration:none;">Fermer</a>
    </div>
    <div class="card">
        <div class="card-title">⚙️ CONFIGURATION - {session['client']}</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>
            <label>2. Identifiant / Client :</label>
            <input type="text" name="client_final" placeholder="Boutique_Rasoa" required>
            <div class="wifi-box" style="margin-top:10px;">
                <div style="font-size:11px; font-weight:bold; color:var(--accent-cyan); margin-bottom:6px;">📶 WI-FI</div>
                <input type="text" name="ssid" value="KETRIKA-NET" placeholder="Nom Wi-Fi" required>
                {wifi_pass_html}
                {dns_input_html}
            </div>
            {bandwidth_html}
            <label>3. Fonctionnalités incluses :</label>
            <div class="feature-box">{feat_html}</div>
            <button type="submit" class="btn-primary">🚀 GÉNÉRER L'INJECTION</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    modele = request.form.get("modele")
    plan_key = session.get("type_abo", "basic")
    client_final = request.form.get("client_final").replace(" ", "_")
    ssid = request.form.get("ssid", "KETRIKA-NET")
    wifi_pass = request.form.get("wifi_pass", "ketrika2025")
    dns_name = request.form.get("dns_name", "ketrika.wifi")
    bw_choice = request.form.get("bandwidth", "illimite")
    if bw_choice == "custom":
        bw_down = request.form.get("custom_down", "3M")
        bw_up = request.form.get("custom_up", "1M")
    else:
        bw_profile = BANDWIDTH_PROFILES.get(bw_choice, BANDWIDTH_PROFILES["illimite"])
        bw_down = bw_profile["down"]
        bw_up = bw_profile["up"]
    options = {"ssid": ssid, "wifi_pass": wifi_pass, "dns_name": dns_name, "bw_down": bw_down, "bw_up": bw_up}
    warp_data = creer_config_warp_complete() if plan_key in ["warp", "hotspot", "pro"] else {}
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    sauvegarder_config(session["licence"], client_final, modele, plan_key, options, warp_data, config_id)
    incrementer_utilisation(session["licence"])
    host = request.host_url.replace("http://", "https://")
    online_cmd = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    cfg = get_config_by_id(config_id)
    raw_s = build_raw_script(cfg).replace('"', '\\"').replace('\n', ' ')
    one_liner = f'/system script add name=ketrika_run source="{raw_s}"; /system script run ketrika_run; /system script remove ketrika_run'

    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Injection prête pour : {client_final} ({modele})</b></div>
        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE</div>
        <div class="terminal-box" id="cmd-oneliner">{one_liner}</div>
        <button class="btn-copy" id="btn-cp1" onclick="copyText('cmd-oneliner', 'btn-cp1')">📋 COPIER LA COMMANDE</button>
        <hr style="border-color:var(--border-light); margin:14px 0;">
        <div class="card-title">MÉTHODE 2 : FICHIER .RSC</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER KETRIKA.RSC</a>
        <hr style="border-color:var(--border-light); margin:14px 0;">
        <div class="card-title">MÉTHODE 3 : ROUTEUR EN LIGNE</div>
        <div class="terminal-box" id="cmd-online">{online_cmd}</div>
        <button class="btn-copy" id="btn-cp2" onclick="copyText('cmd-online', 'btn-cp2')" style="background:linear-gradient(135deg, #64748b, #475569);">📋 COPIER</button>
        <a href="/dashboard" class="btn-primary" style="margin-top:14px;">🔄 NOUVELLE CONFIGURATION</a>
    </div>
    """
    return render(content)

@app.route("/download/<config_id>.rsc")
def download_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("Configuration introuvable", mimetype="text/plain")
    script_content = build_raw_script(cfg)
    mem_file = io.BytesIO()
    mem_file.write(script_content.encode('utf-8'))
    mem_file.seek(0)
    return send_file(mem_file, mimetype="text/plain", as_attachment=True, download_name="ketrika.rsc")

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("# Invalide", mimetype="text/plain")
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
    if not session.get("admin"):
        return redirect(url_for("admin"))
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC")
    commandes = c.fetchall()
    conn.close()
    rows_html = ""
    for cmd in commandes:
        rows_html += f'<tr><td><b>{cmd[1]}</b><br><small>{cmd[2]}</small></td><td>{cmd[3].upper()}<br><b>{cmd[4]:,} Ar</b></td><td><code>{cmd[5]}</code></td><td><form method="POST" action="/admin/valider/{cmd[0]}"><button type="submit" class="btn-primary" style="padding:4px 8px; font-size:10px; margin:0;">⚡ VALIDER</button></form></td></tr>'
    return render(f'<div class="card"><div class="card-title">📋 COMMANDES ({len(commandes)})</div><table><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>{rows_html if rows_html else "<tr><td colspan=4 style=text-align:center>Aucune commande</td></tr>"}</table><a href="/admin/creer" class="btn-primary" style="margin-top:12px;">➕ CRÉER UNE CLÉ</a></div>')

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,))
    cmd = c.fetchone()
    if cmd:
        cle = creer_licence(cmd[1], cmd[2], cmd[3], cmd[4])
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id))
        conn.commit()
    conn.close()
    return render(f'<div class="card"><div class="alert alert-success">✅ Validé pour {cmd[1]} !</div><div class="card-title">CLÉ POUR {cmd[2]} :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">RETOUR</a></div>')

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">Dashboard</a></div>')
    return render('<div class="card"><div class="card-title">Créer une Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="basic">Basic (10k)</option><option value="standard">Standard (15k)</option><option value="warp">Blindé (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
