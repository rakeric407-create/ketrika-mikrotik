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

# Table des commandes et des vrais avis clients
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
        nom TEXT NOT NULL,
        ville TEXT,
        etoiles INTEGER NOT NULL,
        commentaire TEXT NOT NULL,
        date_avis TEXT
    )''')
    # Insérer un premier avis d'exemple si la table est vide
    c.execute("SELECT COUNT(*) FROM avis")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)",
                  ("Mamy R.", "Antananarivo", 5, "Script injecté en 3 secondes sur hAP ax2. Fonctionne parfaitement !", "2026-01-15"))
    conn.commit()
    conn.close()

init_extra_tables()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "base": {"nom": "🛡️ Pack Essentiel", "prix": 10000, "desc": "Optimisation TTL + DNS Sécurisé + Wi-Fi Dual Band"},
    "warp": {"nom": "🚀 Pack Blindé (VPN)", "prix": 20000, "desc": "Essentiel + Tunnel Chiffré WireGuard Global"},
    "hotspot": {"nom": "🎫 Pack Wi-Fi Zone", "prix": 30000, "desc": "Blindé + Portail Hotspot + Contrôle Débit"},
    "pro": {"nom": "🏢 Pack Pro WISP", "prix": 50000, "desc": "Solution intégrale + PPPoE + QoS + DNS Perso"}
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
    "illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Plein débit sans restriction"},
    "ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10 Mbps ↓ / 5 Mbps ↑"},
    "rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5 Mbps ↓ / 2 Mbps ↑"},
    "standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2 Mbps ↓ / 1 Mbps ↑"},
    "eco": {"nom": "🔒 ÉCONOMIQUE (1M/512K)", "down": "1M", "up": "512k", "desc": "1 Mbps ↓ / 512 Kbps ↑"},
    "custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Limites personnalisées"}
}

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #030712;
            --card-bg: #0b1120;
            --accent-cyan: #00f2fe;
            --accent-green: #10b981;
            --accent-purple: #8b5cf6;
            --accent-orange: #f59e0b;
            --accent-gold: #fbbf24;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        @keyframes pulse-glow { 0%, 100% { text-shadow: 0 0 15px rgba(0, 242, 254, 0.4); } 50% { text-shadow: 0 0 25px rgba(0, 242, 254, 0.8); } }
        @keyframes border-flow { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
        @keyframes slide-in { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg-dark); color: var(--text-main); 
            min-height: 100vh; padding: 12px; overflow-x: hidden;
        }
        body::before {
            content: ''; position: fixed; inset: 0;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.06), transparent 40%),
                radial-gradient(circle at 85% 70%, rgba(16, 185, 129, 0.05), transparent 45%);
            z-index: -2; pointer-events: none;
        }
        
        .container { max-width: 820px; margin: auto; animation: slide-in 0.5s ease-out; }
        
        .top-nav {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 12px; padding: 8px 14px; background: rgba(11, 17, 32, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px; backdrop-filter: blur(10px);
        }
        .lang-btn {
            background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan); border: 1px solid rgba(0, 242, 254, 0.3);
            padding: 4px 10px; border-radius: 15px; font-size: 11px; font-weight: 700; cursor: pointer;
        }
        
        .header { text-align: center; padding: 12px 0 18px; }
        .header h1 { 
            font-family: 'Space Grotesk', sans-serif; font-size: 30px; font-weight: 900; 
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green)); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
            letter-spacing: 1.5px; text-transform: uppercase;
        }
        .header p { color: var(--text-muted); font-size: 12px; margin-top: 4px; }
        
        .card { 
            background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.05); 
            border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; 
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); position: relative; overflow: hidden;
        }
        .card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-green), transparent);
        }
        
        .card-title { 
            font-family: 'Space Grotesk', sans-serif; font-size: 14px; color: var(--accent-cyan); 
            margin-bottom: 12px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;
            display: flex; align-items: center; gap: 6px;
        }

        .advantages-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; }
        .adv-box { 
            background: #101524; padding: 12px; border-radius: 10px; text-align: center; 
            border: 1px solid rgba(255,255,255,0.04);
        }
        .adv-icon { font-size: 20px; display: block; margin-bottom: 4px; }
        .adv-title { font-family: 'Space Grotesk'; font-size: 12px; color: #fff; font-weight: 700; }
        .adv-desc { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
        
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input, select, textarea { 
            width: 100%; padding: 11px 13px; margin-top: 4px; 
            background: #111827; border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 8px; color: #fff; font-size: 13px; font-family: inherit;
        }
        input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent-cyan); }

        .btn-primary { 
            width: 100%; padding: 13px; margin-top: 14px; 
            background: linear-gradient(135deg, #00f2fe, #4facfe); 
            color: #030712; border: none; border-radius: 8px; 
            font-size: 13px; font-weight: 800; cursor: pointer; 
            font-family: 'Space Grotesk'; letter-spacing: 0.5px; text-transform: uppercase;
            text-decoration: none; display: inline-block; text-align: center;
        }
        .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }
        .btn-copy {
            background: linear-gradient(135deg, #8b5cf6, #6d28d9); color: #fff;
            padding: 11px; border-radius: 8px; border: none; font-weight: 700;
            cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase;
            margin-top: 8px; font-size: 12px;
        }
        .btn-copy.copied { background: #10b981; }

        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 6px; }
        .plan-option { 
            background: #101524; border: 1px solid rgba(255, 255, 255, 0.05); 
            padding: 11px 14px; border-radius: 10px; cursor: pointer; 
            display: flex; justify-content: space-between; align-items: center;
        }
        .plan-option:hover { border-color: var(--accent-cyan); }
        .plan-option input { width: 16px; height: 16px; accent-color: var(--accent-cyan); }

        .payment-banner { 
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.02)); 
            border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 10px; 
            padding: 12px; margin-top: 12px; text-align: center; 
        }
        .payment-phone { 
            font-family: 'Space Grotesk'; font-size: 24px; color: #f59e0b; 
            margin: 4px 0; font-weight: 800; letter-spacing: 1px; 
        }

        .terminal-box { 
            background: #040711; border: 1px solid var(--accent-green); 
            color: var(--accent-green); padding: 12px; border-radius: 8px; 
            font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 8px;
        }

        .badge { background: rgba(0, 242, 254, 0.08); color: var(--accent-cyan); padding: 4px 10px; border-radius: 15px; font-size: 10px; font-weight: 700; border: 1px solid rgba(0, 242, 254, 0.3); }
        .alert { padding: 10px 12px; border-radius: 8px; margin-bottom: 10px; font-size: 12px; }
        .alert-success { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #a7f3d0; }
        .alert-error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5; }

        /* ÉTOILES INTERACTIVES POUR NOTER */
        .rating-input {
            display: flex; flex-direction: row-reverse; justify-content: center; gap: 8px; margin: 10px 0;
        }
        .rating-input input { display: none; }
        .rating-input label {
            font-size: 28px; color: #374151; cursor: pointer; transition: 0.2s; margin: 0;
        }
        .rating-input label:hover,
        .rating-input label:hover ~ label,
        .rating-input input:checked ~ label {
            color: var(--accent-gold);
            transform: scale(1.15);
        }

        /* VRAIS AVIS LISTE */
        .reviews-scroll {
            max-height: 220px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-top: 10px;
        }
        .review-card { 
            background: #101524; padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04);
        }
        .review-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
        .stars-gold { color: var(--accent-gold); font-size: 11px; letter-spacing: 2px; }

        /* ACCORDION FAQ */
        .faq-item { border-bottom: 1px solid rgba(255,255,255,0.04); padding: 10px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: #fff; font-size: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .faq-answer { color: var(--text-muted); font-size: 11px; line-height: 1.5; margin-top: 6px; display: none; }
        .faq-item.active .faq-answer { display: block; }
        .faq-toggle { color: var(--accent-cyan); font-size: 14px; }

        /* WHATSAPP FLOAT */
        .whatsapp-float {
            position: fixed; bottom: 18px; right: 18px; z-index: 9999;
            background: linear-gradient(135deg, #25D366, #128C7E); color: #fff;
            padding: 10px 15px; border-radius: 30px; font-weight: 800; font-size: 12px;
            box-shadow: 0 8px 20px rgba(37, 211, 102, 0.3); text-decoration: none;
            display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk';
        }

        .footer { text-align: center; color: var(--text-muted); opacity: 0.8; margin: 20px 0 10px; font-size: 10px; }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance%20MikroTik" target="_blank" class="whatsapp-float">
        💬 <span>Assistance</span>
    </a>

    <div class="container">
        <div class="top-nav">
            <span style="font-size:11px; color:var(--text-muted);">⚡ KETRIKA OS v2.7 • Madagascar</span>
            <button class="lang-btn" onclick="toggleLang()">🇲🇬 MG / 🇫🇷 FR</button>
        </div>

        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p class="txt-fr">Système Professionnel d'Optimisation & Déploiement Réseau MikroTik</p>
            <p class="txt-mg" style="display:none;">Fitaovana matihanina hanatsarana sy hanitsiana ny MikroTik</p>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • Ingénierie Réseau • Support : 038 28 171 00
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
    
    # Récupération dynamique des vrais avis depuis SQLite
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
                <b style="font-size:12px; color:#fff;">{a[0]} <span style="font-weight:normal; color:var(--text-muted); font-size:10px;">({a[1] or 'Madagascar'})</span></b>
                <span class="stars-gold">{etoiles_str}</span>
            </div>
            <div style="font-size:11px; color:var(--text-muted); line-height:1.4;">"{a[3]}"</div>
        </div>
        """

    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "base" else ""
        plans_html += f"""
        <label class="plan-option" for="plan_{k}">
            <div>
                <b style="color:#fff; font-size:13px;">{v['nom']}</b>
                <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">{v['desc']}</div>
            </div>
            <div style="text-align:right;">
                <b style="color:var(--accent-green); font-size:14px; font-family:'Space Grotesk';">{v['prix']:,} Ar</b><br>
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked}>
            </div>
        </label>
        """
    
    content = f"""
    <!-- ATOUTS TECHNIQUES -->
    <div class="card">
        <div class="advantages-grid">
            <div class="adv-box">
                <span class="adv-icon">🔒</span>
                <div class="adv-title">WireGuard Tunnel</div>
                <div class="adv-desc">Chiffrement 100% anonyme</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">⚡</span>
                <div class="adv-title">Vitesse Maximale</div>
                <div class="adv-desc">Latence ultra-réduite</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">🌐</span>
                <div class="adv-title">DNS DoH Sécurisé</div>
                <div class="adv-desc">Cloudflare 1.1.1.1</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">📶</span>
                <div class="adv-title">Wi-Fi Dual Band</div>
                <div class="adv-desc">Canaux 2.4G & 5G 80MHz</div>
            </div>
        </div>
    </div>

    <!-- COMMANDE -->
    <div class="card">
        <div class="card-title">🛒 1. COMMANDER UNE CONFIGURATION</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            
            <div class="payment-banner">
                <b style="color:#f59e0b; font-size:12px; font-family:'Space Grotesk';">📱 MOBILE MONEY DIRECT</b>
                <div style="font-size:11px; color:#fff; margin-top:2px;">Envoyez votre paiement au numéro :</div>
                <div class="payment-phone">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted); font-size:10px;">Mvola | Orange Money | Airtel Money</small>
            </div>

            <label>Votre Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Numéro de Téléphone (Réception Clé) :</label>
            <input type="text" name="tel" placeholder="034 00 000 00" required>
            <label>Référence transaction SMS :</label>
            <input type="text" name="ref_paiement" placeholder="Code de transaction reçu" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <!-- ACTIVATION -->
    <div class="card">
        <div class="card-title">🔐 2. VOUS AVEZ UNE CLÉ ? ACTIVEZ ICI</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1px;">
            <button type="submit" class="btn-primary btn-success">OUVRIR LE GÉNÉRATEUR</button>
        </form>
    </div>

    <!-- SECTION VRAIS AVIS CLIENTS & FORMULAIRE POUR NOTER -->
    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS ({total_avis}) • Note : {avg_note}/5</div>
        
        <div class="reviews-scroll">
            {reviews_html}
        </div>

        <hr style="border-color:rgba(255,255,255,0.05); margin:14px 0;">

        <div style="font-size:12px; font-weight:700; color:var(--accent-cyan); text-align:center;">✍️ DONNER VOTRE AVIS & ÉTOILES</div>
        <form method="POST" action="/ajouter-avis">
            <div class="rating-input">
                <input type="radio" id="s5" name="etoiles" value="5" checked><label for="s5">★</label>
                <input type="radio" id="s4" name="etoiles" value="4"><label for="s4">★</label>
                <input type="radio" id="s3" name="etoiles" value="3"><label for="s3">★</label>
                <input type="radio" id="s2" name="etoiles" value="2"><label for="s2">★</label>
                <input type="radio" id="s1" name="etoiles" value="1"><label for="s1">★</label>
            </div>
            
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                <input type="text" name="nom" placeholder="Votre Nom / Pseudo" required>
                <input type="text" name="ville" placeholder="Votre Ville (Ex: Tana)" required>
            </div>
            <textarea name="commentaire" placeholder="Votre avis sur notre service..." rows="2" required style="margin-top:6px;"></textarea>
            <button type="submit" class="btn-primary" style="padding:10px; font-size:11px; margin-top:8px;">⭐ PUBLIER MON AVIS</button>
        </form>
    </div>

    <!-- FAQ -->
    <div class="card">
        <div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item">
            <div class="faq-question"><span>Le tunnel VPN nécessite-t-il un abonnement ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, 100% gratuit et illimité à vie !</b> Vous payez uniquement l'outil de configuration une fois. Aucun frais mensuel de VPN.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Combien de temps prend l'installation ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Moins de <b>5 secondes</b> ! Vous collez la commande dans Winbox Terminal et tout s'applique automatiquement.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Quels sont les modèles compatibles ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Compatible avec tous les MikroTik RouterOS v7 : hAP ax2/ax3, hAP ac2/ac3, RB750/760/2011/3011/4011/1100, CCR, mANTBox, LHG, SXTsq.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Comment payer et recevoir la clé ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Paiement Mobile Money (Mvola / Orange / Airtel) au <b>038 28 171 00</b>. Votre clé est transmise par SMS après validation.</div>
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
        <div class="alert alert-success"><b>✅ Commande enregistrée avec succès !</b></div>
        <p style="font-size:12px; line-height:1.5; color:var(--text-muted);">
            Merci <b style="color:#fff;">{nom}</b>. Votre commande pour <b style="color:#fff;">{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar) est validée.<br><br>
            Notre équipe vérifie la référence <code style="color:var(--accent-cyan);">{ref}</code> et vous envoie la clé par SMS au <b style="color:#fff;">{tel}</b> d'ici quelques instants.
        </p>
        <a href="/" class="btn-primary">RETOUR À L'ACCUEIL</a>
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
    
    plan_key = session.get("type_abo", "base")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["base"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])

    feat_html = "<div>✅ Optimisation TTL Avancée</div><div>✅ DNS Sécurisé DoH Cloudflare</div><div>✅ Blocage IPv6 & P2P</div><div>✅ Wi-Fi Dual Band Haute Vitesse</div>"
    dns_input_html = ""
    bandwidth_html = ""
    
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel Chiffré WireGuard (100% gratuit à vie)</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Portail Captif Hotspot</div>"
        dns_input_html = """
        <label>🔗 Adresse Hotspot (Page de login) :</label>
        <input type="text" name="dns_name" value="wifizone.wifi" required>
        """
        
        bw_options_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            checked = "checked" if k == "illimite" else ""
            bw_options_html += f"""
            <label style="background:#111827; padding:8px; border-radius:6px; font-size:11px; display:flex; align-items:center; gap:6px; cursor:pointer;">
                <input type="radio" name="bandwidth" value="{k}" {checked} style="width:auto; margin:0;">
                <span><b>{v['nom']}</b> ({v['desc']})</span>
            </label>
            """
        
        bandwidth_html = f"""
        <div class="wifi-box" style="border-color: rgba(139, 92, 246, 0.4); margin-top:10px;">
            <div style="font-size:11px; font-weight:bold; color:var(--accent-purple); margin-bottom:6px;">📊 DÉBIT PAR CLIENT :</div>
            <div style="display:grid; grid-template-columns:1fr; gap:4px;">{bw_options_html}</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:6px;">
                <input type="text" name="custom_down" value="3M" placeholder="Download (ex: 5M)">
                <input type="text" name="custom_up" value="1M" placeholder="Upload (ex: 2M)">
            </div>
        </div>
        """
    
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ Serveur PPPoE + QoS Bandwidth</div>"

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge">{plan_info['nom']}</span>
        <a href="/logout" style="color:#ef4444; font-size:11px; text-decoration:none;">Fermer</a>
    </div>

    <div class="card">
        <div class="card-title">⚙️ CONFIGURATION - {session['client']}</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Identifiant / Client :</label>
            <input type="text" name="client_final" placeholder="Boutique_Rasoa" required>

            <div class="wifi-box" style="margin-top:10px;">
                <div style="font-size:11px; font-weight:bold; color:var(--accent-cyan); margin-bottom:6px;">📶 WI-FI (2.4G + 5G)</div>
                <input type="text" name="ssid" value="KETRIKA-NET" placeholder="Nom Wi-Fi" required>
                <input type="text" name="wifi_pass" value="ketrika2025" placeholder="Mot de passe" required style="margin-top:6px;">
                {dns_input_html}
            </div>
            
            {bandwidth_html}

            <label>3. Inclus dans votre formule :</label>
            <div class="feature-box" style="padding:10px; font-size:11px; line-height:1.8;">{feat_html}</div>

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
    plan_key = session.get("type_abo", "base")
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

        <div class="card-title">MÉTHODE 1 : COMMANDE EN 1 SEULE LIGNE (ANTI-DÉCONNEXION)</div>
        <div class="terminal-box" id="cmd-oneliner">{one_liner}</div>
        <button class="btn-copy" id="btn-cp1" onclick="copyText('cmd-oneliner', 'btn-cp1')">📋 COPIER LA COMMANDE</button>

        <hr style="border-color:rgba(255,255,255,0.05); margin:14px 0;">

        <div class="card-title">MÉTHODE 2 : TÉLÉCHARGER LE FICHIER (.RSC)</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER KETRIKA.RSC</a>

        <hr style="border-color:rgba(255,255,255,0.05); margin:14px 0;">

        <div class="card-title">MÉTHODE 3 : SI ROUTEUR DÉJÀ EN LIGNE</div>
        <div class="terminal-box" id="cmd-online">{online_cmd}</div>
        <button class="btn-copy" id="btn-cp2" onclick="copyText('cmd-online', 'btn-cp2')" style="background:#374151;">📋 COPIER</button>

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
        rows_html += f"""
        <tr>
            <td><b>{cmd[1]}</b><br><small>{cmd[2]}</small></td>
            <td>{cmd[3].upper()}<br><b>{cmd[4]:,} Ar</b></td>
            <td><code>{cmd[5]}</code></td>
            <td>
                <form method="POST" action="/admin/valider/{cmd[0]}">
                    <button type="submit" class="btn-primary" style="padding:4px 8px; font-size:10px; margin:0;">⚡ VALIDER</button>
                </form>
            </td>
        </tr>
        """

    return render(f"""
    <div class="card">
        <div class="card-title">📋 COMMANDES ({len(commandes)})</div>
        <table><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>
        {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center;">Aucune commande en attente</td></tr>'}
        </table>
        <a href="/admin/creer" class="btn-primary" style="margin-top:12px;">➕ CRÉER UNE CLÉ</a>
    </div>
    """)

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
    
    return render(f"""
    <div class="card">
        <div class="alert alert-success">✅ Validé pour {cmd[1]} !</div>
        <div class="card-title">CLÉ POUR {cmd[2]} :</div>
        <div class="terminal-box">{cle}</div>
        <a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">RETOUR</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:12px;">Dashboard</a></div>')
    return render("""<div class="card"><div class="card-title">Créer une Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="base">Essentiel (10k)</option><option value="warp">Blindé (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
