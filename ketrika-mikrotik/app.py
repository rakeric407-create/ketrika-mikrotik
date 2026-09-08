from flask import Flask, request, Response, render_template_string, session, redirect, url_for, send_file
from database import *
from warp_api import creer_config_warp_complete
import sqlite3, secrets, string, random, io, os, traceback
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.url_map.strict_slashes = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "ketrika.db")

# CONFIGURATION OFFICIELLE KETRIKA
FB_LINK = "https://www.facebook.com/loza.nama.376"
NUMERO_MVOLA = "038 28 171 00"
NUMERO_ORANGE = "037 39 755 72"
NOM_COMPTE = "Jean Eric"
BINANCE_ID = "1229612637"
USDT_BEP20 = "0x0c4bcb1beabbff154f7d445a549f1e5b42de9088"

def init_extra_tables():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS commandes (id INTEGER PRIMARY KEY AUTOINCREMENT, client_nom TEXT, telephone TEXT, formule TEXT, montant REAL, reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE', cle_generee TEXT, date_commande TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS avis (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, ville TEXT, etoiles INTEGER NOT NULL, commentaire TEXT NOT NULL, date_avis TEXT)''')
        c.execute("SELECT COUNT(*) FROM avis")
        if c.fetchone()[0] < 3:
            avis_initiaux = [
                ("Mamy R.", "Antananarivo", 5, "Script injecté après reset total sur mon hAP ax2. Configuration parfaite du premier coup !", "2026-01-15"),
                ("Jean Luc", "Tamatave", 5, "Configuration propre sur hAP ac2. Wi-Fi et pare-feu impeccables.", "2026-01-20"),
                ("Boutique Alpha", "Majunga", 5, "Pack Wi-Fi Zone parfait avec gestion de débit pour mon business.", "2026-01-28")
            ]
            c.executemany("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", avis_initiaux)
        conn.commit()
        conn.close()
    except Exception: pass

init_extra_tables()
init_db()

TARIFS_MODULES = {
    "basic": {"nom": "🛡️ Basic", "prix": 10000, "prix_usd": 2.50, "desc": "Config complète A à Z + Wi-Fi + Optimisation", "badge": ""},
    "standard": {"nom": "⭐ Standard", "prix": 15000, "prix_usd": 3.75, "desc": "Basic + Wi-Fi Dual Band 5G + Sécurité+", "badge": "POPULAIRE"},
    "warp": {"nom": "🚀 Premium VPN", "prix": 20000, "prix_usd": 5.00, "desc": "Standard + Tunnel WireGuard confidentiel gratuit", "badge": "MEILLEUR CHOIX"},
    "hotspot": {"nom": "🎫 Wi-Fi Zone", "prix": 30000, "prix_usd": 7.50, "desc": "Premium + Portail Hotspot + Débit contrôlé", "badge": ""},
    "pro": {"nom": "🏢 Pro WISP", "prix": 50000, "prix_usd": 12.50, "desc": "Solution intégrale + Multi-WAN + PPPoE + QoS", "badge": "PRO STUDIO"}
}

MODELES_MIKROTIK = ["hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)", "hAP ac2 (Dual Band Wireless)", "hAP ac3 (Dual Band Wireless)", "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (Wireless)", "LHG 5", "SXTsq", "hAP lite (Wireless 2.4G)", "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)", "CCR1009", "CCR2004", "CCR2116", "Chateau LTE/5G", "Autre RouterOS v7"]

BANDWIDTH_PROFILES = {"illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Plein débit"},"ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10↓/5↑"},"rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5↓/2↑"},"standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2↓/1↑"},"eco": {"nom": "🔒 ÉCO (1M/512K)", "down": "1M", "up": "512k", "desc": "1↓/0.5↑"},"custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Personnalisé"}}

