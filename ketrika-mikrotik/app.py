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

def init_commandes_table():
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_nom TEXT,
        telephone TEXT,
        formule TEXT,
        montant REAL,
        reference_paiement TEXT,
        statut TEXT DEFAULT 'EN_ATTENTE',
        cle_generee TEXT,
        date_commande TEXT
    )''')
    conn.commit()
    conn.close()

init_commandes_table()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "base": {"nom": "🛡️ Pack Essentiel (Anti-Bridage)", "prix": 10000, "desc": "TTL 64 + DNS DoH + Blocage IPv6 & Torrents + Wi-Fi 2.4G/5G"},
    "warp": {"nom": "🚀 Pack Blindé (Tunnel WARP VPN)", "prix": 20000, "desc": "Pack Essentiel + Chiffrement Total WireGuard + Wi-Fi 2.4G/5G"},
    "hotspot": {"nom": "🎫 Pack Wi-Fi Zone (Hotspot + VPN)", "prix": 30000, "desc": "Pack Blindé + Système Tickets Hotspot + Wi-Fi + DNS Perso"},
    "pro": {"nom": "🏢 Pack Pro WISP (PPPoE + Hotspot + VPN)", "prix": 50000, "desc": "Solution intégrale pour revendeurs & WISP + DNS Perso"}
}

MODELES_MIKROTIK = [
    "hAP ax2 (Dual Band Wi-Fi 6 2.4G/5G)", "hAP ax3 (Dual Band Wi-Fi 6 2.4G/5G)",
    "hAP ac2 (Dual Band 2.4G/5G)", "hAP ac3 (Dual Band 2.4G/5G)",
    "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s (5GHz)", "LHG 5 (5GHz)", "SXTsq (5GHz)", "hAP lite (2.4GHz)",
    "RB750Gr3 (hEX - Sans Wi-Fi)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)",
    "CCR1009", "CCR2004", "CCR2116",
    "Chateau LTE/5G (Dual Band)", "Autre RouterOS v7"
]

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK PRO v2.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #030712;
            --card-bg: #0b0f19;
            --accent-cyan: #00f2fe;
            --accent-green: #10b981;
            --accent-glow: rgba(0, 242, 254, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg-dark); 
            color: var(--text-main); 
            min-height: 100vh; 
            padding: 20px; 
            background-image: radial-gradient(circle at 50% -10%, rgba(0, 242, 254, 0.08), transparent 50%),
                              radial-gradient(circle at 10% 90%, rgba(16, 185, 129, 0.03), transparent 30%);
            background-attachment: fixed;
        }
        .container { max-width: 850px; margin: auto; }
        
        /* HEADER */
        .header { text-align: center; padding: 30px 0; position: relative; }
        .header h1 { 
            font-family: 'Space Grotesk', sans-serif; 
            font-size: 34px; 
            font-weight: 700; 
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green)); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        .header p { color: var(--text-muted); font-size: 14px; margin-top: 6px; font-weight: 300; }

        /* CARDS */
        .card { 
            background: var(--card-bg); 
            border: 1px solid rgba(255, 255, 255, 0.04); 
            border-radius: 18px; 
            padding: 28px; 
            margin-bottom: 25px; 
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6); 
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-green), transparent);
        }
        .card-title { 
            font-family: 'Space Grotesk', sans-serif; 
            font-size: 16px; 
            color: var(--accent-cyan); 
            margin-bottom: 15px; 
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* FORMS */
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 15px; text-transform: uppercase; letter-spacing: 1px; }
        input, select { 
            width: 100%; 
            padding: 14px; 
            margin-top: 6px; 
            background: #111524; 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 10px; 
            color: #fff; 
            font-size: 15px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
        }
        input:focus, select:focus { 
            outline: none; 
            border-color: var(--accent-cyan); 
            box-shadow: 0 0 15px var(--accent-glow); 
            background: #151b2e;
        }

        /* BUTTONS */
        .btn-primary { 
            width: 100%; 
            padding: 16px; 
            margin-top: 20px; 
            background: linear-gradient(135deg, #00f2fe, #4facfe); 
            color: #030712; 
            border: none; 
            border-radius: 10px; 
            font-size: 15px; 
            font-weight: 700; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            font-family: 'Space Grotesk', sans-serif; 
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .btn-primary:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(0, 242, 254, 0.35); 
        }
        .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }
        .btn-success:hover { box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3); }

        /* PLAN SELECTOR */
        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 12px; margin-top: 10px; }
        .plan-option { 
            background: #101524; 
            border: 1px solid rgba(255, 255, 255, 0.05); 
            padding: 16px; 
            border-radius: 12px; 
            cursor: pointer; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            transition: all 0.3s ease;
        }
        .plan-option:hover {
            border-color: var(--accent-cyan);
            background: #141b2f;
        }
        .plan-option input { width: 18px; height: 18px; accent-color: var(--accent-cyan); margin: 0; cursor: pointer; }

        /* PAYMENT BANNER */
        .payment-banner { 
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.03)); 
            border: 1px solid rgba(245, 158, 11, 0.3); 
            border-radius: 12px; 
            padding: 20px; 
            margin-top: 20px; 
            text-align: center; 
        }
        .payment-phone { 
            font-family: 'Space Grotesk', sans-serif; 
            font-size: 30px; 
            color: #f59e0b; 
            margin: 8px 0; 
            font-weight: 700; 
            letter-spacing: 2px; 
            text-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
        }

        /* TERMINAL BOX */
        .terminal-box { 
            background: #040711; 
            border: 1px solid var(--accent-green); 
            color: var(--accent-green); 
            padding: 18px; 
            border-radius: 10px; 
            font-family: 'Courier New', monospace; 
            font-size: 13px; 
            word-break: break-all; 
            margin-top: 12px; 
            line-height: 1.5; 
            box-shadow: 0 5px 15px rgba(16, 185, 129, 0.1);
        }

        .badge { 
            background: rgba(0, 242, 254, 0.08); 
            color: var(--accent-cyan); 
            padding: 5px 12px; 
            border-radius: 20px; 
            font-size: 11px; 
            font-weight: 600;
            border: 1px solid rgba(0, 242, 254, 0.25); 
            letter-spacing: 0.5px;
        }
        .alert { padding: 14px; border-radius: 10px; margin-bottom: 15px; font-size: 13px; line-height: 1.5; }
        .alert-success { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #a7f3d0; }
        .alert-error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5; }
        .alert-warning { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #fde68a; }
        
        .feature-box { background: #101524; padding: 18px; border-radius: 12px; margin-top: 12px; line-height: 2; font-size: 13px; border-left: 4px solid var(--accent-cyan); }
        .wifi-box { background: #101524; border: 1px dashed rgba(0, 242, 254, 0.2); padding: 18px; border-radius: 12px; margin-top: 15px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        table th, table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; }
        table th { color: var(--accent-cyan); font-family: 'Space Grotesk', sans-serif; font-weight: 600; }
        
        .footer { text-align: center; color: var(--text-muted); opacity: 0.8; margin-top: 35px; font-size: 11px; font-weight: 300; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p>Technologie Avancée d'Optimisation Réseau & Protection Starlink</p>
        </div>
        {{ content|safe }}
        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • Ingénierie Réseau Avancée • Support : 038 28 171 00
        </div>
    </div>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content)

def build_raw_script(cfg):
    plan = cfg["type"]
    opt = cfg.get("options", {})
    ssid = opt.get("ssid", "STARLINK-KETRIKA")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    dns_name = opt.get("dns_name", "ketrika.wifi")
    
    s = f"# ==========================================\n# KETRIKA MIKROTIK - {cfg['client']} ({cfg['modele']})\n# Pack Actif : {plan.upper()}\n# ==========================================\n"
    
    # 1. SOCLE ANTI-BRIDAGE STARLINK
    s += '/ip firewall mangle remove [find comment="KETRIKA-TTL"]\n/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"\n'
    s += '/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes\n/ip firewall nat remove [find comment="KETRIKA-DNS"]\n/ip firewall nat add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n'
    s += '/ipv6 settings set disable-ipv6=yes\n'
    s += '/ip firewall filter remove [find comment="KETRIKA-P2P"]\n/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P"\n'
    
    # 2. GESTION WI-FI DUAL-BAND (2.4 GHz + 5 GHz)
    s += f"""
# --- CONFIGURATION WI-FI DUAL BAND (2.4 GHz & 5 GHz) ---
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
    /interface wireless security-profiles add name=ketrika-sec mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}" unicast-ciphers=aes-ccm group-ciphers=aes-ccm
    
    /interface wireless set [find] ssid="{ssid}" security-profile=ketrika-sec disabled=no
    /interface wireless set [find band~"2ghz"] band=2ghz-b/g/n channel-width=20/40mhz-XX country="madagascar"
    /interface wireless set [find band~"5ghz"] band=5ghz-a/n/ac channel-width=20/40/80mhz-XXXX country="madagascar"
}} on-error={{}};
"""

    # 3. VPN WARP (20k, 30k, 50k)
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

    # 4. HOTSPOT WI-FI ZONE AVEC DNS PERSONNALISABLE (30k, 50k)
    if plan in ["hotspot", "pro"]:
        s += f"""/ip pool add name=ketrika-hs-pool ranges=10.5.50.10-10.5.50.254
/ip dhcp-server add name=ketrika-hs-dhcp interface=bridge address-pool=ketrika-hs-pool disabled=no
/ip hotspot profile add name=ketrika-hs hotspot-address=10.5.50.1 dns-name={dns_name}
/ip hotspot add name=hs-ketrika interface=bridge address-pool=ketrika-hs-pool profile=ketrika-hs disabled=no
"""

    # 5. PACK PRO (50k)
    if plan == "pro":
        s += """/ip pool add name=ketrika-ppp-pool ranges=10.10.10.2-10.10.10.254
/ppp profile add name=ketrika-ppp local-address=10.10.10.1 remote-address=ketrika-ppp-pool dns-server=1.1.1.1
/interface pppoe-server server add service-name=KETRIKA-NET interface=bridge default-profile=ketrika-ppp disabled=no
/queue type add name=pcq-download kind=pcq pcq-rate=5M pcq-classifier=dst-address
/queue type add name=pcq-upload kind=pcq pcq-rate=2M pcq-classifier=src-address
/queue simple add name=KETRIKA-QOS target=10.5.50.0/24 queue=pcq-upload/pcq-download comment="KETRIKA-QOS"
"""
    return s

@app.route("/")
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "base" else ""
        plans_html += f"""
        <label class="plan-option" for="plan_{k}">
            <div>
                <b style="color:#fff; font-size:14px;">{v['nom']}</b>
                <div style="color:var(--text-muted); font-size:12px; margin-top:3px;">{v['desc']}</div>
            </div>
            <div style="text-align:right;">
                <b style="color:var(--accent-green); font-size:16px;">{v['prix']:,} Ar</b><br>
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked}>
            </div>
        </label>
        """
    
    content = f"""
    <div class="card">
        <div class="card-title">🛒 1. CHOISIR VOTRE CONFIGURATION</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            <div style="background:#111524; padding:18px; border-radius:12px; margin-top:15px; border-left:4px solid #f59e0b; border-right:1px solid rgba(245, 158, 11, 0.15); border-top:1px solid rgba(245, 158, 11, 0.15); border-bottom:1px solid rgba(245, 158, 11, 0.15);">
                <b style="color:#f59e0b; font-size:13px; font-family:'Space Grotesk';">📱 DEBITEZ ET ENVOYEZ LE PAIEMENT</b>
                <div style="font-size:13px; color:#fff; margin-top:4px;">Versez la somme correspondante au numéro :</div>
                <div class="payment-phone">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted);">Mvola / Orange Money / Airtel Money</small>
            </div>
            <label>Votre Nom complet :</label>
            <input type="text" name="nom" placeholder="Ex: Rakoto Jean" required>
            <label>Votre Numéro de Téléphone :</label>
            <input type="text" name="tel" placeholder="Ex: 034 00 000 00" required>
            <label>Référence de la transaction :</label>
            <input type="text" name="ref_paiement" placeholder="Ex: Code de transaction reçu par SMS" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">🔐 2. ACCÉDER AU SYSTÈME D'ACTIVATION</div>
        <form method="POST" action="/login">
            <label>Clé de Licence :</label>
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1px;">
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

    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)",
              (nom, tel, formule, montant, ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Demande de commande soumise !</b></div>
        <p style="font-size:14px; line-height:1.6; color:var(--text-muted);">
            Merci <b style="color:#fff;">{nom}</b>. Votre demande d'activation pour le pack <b style="color:#fff;">{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar) est enregistrée.<br><br>
            Notre équipe valide la référence de paiement <code style="color:var(--accent-cyan);">{ref}</code> et vous envoie la clé par SMS au <b style="color:#fff;">{tel}</b> d'ici quelques instants.
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
        return render('<div class="card"><div class="alert alert-error">❌ Clé de licence incorrecte ou expirée !</div><a href="/" class="btn-primary">Retour</a></div>')
    
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

    feat_html = "<div>✅ Masquage TTL = 64 (Optimisé Starlink)</div><div>✅ DNS Sécurisé DoH Cloudflare</div><div>✅ Bloqueur IPv6 & Anti-Fuite</div><div>✅ Wi-Fi Dual Band Haute Performance</div>"
    
    dns_input_html = ""
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel Crypté WireGuard Cloudflare WARP</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Portail Captif Hotspot (Wi-Fi Zone)</div>"
        # Ajout du champ dynamique pour choisir l'adresse DNS du Hotspot !
        dns_input_html = """
        <label>🔗 Adresse DNS / Page de connexion du Hotspot :</label>
        <input type="text" name="dns_name" value="wifizone.wifi" placeholder="Ex: wifizone.wifi ou monwifi.net" required>
        <small style="color:var(--text-muted); font-size:11px; display:block; margin-top:4px;">C'est l'adresse que vos clients tapent pour se connecter (ex: wifizone.wifi).</small>
        """
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ Serveur d'abonnements PPPoE + PCQ Bandwidth QoS</div>"

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span class="badge">Niveau : {plan_info['nom']}</span>
        <a href="/logout" style="color:#ef4444; font-size:12px; text-decoration:none;">Fermer Session</a>
    </div>

    <div class="card">
        <div class="card-title">⚙️ GÉNÉRATEUR MIKROTIK - {session['client']}</div>
        <form method="POST" action="/generate">
            <label>1. Modèle de matériel MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Identifiant du client final :</label>
            <input type="text" name="client_final" placeholder="Ex: Boutique_Rasoa" required>

            <div class="wifi-box">
                <div style="font-size:13px; font-weight:bold; color:var(--accent-cyan); margin-bottom:8px;">📶 PARAMÈTRES WI-FI (2.4 GHz + 5 GHz)</div>
                
                <label>Nom du Wi-Fi (SSID) :</label>
                <input type="text" name="ssid" value="STARLINK-KETRIKA" required>

                <label>Mot de passe Wi-Fi :</label>
                <input type="text" name="wifi_pass" value="ketrika2025" placeholder="Minimum 8 caractères" required>
                
                {dns_input_html}
            </div>

            <label style="margin-top:15px;">3. Modules inclus dans votre clé :</label>
            <div class="feature-box">
                {feat_html}
            </div>

            <button type="submit" class="btn-primary">GÉNÉRER LE SCRIPT UNIQUE ({plan_info['prix']:,} Ar)</button>
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
    ssid = request.form.get("ssid", "STARLINK-KETRIKA")
    wifi_pass = request.form.get("wifi_pass", "ketrika2025")
    dns_name = request.form.get("dns_name", "ketrika.wifi")
    
    options = {"ssid": ssid, "wifi_pass": wifi_pass, "dns_name": dns_name}
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
        <div class="alert alert-success"><b>✅ Script généré pour : {client_final} ({modele})</b></div>
        <div class="alert alert-warning">
            📶 <b>Wi-Fi Configuration :</b> Nom: <b>{ssid}</b> | Mot de passe: <b>{wifi_pass}</b><br>
            <i>Conseil : Connectez-vous sur l'adresse MAC dans Winbox pour éviter la déconnexion !</i>
        </div>

        <div class="card-title">MÉTHODE 1 (RECOMMANDÉE) : COMMANDE UNIQUE (ANTI-DÉCONNEXION)</div>
        <p style="font-size:12px; color:var(--text-muted);">Copiez cette ligne et collez-la dans <b>Winbox ➡️ New Terminal</b> :</p>
        <div class="terminal-box">{one_liner}</div>

        <hr style="border-color:#2d3748; margin:20px 0;">

        <div class="card-title">MÉTHODE 2 : TÉLÉCHARGER LE FICHIER (.RSC)</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success" style="margin-top:10px;">📥 TÉLÉCHARGER KETRIKA.RSC</a>

        <hr style="border-color:#2d3748; margin:20px 0;">

        <div class="card-title">MÉTHODE 3 : SI LE ROUTEUR EST DÉJÀ EN LIGNE</div>
        <div class="terminal-box">{online_cmd}</div>

        <a href="/dashboard" class="btn-primary" style="margin-top:20px;">NOUVELLE CONFIGURATION</a>
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
    
    return send_file(
        mem_file,
        mimetype="text/plain",
        as_attachment=True,
        download_name="ketrika.rsc"
    )

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
    return render('<div class="card"><div class="card-title">🔐 ACCÈS ADMIN</div><form method="POST"><input type="text" name="username" placeholder="admin" required><input type="password" name="password" placeholder="mot de passe" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

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
                    <button type="submit" class="btn-primary" style="padding:6px 10px; font-size:11px; margin:0;">⚡ VALIDER</button>
                </form>
            </td>
        </tr>
        """

    return render(f"""
    <div class="card">
        <div class="card-title">📋 COMMANDES EN ATTENTE ({len(commandes)})</div>
        <table>
            <tr><th>Client / Tél</th><th>Pack / Prix</th><th>Réf Paiement</th><th>Action</th></tr>
            {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Aucune commande en attente</td></tr>'}
        </table>
        <a href="/admin/creer" class="btn-primary" style="margin-top:20px;">➕ CRÉER UNE CLÉ MANUELLE</a>
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
        <div class="alert alert-success">✅ Commande validée pour {cmd[1]} ({cmd[3].upper()}) !</div>
        <div class="card-title">CLÉ À ENVOYER PAR SMS AU {cmd[2]} :</div>
        <div class="terminal-box">{cle}</div>
        <a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">RETOUR AUX COMMANDES</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">Dashboard</a></div>')
    return render("""<div class="card"><div class="card-title">Créer une Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="base">Pack Essentiel (10k)</option><option value="warp">Pack Blindé (20k)</option><option value="hotspot">Pack Hotspot (30k)</option><option value="pro">Pack Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
