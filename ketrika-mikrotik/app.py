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
    if c.fetchone()[0] < 3:
        avis_initiaux = [
            ("Mamy R.", "Antananarivo", 5, "Script injecté après reset total sur mon hAP ax2. Tout a fonctionné du premier coup !", "2026-01-15"),
            ("Jean Luc", "Tamatave", 5, "Configuration propre sur hAP ac2. Le Wi-Fi et le pare-feu sont impeccables.", "2026-01-20"),
            ("Boutique Alpha", "Majunga", 5, "Pack Wi-Fi Zone parfait avec gestion de débit pour mon business.", "2026-01-28"),
            ("Toky N.", "Diego Suarez", 5, "Très satisfait du débridage et de la réactivité du support WhatsApp.", "2026-02-02")
        ]
        c.executemany("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", avis_initiaux)
    
    # 5 CLÉS DE TEST FRAÎCHES (1 USAGE UNIQUE CHACUNE)
    test_keys = [
        ("KTR-BASIC-10K", "Test Basic", "0382817100", "basic", 10000),
        ("KTR-STANDARD-15K", "Test Standard", "0382817100", "standard", 15000),
        ("KTR-WARP-20K", "Test Warp", "0382817100", "warp", 20000),
        ("KTR-HOTSPOT-30K", "Test Hotspot", "0382817100", "hotspot", 30000),
        ("KTR-PRO-50K", "Test Pro", "0382817100", "pro", 50000)
    ]
    for k in test_keys:
        c.execute("INSERT OR IGNORE INTO licences (cle, client_nom, client_telephone, type_abonnement, date_creation, date_expiration, actif, nb_utilisations, prix_paye) VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?)",
                  (k[0], k[1], k[2], k[3], datetime.now().isoformat(), "2027-01-01", k[4]))
    
    conn.commit()
    conn.close()