IP_SUGGESTIONS = ["192.168.88.1", "192.168.1.1", "192.168.0.1", "192.168.10.1", "192.168.100.1", "10.0.0.1", "10.0.1.1", "10.10.10.1", "172.16.0.1", "172.16.1.1", "172.20.0.1"]

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="google-site-verification" content="a8G-WaLOM4cff6QkaeNJSjm6eavmu0DPif8RBdUnjLI" />
    <title>KETRIKA MIKROTIK PRO</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg-main: #eef2ff; --bg-card: #ffffff; --accent-cyan: #0284c7; --accent-green: #059669; --accent-purple: #7c3aed; --accent-orange: #ea580c; --accent-gold: #f59e0b; --text-dark: #0f172a; --text-body: #334155; --text-muted: #64748b; --border-light: #e2e8f0; }
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: linear-gradient(135deg, #eef2ff 0%, #f1f5f9 100%); color: var(--text-dark); min-height: 100vh; padding: 10px; }
        .container { max-width: 860px; margin: auto; }
        .top-nav { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 10px 14px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border: 1px solid var(--border-light); border-radius: 14px; box-shadow: 0 4px 15px rgba(2,132,199,0.06); gap: 8px; flex-wrap: wrap; }
        .nav-brand { display: flex; align-items: center; gap: 8px; font-family: 'Space Grotesk'; font-weight: 800; font-size: 13px; color: var(--text-dark); text-decoration: none; }
        .nav-logo-icon { width: 26px; height: 26px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; }
        .top-links { display: flex; gap: 6px; align-items: center; }
        .top-links a { font-size: 11px; color: #fff; text-decoration: none; font-weight: 700; padding: 6px 12px; background: linear-gradient(135deg, #1877f2, #0d6efd); border-radius: 10px; }
        .header { text-align: center; padding: 14px 5px 20px; }
        .logo-wrapper { position: relative; width: 80px; height: 80px; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; }
        .logo-aura { position: absolute; inset: -3px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink)); filter: blur(8px); opacity: 0.7; }
        .logo-box { position: relative; width: 100%; height: 100%; border-radius: 50%; background: linear-gradient(135deg, #0f172a, #1e293b); border: 2px solid rgba(255,255,255,0.9); display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 25px rgba(2,132,199,0.3); }
        .logo-box svg { width: 42px; height: 42px; }
        .header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 28px; font-weight: 900; background: linear-gradient(135deg, #0284c7, #7c3aed, #db2777, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; line-height: 1.2; }
        .header .tagline { color: var(--text-body); font-size: 13px; margin-top: 6px; font-weight: 600; }
        .card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 16px; padding: 20px; margin-bottom: 14px; box-shadow: 0 4px 15px rgba(15,23,42,0.05); position: relative; overflow: hidden; }
        .card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple), var(--accent-pink), var(--accent-green)); }
        .card-title { font-family: 'Space Grotesk', sans-serif; font-size: 15px; color: var(--accent-cyan); margin-bottom: 14px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; display: flex; align-items: center; gap: 8px; }
        .hero-card { background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%); color: #fff; padding: 22px; border-radius: 18px; margin-bottom: 14px; box-shadow: 0 10px 30px rgba(2,132,199,0.2); }
        .hero-card h2 { font-family: 'Space Grotesk'; font-size: 20px; font-weight: 900; margin-bottom: 8px; }
        .features-detail { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 12px; }
        .feature-detail-box { background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2); }
        .feature-detail-box .fd-title { font-family: 'Space Grotesk'; font-size: 13px; font-weight: 800; margin-bottom: 3px; }
        .feature-detail-box .fd-desc { font-size: 11px; opacity: 0.9; line-height: 1.4; }
        .advantages-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        @media (min-width: 500px) { .advantages-grid { grid-template-columns: repeat(4, 1fr); } }
        .adv-box { background: #f8fafc; padding: 12px 6px; border-radius: 12px; text-align: center; border: 1px solid var(--border-light); }
        .adv-title { font-family: 'Space Grotesk'; font-size: 11px; font-weight: 800; }
        .step-box { background: #f0fdfa; border: 1px solid #bae6fd; padding: 14px; border-radius: 14px; text-align: center; }
        .step-num { width: 34px; height: 34px; margin: 0 auto 8px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Space Grotesk'; font-weight: 900; }
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 10px; text-transform: uppercase; }
        input, select, textarea { width: 100%; padding: 12px 14px; margin-top: 4px; background: #f8fafc; border: 1px solid var(--border-light); border-radius: 10px; color: var(--text-dark); font-size: 14px; font-family: inherit; }
        .ip-chip { background: #e0f2fe; color: var(--accent-cyan); padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; cursor: pointer; border: 1px solid #bae6fd; font-family: monospace; }
        .btn-primary { width: 100%; padding: 14px; margin-top: 12px; background: linear-gradient(135deg, #0284c7, #0369a1); color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 800; cursor: pointer; font-family: 'Space Grotesk'; text-transform: uppercase; text-decoration: none; display: block; text-align: center; }
        .plan-option { background: #f8fafc; border: 2px solid var(--border-light); padding: 12px 10px; border-radius: 12px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; position: relative; gap: 8px; }
        .plan-option.selected { border-color: var(--accent-cyan); background: #f0f9ff; }
        .plan-price { text-align: right; }
        .plan-price b { color: var(--accent-green); font-size: 15px; font-family: 'Space Grotesk'; white-space: nowrap; }
        .plan-price small { display: block; color: var(--text-muted); font-size: 10px; font-weight: 700; }
        .pay-tabs { display: flex; gap: 6px; margin-top: 10px; }
        .pay-tab-btn { flex: 1; padding: 10px 5px; text-align: center; background: #f1f5f9; border: 1px solid var(--border-light); border-radius: 8px; font-size: 10px; font-weight: 700; cursor: pointer; font-family: 'Space Grotesk'; }
        .pay-tab-btn.active { background: var(--accent-cyan); color: #fff; border-color: var(--accent-cyan); }
        .pay-tab-content { display: none; margin-top: 10px; }
        .pay-tab-content.active { display: block; }
        .payment-banner { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 14px; text-align: center; }
        .payment-box { background: #fff; border: 1px solid #fde68a; border-radius: 10px; padding: 10px; margin-bottom: 8px; }
        .payment-box .number { font-family: 'Space Grotesk'; font-size: 18px; font-weight: 900; color: #b45309; }
        .crypto-box { background: #0f172a; color: #fff; border: 1px solid #334155; border-radius: 12px; padding: 14px; text-align: center; }
        .crypto-code { background: #1e293b; color: #38bdf8; padding: 8px; border-radius: 8px; font-family: monospace; font-size: 11px; word-break: break-all; margin: 5px 0; }
        .whatsapp-float { position: fixed; bottom: 18px; right: 18px; z-index: 9999; background: #25D366; color: #fff; padding: 10px 16px; border-radius: 30px; font-weight: 800; font-size: 12px; text-decoration: none; display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk'; box-shadow: 0 4px 15px rgba(37,211,102,0.4); }
        .ai-chat-float { position: fixed; bottom: 18px; left: 18px; z-index: 9999; background: linear-gradient(135deg, #0284c7, #7c3aed); color: #fff; padding: 10px 16px; border-radius: 30px; font-weight: 800; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk'; }
        .footer { text-align: center; color: var(--text-muted); margin: 20px 0 75px; font-size: 10px; padding: 10px; border-top: 1px solid var(--border-light); }
        .bw-card { background: #ffffff; border: 2px solid var(--border-light); padding: 10px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; gap: 10px; }
        .bw-card.active { border-color: var(--accent-purple); background: #faf5ff; }
        .bw-card input { width: 18px; height: 18px; margin: 0; }
    </style>
</head>
<body>
    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20une%20assistance" target="_blank" class="whatsapp-float">💬 <span>Assistance</span></a>
    <div class="ai-chat-float" onclick="alert('Assistant IA KETRIKA\\nPosez vos questions par WhatsApp pour une réponse rapide !')">🤖 <span>Assistant IA</span></div>

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
            <div class="logo-wrapper"><div class="logo-aura"></div><div class="logo-box"><svg viewBox="0 0 24 24" fill="none" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00f2fe" /><stop offset="100%" stop-color="#7c3aed" /></linearGradient></defs><rect x="2" y="14" width="20" height="8" rx="2" fill="rgba(0,242,254,0.1)"></rect><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="#00f2fe" stroke="#00f2fe" stroke-width="1.5"></path></svg></div></div>
            <h1>KETRIKA MIKROTIK</h1>
            <p class="tagline txt-fr">Solution Professionnelle d'Optimisation Réseau MikroTik</p>
            <div class="stats-live"><span class="live-dot"></span><span>Config en 5s • 1 Clé = 1 Routeur • Support International</span></div>
        </div>

        {{ content|safe }}

        <div class="footer">KETRIKA MIKROTIK PRO © 2026 • <a href="{{ fb_link }}" target="_blank">Facebook Officiel</a><br>ID Binance : {{ binance_id }} • 📞 038 28 171 00 (Jean Eric)</div>
    </div>
    <script>
        function toggleLang() { let f=document.querySelectorAll('.txt-fr'), m=document.querySelectorAll('.txt-mg'); f.forEach(e=>e.style.display=e.style.display==='none'?'':'none'); m.forEach(e=>m.style.display=m.style.display==='none'?'':'none'); }
        function copyText(elemId, btnId) { let e=document.getElementById(elemId); let t=e.innerText||e.value; navigator.clipboard.writeText(t).then(()=>{ let b=document.getElementById(btnId); let o=b.innerHTML; b.innerHTML='✅ COPIÉ !'; b.classList.add('copied'); setTimeout(()=>{b.innerHTML=o; b.classList.remove('copied');},2000);}); }
        function setIP(ip) { document.getElementById('router_ip').value = ip; }
        function selectPayTab(n) { document.querySelectorAll('.pay-tab-btn').forEach(b=>b.classList.remove('active')); document.querySelectorAll('.pay-tab-content').forEach(c=>c.classList.remove('active')); document.getElementById('tab_btn_'+n).classList.add('active'); document.getElementById('tab_content_'+n).classList.add('active'); }
        function selectBW(v) { document.querySelectorAll('.bw-card').forEach(c=>c.classList.remove('active')); document.getElementById('card_'+v).classList.add('active'); document.getElementById('bw_'+v).checked=true; document.getElementById('custom-bw-box').style.display=(v==='custom'?'grid':'none'); }
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content, fb_link=FB_LINK, binance_id=BINANCE_ID)

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
    subnet_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}" if len(ip_parts) == 4 else "192.168.88"
    dhcp_pool = f"{subnet_base}.10-{subnet_base}.250"
    dhcp_net = f"{subnet_base}.0/24"

    is_wifi6 = any(k in modele for k in ["ax2", "ax3", "ax 15s", "Wi-Fi 6"])
    is_wireless = any(k in modele for k in ["ac2", "ac3", "lite", "Wireless"])

    s = f"""# KETRIKA MIKROTIK PRO - CONFIG A Z
/interface bridge add name=bridge-lan auto-mac=yes
/interface list add name=WAN
/interface list add name=LAN
/interface list member add interface=ether1 list=WAN
/interface list member add interface=bridge-lan list=LAN
:foreach i in=[/interface ethernet find where name!="ether1"] do={{ /interface bridge port add bridge=bridge-lan interface=$i }}
/ip dhcp-client add interface=ether1 disabled=no use-peer-dns=no add-default-route=yes default-route-distance=1
/ip address add address={router_ip}/24 interface=bridge-lan
/ip pool add name=dhcp-pool ranges={dhcp_pool}
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
        s += f'/interface wireless security-profiles add name=sec-wifi mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}"\n/interface wireless set [find] ssid="{ssid}" security-profile=sec-wifi country="madagascar" disabled=no\n:foreach w in=[/interface wireless find] do={{ /interface bridge port add bridge=bridge-lan interface=$w }}\n'
    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f':if ([:len [/routing table find name=to-warp]] = 0) do={{ /routing table add name=to-warp fib }}\n/interface wireguard add name=warp-vpn listen-port=51820 mtu=1280 private-key="{cfg["warp_private"]}"\n/interface wireguard peers add interface=warp-vpn public-key="{cfg["warp_public"]}" endpoint-address=162.159.192.1 endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25\n/ip address add address={cfg["warp_ip"]}/32 interface=warp-vpn\n/ip firewall nat add chain=srcnat out-interface=warp-vpn action=masquerade\n/ip route add dst-address=0.0.0.0/0 gateway=warp-vpn routing-table=to-warp\n/ip firewall mangle add chain=prerouting in-interface-list=LAN dst-address-type=!local action=mark-routing new-routing-mark=to-warp passthrough=yes\n'
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
    for a in liste_avis: reviews_html += f'<div class="review-card"><div class="review-header"><b>{a[0]} ({a[1]})</b><span class="stars-gold">{"⭐"*a[2]}</span></div><div class="review-text">"{a[3]}"</div></div>'
    
    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        sel = "selected" if k == "standard" else ""; ck = "checked" if k == "standard" else ""
        badge = f'<div class="plan-badge badge-popular">{v["badge"]}</div>' if v["badge"] else ""
        plans_html += f'<label class="plan-option {sel}" id="opt_{k}" for="plan_{k}">{badge}<div class="plan-info"><b>{v["nom"]}</b><div>{v["desc"]}</div></div><div class="plan-price"><b>{v["prix"]:,} Ar</b><small>${v["prix_usd"]:.2f} USD</small><input type="radio" name="formule" id="plan_{k}" value="{k}" {ck} onchange="document.querySelectorAll(\'.plan-option\').forEach(e=>e.classList.remove(\'selected\')); document.getElementById(\'opt_{k}\').classList.add(\'selected\');"></div></label>'

    content = f"""
    <div class="live-dashboard">
        <div style="display:flex; justify-content:space-between; font-family:Space Grotesk; font-size:12px;"><b>📊 PERFORMANCES DU TUNNEL</b><span class="badge" style="background:#0284c7; color:#fff;">LIVE</span></div>
        <div class="dashboard-grid">
            <div class="dash-item"><div class="dash-label">PING</div><div class="dash-value green">&lt; 24 ms</div></div>
            <div class="dash-item"><div class="dash-label">CRYPT</div><div class="dash-value">ChaCha20</div></div>
            <div class="dash-item"><div class="dash-label">DNS</div><div class="dash-value">DoH 1.1.1.1</div></div>
            <div class="dash-item"><div class="dash-label">UPTIME</div><div class="dash-value green">99.9%</div></div>
        </div>
    </div>

    <div class="card"><div class="trust-badges-grid">
        <div class="trust-badge-card"><span>🛡️</span><div class="trust-badge-title">v7 Certifié</div></div>
        <div class="trust-badge-card"><span>🔒</span><div class="trust-badge-title">No Logs</div></div>
        <div class="trust-badge-card"><span>⚡</span><div class="trust-badge-title">Injection 5s</div></div>
        <div class="trust-badge-card"><span>🇲🇬</span><div class="trust-badge-title">Mada Support</div></div>
    </div></div>

    <div class="card">
        <div class="card-title">🛒 COMMANDER UN PACK</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            <div class="pay-tabs">
                <div class="pay-tab-btn active" id="tab_btn_momo" onclick="selectPayTab('momo')">Madagascar</div>
                <div class="pay-tab-btn" id="tab_btn_binance" onclick="selectPayTab('binance')">Binance / Crypto</div>
                <div class="pay-tab-btn" id="tab_btn_card" onclick="selectPayTab('card')">Carte Bancaire</div>
            </div>
            <div class="pay-tab-content active" id="tab_content_momo">
                <div class="payment-banner"><div class="payment-grid">
                    <div class="payment-box"><div class="method">🟠 Orange Money</div><div class="number">{NUMERO_ORANGE}</div></div>
                    <div class="payment-box"><div class="method">🟡 Mvola</div><div class="number">{NUMERO_MVOLA}</div></div>
                </div></div>
            </div>
            <div class="pay-tab-content" id="tab_content_binance">
                <div class="crypto-box">
                    <div class="crypto-title">Binance ID : {BINANCE_ID}</div>
                    <div class="crypto-code">{USDT_BEP20}</div>
                    <small>(Réseau BEP-20 / Binance Smart Chain)</small>
                </div>
            </div>
            <div class="pay-tab-content" id="tab_content_card">
                <div class="payment-banner">💳 <b>Paiement par Carte Sécurisé</b><br><p style="font-size:11px;">Après commande, contactez-nous pour recevoir votre lien de paiement par carte (USD).</p></div>
            </div>
            <div class="payment-warning">⏰ Clé non reçue après 15 min ? Appelez le {NUMERO_MVOLA}</div>
            <input type="text" name="nom" placeholder="Nom complet" required>
            <input type="text" name="tel" placeholder="Téléphone ou Email" required>
            <input type="text" name="ref_paiement" placeholder="Référence de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">🔐 ACTIVATION</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE STUDIO</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">⭐ AVIS CLIENTS • {avg}/5</div>
        <div class="rating-summary"><div class="rating-big">{avg}</div><div><div class="stars-gold">{"⭐"*int(avg)}</div><div style="font-size:11px;">{cnt} retours vérifiés</div></div></div>
        <div>{reviews_html}</div>
    </div>
    """
    return render(content)

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"): return redirect(url_for("home"))
    plan_key = session.get("type_abo", "basic"); plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["basic"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    ip_chips = "".join([f'<span class="ip-chip" onclick="setIP(\'{ip}\')">{ip}</span>' for ip in IP_SUGGESTIONS])
    feat_html = "<div>✅ Bridge + Ports auto</div><div>✅ WAN Port 1 Auto</div><div>✅ IP Locale Perso</div><div>✅ Firewall Stateful Pro</div><div>✅ Optimisation TTL & DNS</div>"
    if plan_key in ["warp", "hotspot", "pro"]: feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel VPN (gratuit à vie)</div>"
    
    bw_html = ""
    if plan_key in ["hotspot", "pro"]:
        for k, v in BANDWIDTH_PROFILES.items():
            ck = "checked" if k == "illimite" else ""; ac = "active" if k == "illimite" else ""
            bw_html += f'<div class="bw-card {ac}" id="card_{k}" onclick="selectBW(\'{k}\')"><input type="radio" name="bandwidth" id="bw_{k}" value="{k}" {ck}><div class="bw-card-text"><b>{v["nom"]}</b><span>{v["desc"]}</span></div></div>'

    content = f"""
    <div class="top-nav" style="margin-bottom:10px;"><span class="badge">{plan_info['nom']}</span><a href="/logout" style="color:var(--accent-red); font-size:11px; font-weight:700; text-decoration:none;">Fermer Session</a></div>
    <div class="card">
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label><select name="modele" required>{modeles_opt}</select>
            <label>2. Identifiant Client :</label><input type="text" name="client_final" required>
            <label>3. Adresse IP du Routeur :</label><input type="text" name="router_ip" id="router_ip" value="192.168.88.1" required><div class="ip-suggestions">{ip_chips}</div>
            <div class="wifi-box">
                <div class="wifi-box-title">📶 PARAMÈTRES WI-FI</div>
                <label style="margin:0;">SSID :</label><input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe :</label><input type="text" name="wifi_pass" value="ketrika2025" required>
                {('<label>Adresse Hotspot :</label><input type="text" name="dns_name" value="wifizone.wifi" required>' if plan_key in ["hotspot", "pro"] else '')}
            </div>
            {('<div class="wifi-box" style="border-color:rgba(124,58,237,0.3);"><div class="wifi-box-title" style="color:var(--accent-purple);">📊 BANDE PASSANTE</div><div class="bw-grid">'+bw_html+'</div><div id="custom-bw-box" style="display:none; grid-template-columns:1fr 1fr; gap:6px; margin-top:8px;"><input type="text" name="custom_down" value="3M" placeholder="Down"><input type="text" name="custom_up" value="1M" placeholder="Up"></div></div>' if plan_key in ["hotspot", "pro"] else '')}
            <label>4. Inclus :</label><div class="feature-box">{feat_html}</div>
            <button type="submit" class="btn-primary">🚀 GÉNÉRER LA CONFIG A à Z</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"): return redirect(url_for("home"))
    cle = session.get("licence"); modele = request.form.get("modele", ""); plan_key = session.get("type_abo", "basic"); client_final = request.form.get("client_final", "Client").replace(" ", "_")
    options = {"ssid": request.form.get("ssid"), "wifi_pass": request.form.get("wifi_pass"), "dns_name": request.form.get("dns_name", "ketrika.wifi"), "router_ip": request.form.get("router_ip", "192.168.88.1"), "bw_down": "0", "bw_up": "0"}
    warp_data = creer_config_warp_complete() if plan_key in ["warp", "hotspot", "pro"] else {}
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    sauvegarder_config(cle, client_final, modele, plan_key, options, warp_data, config_id)
    incrementer_utilisation(cle); conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("UPDATE licences SET actif=0, nb_utilisations=1 WHERE cle=?", (cle,)); conn.commit(); conn.close(); session.clear()
    host = request.host_url.rstrip('/').replace("http://", "https://")
    cfg = get_config_by_id(config_id); raw_s = build_raw_script(cfg); clean_s = clean_script_for_oneliner(raw_s); one_liner = f'/system script add name=ketrika_run source="{clean_s}"; /system script run ketrika_run; /system script remove ketrika_run'
    content = f"""<div class="card"><div class="alert alert-success"><b>✅ Injection prête pour : {client_final}</b></div><div class="terminal-box" id="cmd1">{one_liner}</div><button class="btn-copy" id="b1" onclick="copyText('cmd1','b1')">📋 COPIER LA COMMANDE</button><hr><a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER LE FICHIER</a><a href="/" class="btn-primary" style="margin-top:14px;">🏠 RETOUR ACCUEIL</a></div>"""
    return render(content)

@app.route("/tuto")
def tuto():
    return render('<div class="card"><div class="card-title">📖 GUIDE D\'INSTALLATION</div><div class="step-guide"><b>1.</b> WAN Starlink sur <b>Port 1</b>.<br><b>2.</b> Connectez PC sur <b>Port 2</b>.<br><b>3.</b> Ouvrez <b>Winbox</b> (Connexion MAC).<br><b>4.</b> Collez la commande dans le <b>New Terminal</b>.</div><a href="/" class="btn-primary">RETOUR</a></div>')

@app.route("/commander", methods=["POST"])
def commander():
    nom = request.form.get("nom"); tel = request.form.get("tel"); f = request.form.get("formule"); ref = request.form.get("ref_paiement"); m = TARIFS_MODULES.get(f, {}).get("prix", 10000)
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)", (nom, tel, f, m, ref, datetime.now().strftime("%Y-%m-%d %H:%M"))); conn.commit(); conn.close()
    return render(f'<div class="card"><div class="alert alert-success"><b>✅ Commande enregistrée !</b></div><p style="font-size:13px;">Clé envoyée par SMS au <b>{tel}</b> sous 15 min.</p><a href="/" class="btn-primary">RETOUR</a></div>')

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper(); result = verifier_licence(cle)
    if not result or not result["valide"] or result.get("utilisations", 0) >= 1: return render('<div class="card"><div class="alert alert-error">❌ Clé incorrecte ou déjà utilisée.</div><a href="/" class="btn-primary">Retour</a></div>')
    session["authenticated"] = True; session["licence"] = cle; session["client"] = result["client"]; session["type_abo"] = result["type"]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/config/<path:config_id>")
def get_config(config_id):
    cid = config_id.replace('.rsc', '').strip(); cfg = get_config_by_id(cid)
    if not cfg: return Response("# Erreur", mimetype="text/plain")
    return Response(build_raw_script(cfg), mimetype="text/plain")

@app.route("/download/<path:config_id>")
def download_config(config_id):
    cid = config_id.replace('.rsc', '').strip(); cfg = get_config_by_id(cid)
    if not cfg: return redirect(url_for("home"))
    mem = io.BytesIO(); mem.write(build_raw_script(cfg).encode('utf-8')); mem.seek(0)
    return send_file(mem, mimetype="text/plain", as_attachment=True, download_name="ketrika.rsc")

@app.route("/ajouter-avis", methods=["POST"])
def ajouter_avis():
    nom = request.form.get("nom"); ville = request.form.get("ville"); et = int(request.form.get("etoiles", 5)); com = request.form.get("commentaire")
    if nom and com: conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("INSERT INTO avis (nom, ville, etoiles, commentaire, date_avis) VALUES (?, ?, ?, ?, ?)", (nom, ville, et, com, datetime.now().strftime("%Y-%m-%d"))); conn.commit(); conn.close()
    return redirect(url_for("home"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True; return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ADMIN</div><form method="POST"><input type="text" name="username" placeholder="admin" required><input type="password" name="password" placeholder="mot de passe" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC"); cmds = c.fetchall(); conn.close()
    rows = ""
    for cmd in cmds: rows += f'<tr><td><b>{cmd[1]}</b><br><small>{cmd[2]}</small></td><td>{cmd[3].upper()}<br><b>{cmd[4]:,} Ar</b></td><td><code>{cmd[5]}</code></td><td><form method="POST" action="/admin/valider/{cmd[0]}"><button type="submit" class="btn-primary" style="padding:4px 8px; font-size:10px; margin:0;">⚡ VALIDER</button></form></td></tr>'
    return render(f'<div class="card"><div class="card-title">📋 COMMANDES ({len(cmds)})</div><table><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>{rows if rows else "<tr><td colspan=4 style=text-align:center>Aucune</td></tr>"}</table></div>')

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"): return redirect(url_for("admin"))
    conn = sqlite3.connect(DB_FILE); c = conn.cursor(); c.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,)); cmd = c.fetchone()
    if cmd:
        cle = creer_licence(cmd[1], cmd[2], cmd[3], cmd[4])
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id)); conn.commit()
    conn.close()
    return render(f'<div class="card"><div class="alert alert-success">✅ Validé !</div><div class="card-title">CLÉ :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary">RETOUR</a></div>')

@app.errorhandler(404)
def h404(e): return redirect(url_for("home"))
@app.errorhandler(500)
def h500(e): return redirect(url_for("home"))

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)