init_extra_tables()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "desc": "Config A à Z + Anti-Bridage + Wi-Fi", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Blindé VPN", "prix": 20000, "desc": "Standard + Tunnel WireGuard gratuit à vie", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "desc": "Blindé + Portail Hotspot + Débit contrôlé", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "desc": "Solution intégrale + PPPoE + QoS", "badge": "PRO"}
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
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #f1f5f9;
            --bg-card: #ffffff;
            --accent-cyan: #0284c7;
            --accent-green: #059669;
            --accent-purple: #7c3aed;
            --accent-orange: #d97706;
            --accent-gold: #f59e0b;
            --accent-red: #dc2626;
            --text-dark: #0f172a;
            --text-body: #334155;
            --text-muted: #64748b;
            --border-light: #e2e8f0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg-main); color: var(--text-dark); min-height: 100vh; padding: 12px; }
        .container { max-width: 840px; margin: auto; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding: 10px 16px; background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .lang-btn { background: #e0f2fe; color: var(--accent-cyan); border: 1px solid #bae6fd; padding: 5px 12px; border-radius: 15px; font-size: 11px; font-weight: 700; cursor: pointer; }
        .header { text-align: center; padding: 15px 0 22px; }
        .header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 900; background: linear-gradient(135deg, #0284c7, #7c3aed, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1.5px; text-transform: uppercase; }
        .header .tagline { color: var(--text-muted); font-size: 13px; margin-top: 4px; }
        .header .stats-live { display: inline-flex; gap: 8px; margin-top: 10px; padding: 6px 14px; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 20px; font-size: 11px; color: var(--accent-green); font-weight: 700; }
        .live-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; display: inline-block; }
        .card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; padding: 22px; margin-bottom: 16px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); position: relative; overflow: hidden; }
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 15px; color: var(--accent-cyan); margin-bottom: 14px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
        .advantages-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        @media (max-width: 600px) { .advantages-grid { grid-template-columns: repeat(2, 1fr); } }
        .adv-box { background: #f8fafc; padding: 14px 10px; border-radius: 12px; text-align: center; border: 1px solid var(--border-light); }
        .adv-icon { font-size: 26px; display: block; margin-bottom: 4px; }
        .adv-title { font-family: 'Space Grotesk'; font-size: 13px; color: var(--text-dark); font-weight: 800; }
        .adv-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 12px; text-transform: uppercase; }
        input, select, textarea { width: 100%; padding: 12px 14px; margin-top: 5px; background: #f8fafc; border: 1px solid var(--border-light); border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent-cyan); background: #fff; }
        .btn-primary { width: 100%; padding: 14px; margin-top: 15px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; border: none; border-radius: 10px; font-size: 14px; font-weight: 800; cursor: pointer; font-family: 'Space Grotesk'; text-transform: uppercase; text-decoration: none; display: inline-block; text-align: center; }
        .btn-success { background: linear-gradient(135deg, #059669, #047857); }
        .btn-copy { background: linear-gradient(135deg, #7c3aed, #6d28d9); color: #fff; padding: 12px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase; margin-top: 8px; font-size: 12px; }
        .btn-copy.copied { background: linear-gradient(135deg, #059669, #047857); }
        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 8px; }
        .plan-option { background: #f8fafc; border: 2px solid var(--border-light); padding: 14px 16px; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; position: relative; }
        .plan-option:hover { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-option input { width: 18px; height: 18px; accent-color: var(--accent-cyan); }
        .plan-badge { position: absolute; top: -1px; right: 14px; padding: 3px 10px; border-radius: 0 0 8px 8px; font-size: 9px; font-weight: 800; color: #fff; font-family: 'Space Grotesk'; }
        .badge-popular { background: #ea580c; }
        .badge-best { background: #db2777; }
        .badge-pro { background: #059669; }
        .payment-banner { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 16px; margin-top: 14px; text-align: center; }
        .payment-phone { font-family: 'Space Grotesk'; font-size: 28px; color: #b45309; margin: 4px 0; font-weight: 900; letter-spacing: 2px; }
        .terminal-box { background: #0f172a; border: 1px solid #334155; color: #4ade80; padding: 14px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 11px; word-break: break-all; margin-top: 8px; }
        .badge { background: #e0f2fe; color: var(--accent-cyan); padding: 5px 12px; border-radius: 15px; font-size: 11px; font-weight: 700; }
        .alert { padding: 12px 15px; border-radius: 10px; margin-bottom: 12px; font-size: 13px; }
        .alert-success { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
        .alert-error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
        .alert-warning { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
        .rating-summary { display: flex; align-items: center; justify-content: center; gap: 15px; padding: 14px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; margin-bottom: 12px; }
        .rating-big { font-family: 'Space Grotesk'; font-size: 38px; font-weight: 900; color: #b45309; }
        .stars-gold { color: var(--accent-gold); font-size: 13px; letter-spacing: 2px; }
        .review-card { background: #f8fafc; padding: 12px; border-radius: 10px; border: 1px solid var(--border-light); margin-bottom: 8px; }
        .rating-input { display: flex; flex-direction: row-reverse; justify-content: center; gap: 6px; margin: 10px 0; }
        .rating-input input { display: none; }
        .rating-input label { font-size: 30px; color: #cbd5e1; cursor: pointer; }
        .rating-input label:hover, .rating-input label:hover ~ label, .rating-input input:checked ~ label { color: var(--accent-gold); }
        .faq-item { border-bottom: 1px solid var(--border-light); padding: 12px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: var(--text-dark); font-size: 13px; cursor: pointer; display: flex; justify-content: space-between; }
        .faq-answer { color: var(--text-body); font-size: 12px; line-height: 1.6; margin-top: 6px; display: none; background: #f8fafc; padding: 10px 12px; border-radius: 8px; }
        .faq-item.active .faq-answer { display: block; }
        .whatsapp-float { position: fixed; bottom: 20px; right: 20px; z-index: 9999; background: #25D366; color: #fff; padding: 12px 18px; border-radius: 30px; font-weight: 800; font-size: 13px; text-decoration: none; display: flex; align-items: center; gap: 8px; font-family: 'Space Grotesk'; box-shadow: 0 4px 15px rgba(37,211,102,0.4); }
        .wifi-box { background: #f0f9ff; border: 1px dashed #7dd3fc; padding: 14px; border-radius: 12px; margin-top: 10px; }
        .feature-box { background: #f0fdf4; padding: 12px; border-radius: 10px; margin-top: 8px; line-height: 2; font-size: 12px; border-left: 4px solid var(--accent-green); }
        .footer { text-align: center; color: var(--text-muted); margin: 25px 0 15px; font-size: 11px; padding: 12px; border-top: 1px solid var(--border-light); }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">💬 <span>Assistance</span></a>
    
    <div class="container">
        <div class="top-nav">
            <span style="font-size:11px; color:var(--text-muted); display:flex; align-items:center; gap:6px;"><span class="live-dot"></span> KETRIKA OS v3.6 • Sécurité 1 Clé = 1 Routeur</span>
            <button class="lang-btn" onclick="toggleLang()">🇲🇬 MG / 🇫🇷 FR</button>
        </div>
        
        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p class="tagline txt-fr">Configuration Complète A à Z • Adaptée au modèle exact • 1 Clé = 1 Routeur</p>
            <p class="tagline txt-mg" style="display:none;">Fitaovana matihanina manamboatra ny MikroTik araka ny modely marina</p>
            <div class="stats-live"><span class="live-dot"></span><span>🔥 Architecture Clean • Firewall Pro • Wi-Fi Dédié</span></div>
        </div>
        
        {{ content|safe }}
        
        <div class="footer">KETRIKA MIKROTIK PRO © 2026 • Ingénierie Réseau Avancée • Support : 038 28 171 00</div>
    </div>

    <script>
        let currentLang = 'fr';
        function toggleLang() { currentLang = currentLang === 'fr' ? 'mg' : 'fr'; document.querySelectorAll('.txt-fr').forEach(e => e.style.display = currentLang === 'fr' ? '' : 'none'); document.querySelectorAll('.txt-mg').forEach(e => e.style.display = currentLang === 'mg' ? '' : 'none'); }
        function copyText(elemId, btnId) { const text = document.getElementById(elemId).innerText; navigator.clipboard.writeText(text).then(() => { const btn = document.getElementById(btnId); const o = btn.innerHTML; btn.innerHTML = '✅ COPIÉ !'; btn.classList.add('copied'); setTimeout(() => { btn.innerHTML = o; btn.classList.remove('copied'); }, 2500); }); }
        document.querySelectorAll('.faq-question').forEach(q => { q.addEventListener('click', () => q.parentElement.classList.toggle('active')); });
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content)

def build_raw_script(cfg):
    plan = cfg["type"]
    modele = cfg.get("modele", "")
    opt = cfg.get("options", {})
    ssid = opt.get("ssid", "KETRIKA-NET")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0")
    bw_up = opt.get("bw_up", "0")
    
    # 1. Calcul précis du sous-réseau
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
/interface bridge add name=bridge-lan auto-mac=yes comment="defconf-LAN"
/interface list add name=WAN
/interface list add name=LAN
/interface list member add interface=ether1 list=WAN
/interface list member add interface=bridge-lan list=LAN

# Ajout automatique de tous les ports physiques restants au Bridge
:foreach i in=[/interface ethernet find where name!="ether1"] do={{
    /interface bridge port add bridge=bridge-lan interface=$i comment="LAN-PORT"
}}

# --- 2. WAN (PORT 1 STARLINK) ---
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no use-peer-ntp=yes add-default-route=yes comment="STARLINK-WAN"

# --- 3. ADRESSAGE IP ET SERVEUR DHCP ---
/ip address add address={router_ip}/24 interface=bridge-lan comment="LAN-IP"
/ip pool add name=dhcp-pool ranges={dhcp_pool_start}-{dhcp_pool_end}
/ip dhcp-server add name=dhcp-lan interface=bridge-lan address-pool=dhcp-pool disabled=no lease-time=12h
/ip dhcp-server network add address={dhcp_net} gateway={router_ip} dns-server=1.1.1.1,1.0.0.1 comment="LAN-NET"

# --- 4. ACCES INTERNET (NAT) ---
/ip firewall nat add chain=srcnat out-interface-list=WAN action=masquerade comment="NAT-INTERNET"

# --- 5. ANTI-BRIDAGE STARLINK (MANGLE TTL = 64) ---
/ip firewall mangle add chain=postrouting out-interface-list=WAN action=change-ttl new-ttl=set:64 passthrough=yes comment="STARLINK-TTL-64"

# --- 6. DNS SECURISE DOH ---
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=udp dst-port=53 action=redirect to-ports=53 comment="DNS-REDIRECT-UDP"
/ip firewall nat add chain=dstnat in-interface-list=LAN protocol=tcp dst-port=53 action=redirect to-ports=53 comment="DNS-REDIRECT-TCP"

# --- 7. PARE-FEU D'ENTREPRISE (STATEFUL FIREWALL) ---
/ip firewall filter add chain=input action=accept connection-state=established,related,untracked comment="ACCEPT-ESTABLISHED"
/ip firewall filter add chain=input action=drop connection-state=invalid comment="DROP-INVALID"
/ip firewall filter add chain=input action=accept protocol=icmp comment="ACCEPT-PING"
/ip firewall filter add chain=input in-interface-list=LAN action=accept comment="ACCEPT-LAN-INPUT"
/ip firewall filter add chain=input in-interface-list=WAN action=drop comment="DROP-ALL-WAN-INPUT"

/ip firewall filter add chain=forward action=accept connection-state=established,related,untracked comment="ACCEPT-ESTABLISHED-FWD"
/ip firewall filter add chain=forward action=drop connection-state=invalid comment="DROP-INVALID-FWD"
/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=150,32 action=drop comment="ANTI-FLOOD-P2P"
/ip firewall filter add chain=forward in-interface-list=WAN connection-nat-state=!dstnat connection-state=new action=drop comment="DROP-UNAUTHORIZED-WAN-FWD"

/ipv6 settings set disable-ipv6=yes
/ip service disable telnet,ftp,api
"""

    if is_wifi6:
        s += f"""
# --- 8. WI-FI 6 DEDIE (ROUTEROS V7 WIFI) ---
/interface wifi security add name=sec-wifi authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}" comment="WIFI6-SEC"
/interface wifi configuration add name=cfg-wifi ssid="{ssid}" security=sec-wifi country="Madagascar"
/interface wifi set [find] configuration=cfg-wifi disabled=no
:foreach w in=[/interface wifi find] do={{ /interface bridge port add bridge=bridge-lan interface=$w comment="WIFI-PORT" }}
"""
    elif is_wireless:
        s += f"""
# --- 8. WI-FI CLASSIQUE DEDIE (ROUTEROS WIRELESS N/AC) ---
/interface wireless security-profiles add name=sec-wifi mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}" unicast-ciphers=aes-ccm group-ciphers=aes-ccm
/interface wireless set [find] ssid="{ssid}" security-profile=sec-wifi country="madagascar" disabled=no
:foreach w in=[/interface wireless find] do={{ /interface bridge port add bridge=bridge-lan interface=$w comment="WIFI-PORT" }}
"""

    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f"""
# --- 9. TUNNEL WIREGUARD VPN WARP ---
/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers add interface=warp-vpn public-key="{cfg['warp_public']}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address add address={cfg['warp_ip']}/32 interface=warp-vpn
/interface list member add interface=warp-vpn list=WAN
/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade comment="WARP-NAT"
/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn distance=1 comment="VPN-DEFAULT-ROUTE"
"""

    if plan in ["hotspot", "pro"]:
        s += f"""
# --- 10. SERVEUR HOTSPOT WI-FI ZONE ---
/ip pool add name=hs-pool ranges=10.5.50.10-10.5.50.250
/ip dhcp-server add name=dhcp-hs interface=bridge-lan address-pool=hs-pool disabled=no
/ip hotspot profile add name=hs-prof hotspot-address=10.5.50.1 dns-name={dns_name}
/ip hotspot user profile add name=hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot add name=hotspot-ketrika interface=bridge-lan address-pool=hs-pool profile=hs-prof disabled=no
"""

    if plan == "pro":
        s += f"""
# --- 11. SERVEUR PPPOE & GESTION DE BANDE PASSANTE ---
/ip pool add name=pppoe-pool ranges=10.10.10.2-10.10.10.254
/ppp profile add name=prof-pppoe local-address=10.10.10.1 remote-address=pppoe-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"
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
        reviews_html += f'<div class="review-card"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><b style="font-size:12px;">{a[0]} <span style="color:var(--text-muted); font-size:10px;">({a[1] or "Madagascar"})</span></b><span class="stars-gold">{"⭐" * a[2]}</span></div><div style="font-size:12px; color:var(--text-body);">"{a[3]}"</div></div>'

    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "standard" else ""
        badge_html = ""
        if v.get("badge"):
            bc = "badge-popular" if v["badge"] == "POPULAIRE" else ("badge-best" if v["badge"] == "MEILLEUR CHOIX" else "badge-pro")
            badge_html = f'<div class="plan-badge {bc}">{v["badge"]}</div>'
        plans_html += f'<label class="plan-option" for="plan_{k}">{badge_html}<div style="padding-right:10px;"><b style="font-size:14px;">{v["nom"]}</b><div style="color:var(--text-muted); font-size:11px; margin-top:2px;">{v["desc"]}</div></div><div style="text-align:right; flex-shrink:0;"><b style="color:var(--accent-green); font-size:16px; font-family:Space Grotesk;">{v["prix"]:,} Ar</b><br><input type="radio" name="formule" id="plan_{k}" value="{k}" {checked}></div></label>'
    
    content = f"""
    <div class="card">
        <div class="card-title">💎 POURQUOI NOTRE SOLUTION EST UNIQUE</div>
        <div class="advantages-grid">
            <div class="adv-box"><span class="adv-icon">🔒</span><div class="adv-title">WireGuard</div><div class="adv-desc">Chiffrement ChaCha20</div></div>
            <div class="adv-box"><span class="adv-icon">⚡</span><div class="adv-title">Vitesse Max</div><div class="adv-desc">Latence ultra-réduite</div></div>
            <div class="adv-box"><span class="adv-icon">🌐</span><div class="adv-title">DNS Cloudflare</div><div class="adv-desc">DoH 1.1.1.1 sécurisé</div></div>
            <div class="adv-box"><span class="adv-icon">📶</span><div class="adv-title">Config A à Z</div><div class="adv-desc">Même après Reset</div></div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">🛒 1. CHOISIR VOTRE FORMULE</div>
        <div class="alert-warning" style="font-size:12px;">⚠️ <b>1 Clé = 1 Routeur uniquement.</b> Chaque clé configure intégralement un seul boîtier MikroTik.</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            <div class="payment-banner">
                <b style="color:#92400e; font-size:12px; font-family:Space Grotesk;">📱 PAIEMENT MOBILE MONEY</b>
                <div style="font-size:12px; color:var(--text-body); margin-top:3px;">Envoyez le montant au numéro :</div>
                <div class="payment-phone">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted);">✅ Mvola | ✅ Orange Money | ✅ Airtel Money</small>
            </div>
            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Téléphone (Réception de la clé par SMS) :</label>
            <input type="text" name="tel" placeholder="034 00 000 00" required>
            <label>Référence transaction SMS :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">🔐 2. ACTIVATION (1 Clé = 1 Routeur)</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS ({total_avis}) • Note : {avg_note}/5</div>
        <div class="rating-summary">
            <div class="rating-big">{avg_note}</div>
            <div><div class="stars-gold" style="font-size:18px;">{"⭐" * int(round(avg_note))}</div><div style="font-size:12px; font-weight:700; margin-top:3px;">Avis Vérifiés</div><div style="color:var(--text-muted); font-size:10px;">Basé sur {total_avis} retours clients</div></div>
        </div>
        <div>{reviews_html}</div>
        <hr style="border-color:var(--border-light); margin:14px 0;">
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
                <input type="text" name="nom" placeholder="Votre Nom" required>
                <input type="text" name="ville" placeholder="Votre Ville" required>
            </div>
            <textarea name="commentaire" placeholder="Votre avis sur notre configuration..." rows="2" required style="margin-top:6px;"></textarea>
            <button type="submit" class="btn-primary" style="padding:10px; font-size:11px;">⭐ PUBLIER MON AVIS</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item">
            <div class="faq-question"><span>Est-ce que ça configure tout même après un RESET TOTAL ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Oui, absolument à 100% !</b> Notre script recrée tout de A à Z : il configure le Port 1 pour recevoir Starlink, crée le Bridge LAN avec tous les ports physiques détectés, configure le serveur DHCP, active le Wi-Fi (Wi-Fi 6 ou Wireless selon le modèle), et applique le Mangle TTL et le pare-feu professionnel.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Puis-je choisir l'Adresse IP de mon Routeur ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-cyan);">Oui, tout à fait !</b> Dans le générateur, vous pouvez choisir votre IP (ex: 192.168.88.1, 192.168.1.1, 10.0.0.1 ou sur mesure). Le script configure la plage DHCP adaptée automatiquement.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>1 clé = combien de routeurs ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-red);">1 clé = 1 seul routeur (Usage Unique).</b> Une fois le script généré, la clé est définitivement consommée.</div>
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
    return render(f'<div class="card"><div class="alert alert-success"><b>✅ Commande enregistrée !</b></div><p style="font-size:13px; color:var(--text-body);">Merci <b>{nom}</b>. Pack <b>{TARIFS_MODULES[formule]["nom"]}</b> ({montant:,} Ar). Clé envoyée par SMS au <b>{tel}</b> après validation de <code>{ref}</code>.</p><a href="/" class="btn-primary">RETOUR</a></div>')

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé incorrecte ou expirée !</div><a href="/" class="btn-primary">Retour</a></div>')
    
    # VÉRIFICATION STRICTE EN BASE DE DONNÉES : SI DÉJÀ UTILISÉE => REFUS IMMÉDIAT
    if result.get("utilisations", 0) >= 1:
        return render('<div class="card"><div class="alert alert-error">❌ Cette clé a déjà été consommée pour configurer 1 routeur.<br><b>Règle : 1 Clé = 1 Routeur.</b><br>Veuillez commander une nouvelle clé.</div><a href="/" class="btn-primary">Retour à l\'Accueil</a></div>')
    
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
    
    # Double-vérification de la clé en base
    cle = session.get("licence")
    result = verifier_licence(cle)
    if not result or result.get("utilisations", 0) >= 1:
        session.clear()
        return render('<div class="card"><div class="alert alert-error">❌ Cette clé est déjà consommée.</div><a href="/" class="btn-primary">Retour</a></div>')
    
    plan_key = session.get("type_abo", "basic")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["basic"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])

    feat_html = "<div>✅ Bridge LAN + Ports Ethernet ajoutés automatiquement</div><div>✅ Port 1 configuré pour Starlink (DHCP-Client WAN)</div><div>✅ Serveur DHCP + NAT + IP Locale personnalisée</div><div>✅ Pare-feu Pro (Protection Input / Forward Stateful)</div><div>✅ Mangle TTL = 64 + DNS DoH Sécurisé</div>"
    dns_input_html = ""
    bandwidth_html = ""
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel WireGuard (gratuit à vie)</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Portail Hotspot Wi-Fi Zone</div>"
        dns_input_html = '<label>🔗 Adresse Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required>'
        bw_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            ck = "checked" if k == "illimite" else ""
            bw_html += f'<label style="background:#f8fafc; padding:8px; border-radius:8px; font-size:11px; display:flex; align-items:center; gap:8px; cursor:pointer; border:1px solid var(--border-light);"><input type="radio" name="bandwidth" value="{k}" {ck} style="width:auto; margin:0;"><b>{v["nom"]}</b> <span style="color:var(--text-muted);">({v["desc"]})</span></label>'
        bandwidth_html = f'<div class="wifi-box" style="border-color:rgba(124,58,237,0.3);"><div style="font-size:11px; font-weight:bold; color:var(--accent-purple); margin-bottom:8px;">📊 DÉBIT PAR CLIENT :</div><div style="display:grid; gap:6px;">{bw_html}</div><div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;"><input type="text" name="custom_down" value="3M" placeholder="Download"><input type="text" name="custom_up" value="1M" placeholder="Upload"></div></div>'
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ PPPoE + QoS Bandwidth</div>"

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span class="badge">{plan_info['nom']} • 1 Clé = 1 Routeur</span>
        <a href="/logout" style="color:var(--accent-red); font-size:11px; text-decoration:none;">Fermer</a>
    </div>
    <div class="card">
        <div class="card-title">⚙️ CONFIGURATION DE A À Z - {session['client']}</div>
        <div class="alert-warning" style="font-size:11px;">⚠️ <b>Attention :</b> Cette clé sera définitivement consommée dès que vous cliquerez sur Générer.</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>
            
            <label>2. Nom du client / Routeur :</label>
            <input type="text" name="client_final" placeholder="Boutique_Rasoa" required>

            <label>3. Adresse IP LAN du Routeur :</label>
            <select name="router_ip" required>
                <option value="192.168.88.1">192.168.88.1 (Standard MikroTik)</option>
                <option value="192.168.1.1">192.168.1.1 (Standard Box / Routeur)</option>
                <option value="10.0.0.1">10.0.0.1 (Format Entreprise)</option>
                <option value="172.16.0.1">172.16.0.1 (Format Réseau Pro)</option>
            </select>

            <div class="wifi-box" style="margin-top:10px;">
                <div style="font-size:11px; font-weight:bold; color:var(--accent-cyan); margin-bottom:6px;">📶 WI-FI (SSID + MOT DE PASSE)</div>
                <label>Nom du Wi-Fi (SSID) :</label>
                <input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe Wi-Fi :</label>
                <input type="text" name="wifi_pass" value="ketrika2025" required>
                {dns_input_html}
            </div>
            {bandwidth_html}
            <label>4. Inclus dans votre formule :</label>
            <div class="feature-box">{feat_html}</div>
            <button type="submit" class="btn-primary">🚀 GÉNÉRER LA CONFIG DE A À Z</button>
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
        return render('<div class="card"><div class="alert alert-error">❌ Cette clé a déjà été consommée pour un routeur.</div><a href="/" class="btn-primary">Retour à l\'Accueil</a></div>')
    
    modele = request.form.get("modele")
    plan_key = session.get("type_abo", "basic")
    client_final = request.form.get("client_final").replace(" ", "_")
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
    
    # 1. ENREGISTREMENT ET CONSOMMATION IMMÉDIATE DE LA CLÉ EN BASE DE DONNÉES
    sauvegarder_config(cle, client_final, modele, plan_key, options, warp_data, config_id)
    incrementer_utilisation(cle)
    
    # 2. VERROUILLAGE TOTAL : ACTIF = 0 DANS LA BASE
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("UPDATE licences SET actif=0, nb_utilisations=1 WHERE cle=?", (cle,))
    conn.commit()
    conn.close()

    # 3. DESTRUCTION DE LA SESSION POUR INTERDIRE TOUT RETOUR EN ARRIÈRE
    session.clear()

    host = request.host_url.replace("http://", "https://")
    online_cmd = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    cfg = get_config_by_id(config_id)
    raw_s = build_raw_script(cfg).replace('"', '\\"').replace('\n', ' ')
    one_liner = f'/system script add name=ketrika_run source="{raw_s}"; /system script run ketrika_run; /system script remove ketrika_run'

    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Configuration A à Z prête pour : {client_final} ({modele})</b></div>
        <div class="alert-warning">
            📍 <b>Branchement :</b> Starlink sur le <b>Port 1 (ether1)</b> | PC / Switch sur les <b>autres ports</b><br>
            📶 Wi-Fi: <b>{ssid}</b> | 🔑 Mot de passe: <b>{wifi_pass}</b> | 🌐 IP du Routeur: <b>{router_ip}</b><br>
            🔒 <i>Cette clé est maintenant définitivement consommée et verrouillée.</i>
        </div>
        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE (RECOMMANDÉE)</div>
        <div class="terminal-box" id="cmd1">{one_liner}</div>
        <button class="btn-copy" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE</button>
        <hr style="border-color:var(--border-light); margin:14px 0;">
        <div class="card-title">MÉTHODE 2 : FICHIER .RSC</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER LE FICHIER</a>
        <hr style="border-color:var(--border-light); margin:14px 0;">
        <div class="card-title">MÉTHODE 3 : SI ROUTEUR DÉJÀ CONNECTÉ</div>
        <div class="terminal-box" id="cmd2">{online_cmd}</div>
        <button class="btn-copy" id="b2" onclick="copyText('cmd2','b2')" style="background:linear-gradient(135deg,#64748b,#475569);">📋 COPIER</button>
        <a href="/" class="btn-primary" style="margin-top:14px;">🏠 TERMINER & RETOUR À L'ACCUEIL</a>
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
    return render(f'<div class="card"><div class="card-title">📋 COMMANDES ({len(cmds)})</div><table><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>{rows if rows else "<tr><td colspan=4 style=text-align:center>Aucune</td></tr>"}</table><a href="/admin/creer" class="btn-primary" style="margin-top:12px;">➕ CRÉER CLÉ</a></div>')

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
    return render('<div class="card"><div class="card-title">Créer Clé (1 Routeur)</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="basic">Basic (10k)</option><option value="standard">Standard (15k)</option><option value="warp">Blindé (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
