from flask import Flask, request, Response, render_template_string, session, redirect, url_for, jsonify
from database import *
from warp_api import creer_config_warp_complete
import secrets
import string
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Initialisation base de données
init_db()

# ==========================================
# CONFIGURATION
# ==========================================
NUMERO_PAIEMENT = "038 28 171 00"

TARIFS = {
    "jour": {"prix": 5000, "nom": "1 Jour", "duree": "24h"},
    "semaine": {"prix": 20000, "nom": "1 Semaine", "duree": "7 jours"},
    "mois": {"prix": 50000, "nom": "1 Mois", "duree": "30 jours"},
    "annee": {"prix": 300000, "nom": "1 An", "duree": "365 jours"},
    "vie": {"prix": 800000, "nom": "À VIE", "duree": "Illimité"}
}

MODELES_MIKROTIK = [
    "hAP ax2", "hAP ax3", "hAP ac2", "hAP ac3", "hAP lite",
    "RB750Gr3", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011",
    "CCR1009", "CCR2004", "CCR2116",
    "mANTBox ax 15s", "mANTBox 19s", "LHG 5", "SXTsq",
    "Chateau LTE", "Chateau 5G", "Autre RouterOS v7"
]

# ==========================================
# TEMPLATES HTML
# ==========================================
HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK - {{ title }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); min-height: 100vh; color: #333; padding: 15px; }
        .container { max-width: 800px; margin: auto; }
        .logo { text-align: center; color: white; margin-bottom: 25px; padding: 20px; }
        .logo h1 { font-size: 36px; letter-spacing: 3px; text-shadow: 2px 2px 8px rgba(0,0,0,0.5); }
        .logo p { opacity: 0.9; margin-top: 8px; font-size: 14px; }
        .card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 15px 40px rgba(0,0,0,0.3); margin-bottom: 20px; }
        h2 { color: #0f2027; margin-bottom: 20px; border-bottom: 3px solid #2c5364; padding-bottom: 10px; }
        h3 { color: #203a43; margin: 15px 0 10px; }
        label { display: block; margin-top: 15px; font-weight: bold; color: #444; }
        input, select { width: 100%; padding: 13px; margin-top: 8px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; transition: 0.3s; }
        input:focus, select:focus { outline: none; border-color: #2c5364; box-shadow: 0 0 10px rgba(44,83,100,0.2); }
        button, .btn { width: 100%; padding: 15px; margin-top: 20px; background: linear-gradient(135deg, #0f2027, #2c5364); color: white; border: none; border-radius: 8px; font-size: 17px; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; transition: 0.3s; }
        button:hover, .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        .btn-danger { background: linear-gradient(135deg, #dc3545, #a71d2a); }
        .btn-success { background: linear-gradient(135deg, #28a745, #1e7e34); }
        .checkbox-group { padding: 15px; background: #f8f9fa; border-radius: 8px; margin-top: 10px; border-left: 4px solid #2c5364; }
        .checkbox-group label { display: flex; align-items: center; margin-top: 10px; font-weight: normal; cursor: pointer; }
        .checkbox-group input { width: auto; margin-right: 10px; transform: scale(1.3); }
        .command-box { background: linear-gradient(135deg, #1a1a2e, #0f0f1e); color: #00ff88; padding: 20px; border-radius: 10px; margin-top: 15px; font-family: 'Courier New', monospace; word-break: break-all; font-size: 13px; border: 1px solid #00ff88; }
        .payment-box { background: linear-gradient(135deg, #fff3cd, #ffe69c); border-left: 5px solid #ffc107; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .payment-box b { color: #d9534f; font-size: 26px; display: block; margin: 10px 0; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .info { background: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .tarifs { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 15px; }
        .tarif-card { background: #f8f9fa; border: 2px solid #ddd; padding: 15px; border-radius: 10px; text-align: center; transition: 0.3s; }
        .tarif-card:hover { border-color: #2c5364; transform: scale(1.05); }
        .tarif-card b { color: #0f2027; font-size: 18px; }
        .tarif-card .prix { color: #dc3545; font-size: 22px; font-weight: bold; margin: 10px 0; }
        .nav { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .nav a { flex: 1; text-align: center; padding: 10px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; border-radius: 8px; }
        .nav a:hover { background: rgba(255,255,255,0.3); }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: linear-gradient(135deg, #2c5364, #203a43); color: white; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-card b { font-size: 28px; display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        table th, table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; font-size: 13px; }
        table th { background: #2c5364; color: white; }
        .footer { text-align: center; color: white; opacity: 0.7; margin-top: 30px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p>Solution Anti-Bridage Starlink & Automatisation Pro</p>
        </div>
        {{ content|safe }}
        <div class="footer">© 2025 KETRIKA MIKROTIK | Contact: 038 28 171 00</div>
    </div>
</body>
</html>
"""

def render(title, content):
    return render_template_string(HTML_BASE, title=title, content=content)

# ==========================================
# ROUTES CLIENT
# ==========================================
@app.route("/")
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    tarifs_html = ""
    for key, t in TARIFS.items():
        tarifs_html += f"""
        <div class="tarif-card">
            <b>{t['nom']}</b>
            <div class="prix">{t['prix']:,} Ar</div>
            <small>{t['duree']}</small>
        </div>"""
    
    content = f"""
    <div class="card">
        <h2>🔐 Connexion</h2>
        <form method="POST" action="/login">
            <label>Clé de licence :</label>
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase;">
            <button type="submit">Se connecter</button>
        </form>
    </div>
    
    <div class="card">
        <h2>💰 Nos Tarifs</h2>
        <div class="tarifs">{tarifs_html}</div>
        <div class="payment-box">
            <p><b style="color:#333; font-size:16px;">📱 Pour obtenir votre clé :</b></p>
            <p>1. Envoyez le montant via Mobile Money au numéro :</p>
            <b>{NUMERO_PAIEMENT}</b>
            <p>2. Envoyez votre référence de paiement par SMS</p>
            <p>3. Recevez votre clé de licence en quelques minutes</p>
            <p style="margin-top:10px;">✅ Mvola | ✅ Orange Money | ✅ Airtel Money</p>
        </div>
    </div>
    
    <div class="card">
        <h2>🎯 Fonctionnalités</h2>
        <ul style="line-height:2; padding-left:20px;">
            <li>✅ Configuration automatique pour tous MikroTik</li>
            <li>✅ Anti-bridage Starlink (TTL, DNS, IPv6)</li>
            <li>✅ VPN Cloudflare WARP unique par client</li>
            <li>✅ Hotspot avec tickets Wi-Fi</li>
            <li>✅ Serveur PPPoE pour abonnements</li>
            <li>✅ Installation en 5 secondes</li>
            <li>✅ Support technique inclus</li>
        </ul>
    </div>
    """
    return render("Accueil", content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    
    if not result:
        content = '<div class="card"><div class="error">❌ Clé introuvable !</div><a href="/" class="btn">Retour</a></div>'
        return render("Erreur", content)
    
    if not result["valide"]:
        content = f'<div class="card"><div class="error">❌ {result["raison"]}</div><a href="/" class="btn">Retour</a></div>'
        return render("Erreur", content)
    
    session["authenticated"] = True
    session["licence"] = cle
    session["client"] = result["client"]
    session["type_abo"] = result["type"]
    session["expiration"] = result["expiration"]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    expiration = datetime.fromisoformat(session["expiration"]).strftime("%d/%m/%Y %H:%M")
    
    content = f"""
    <div class="nav">
        <a href="/dashboard">🏠 Générateur</a>
        <a href="/mes-configs">📋 Mes Configs</a>
        <a href="/logout">🚪 Déconnexion</a>
    </div>
    
    <div class="card">
        <div class="info">
            ✅ <b>{session['client']}</b> | Abonnement : <b>{session['type_abo']}</b> | Expire : <b>{expiration}</b>
        </div>
        
        <h2>⚙️ Générer une Configuration</h2>
        <form method="POST" action="/generate">
            <label>1️⃣ Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>
            
            <label>2️⃣ Type de configuration :</label>
            <select name="type_config" required>
                <option value="base">🌐 Base (Internet Simple)</option>
                <option value="hotspot">🎫 Hotspot (Tickets Wi-Fi)</option>
                <option value="pppoe">🔑 PPPoE (Abonnements)</option>
            </select>
            
            <label>3️⃣ Nom du client final :</label>
            <input type="text" name="client_final" placeholder="Ex: Boutique_Rakoto" required>
            
            <label>4️⃣ Nom du réseau Wi-Fi (SSID) :</label>
            <input type="text" name="ssid" placeholder="Ex: KETRIKA-NET" value="KETRIKA-NET">
            
            <label>5️⃣ Mot de passe Wi-Fi :</label>
            <input type="text" name="wifi_pass" placeholder="Min. 8 caractères" value="ketrika2025">
            
            <label>6️⃣ Options Anti-Bridage :</label>
            <div class="checkbox-group">
                <label><input type="checkbox" name="ttl" checked> ✅ Masquage TTL (obligatoire)</label>
                <label><input type="checkbox" name="dns" checked> ✅ DNS chiffré Cloudflare (DoH)</label>
                <label><input type="checkbox" name="ipv6" checked> ✅ Blocage IPv6 (anti-fuite)</label>
                <label><input type="checkbox" name="torrent" checked> ✅ Blocage Torrent/P2P</label>
                <label><input type="checkbox" name="warp" checked> 🛡️ Cloudflare WARP VPN (unique)</label>
                <label><input type="checkbox" name="queue"> 📊 Limitation débit par client (5 Mbps)</label>
                <label><input type="checkbox" name="security" checked> 🔒 Sécurité renforcée</label>
            </div>
            
            <button type="submit">🚀 Générer la Configuration Unique</button>
        </form>
    </div>
    """
    return render("Dashboard", content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    
    # Récupérer les options
    modele = request.form.get("modele")
    type_config = request.form.get("type_config")
    client_final = request.form.get("client_final").replace(" ", "_")
    ssid = request.form.get("ssid", "KETRIKA-NET")
    wifi_pass = request.form.get("wifi_pass", "ketrika2025")
    
    options = {
        "ttl": request.form.get("ttl") == "on",
        "dns": request.form.get("dns") == "on",
        "ipv6": request.form.get("ipv6") == "on",
        "torrent": request.form.get("torrent") == "on",
        "warp": request.form.get("warp") == "on",
        "queue": request.form.get("queue") == "on",
        "security": request.form.get("security") == "on",
        "ssid": ssid,
        "wifi_pass": wifi_pass
    }
    
    # Générer clés WARP uniques si demandé
    warp_data = {}
    if options["warp"]:
        warp_data = creer_config_warp_complete()
    
    # ID unique de configuration
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    
    # Sauvegarder en base
    sauvegarder_config(session["licence"], client_final, modele, type_config, options, warp_data, config_id)
    incrementer_utilisation(session["licence"])
    
    # Commande d'injection
    host = request.host_url.replace("http://", "https://")
    command = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    
    content = f"""
    <div class="nav">
        <a href="/dashboard">🏠 Générateur</a>
        <a href="/mes-configs">📋 Mes Configs</a>
        <a href="/logout">🚪 Déconnexion</a>
    </div>
    
    <div class="card">
        <div class="success">
            <h3>✅ Configuration Générée avec Succès !</h3>
            <p>Client : <b>{client_final}</b> | Modèle : <b>{modele}</b></p>
        </div>
        
        <h2>📋 Commande à copier dans le MikroTik :</h2>
        <div class="command-box">{command}</div>
        
        <div class="info" style="margin-top:20px;">
            <b>📖 Instructions :</b><br>
            1. Ouvrez Winbox et connectez-vous au MikroTik du client<br>
            2. Cliquez sur "New Terminal"<br>
            3. Collez la commande ci-dessus<br>
            4. Appuyez sur Entrée<br>
            5. Attendez 5 secondes ✅ Configuration terminée !
        </div>
        
        <a href="/dashboard" class="btn">➕ Générer une autre config</a>
    </div>
    """
    return render("Config générée", content)

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    """Retourne le script RouterOS complet"""
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("# Configuration introuvable", mimetype="text/plain")
    
    opt = cfg["options"]
    script = f"""# ================================================
# KETRIKA MIKROTIK - Configuration Professionnelle
# Client: {cfg['client']} | Modèle: {cfg['modele']}
# Généré: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ================================================
:log info "KETRIKA: Debut installation"
:put "=== KETRIKA MIKROTIK - Installation en cours ==="
"""
    
    if opt.get("ttl"):
        script += """
# --- ANTI-BRIDAGE : TTL Fix ---
/ip firewall mangle
remove [find comment~"KETRIKA-TTL"]
add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"
:put "[OK] TTL configure a 64"
"""
    
    if opt.get("dns"):
        script += """
# --- DNS Cloudflare DoH ---
/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes servers=1.1.1.1,1.0.0.1
/ip firewall nat
remove [find comment~"KETRIKA-DNS"]
add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS-UDP"
add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS-TCP"
:put "[OK] DNS chiffre active"
"""
    
    if opt.get("ipv6"):
        script += """
# --- Blocage IPv6 ---
/ipv6 settings set disable-ipv6=yes
:put "[OK] IPv6 desactive"
"""
    
    if opt.get("torrent"):
        script += """
# --- Blocage Torrent/P2P ---
/ip firewall filter
remove [find comment~"KETRIKA-P2P"]
add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P-TCP"
add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P-UDP"
add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P-Flood"
:put "[OK] Torrent bloque"
"""
    
    if opt.get("warp"):
        script += f"""
# --- Cloudflare WARP VPN (Cle UNIQUE) ---
/interface wireguard
remove [find name="warp-ketrika"]
add name=warp-ketrika listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers
add interface=warp-ketrika public-key="{cfg.get('warp_public', 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=')}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address
add address={cfg.get('warp_ip', '172.16.0.2')}/32 interface=warp-ketrika
/ip firewall nat
add chain=srcnat out-interface=warp-ketrika action=masquerade comment="KETRIKA-WARP-NAT"
/ip route
add dst-address=0.0.0.0/0 gateway=warp-ketrika distance=1 comment="KETRIKA-WARP-Route"
:put "[OK] Cloudflare WARP active"
"""
    
    if opt.get("queue"):
        script += """
# --- Limitation de bande passante ---
/queue type
add name=pcq-download kind=pcq pcq-rate=5M pcq-classifier=dst-address
add name=pcq-upload kind=pcq pcq-rate=2M pcq-classifier=src-address
/queue simple
add name=KETRIKA-Limit target=192.168.88.0/24 queue=pcq-upload/pcq-download comment="KETRIKA-Queue"
:put "[OK] Limitation debit active (5M/2M par client)"
"""
    
    if opt.get("security"):
        script += """
# --- Sécurité renforcée ---
/ip firewall filter
add chain=input action=drop connection-state=invalid comment="KETRIKA-SEC-Invalid"
add chain=input action=accept connection-state=established,related comment="KETRIKA-SEC-Established"
add chain=input action=drop in-interface-list=WAN comment="KETRIKA-SEC-WAN-Drop"
/ip service disable telnet,ftp,www,api
:put "[OK] Securite renforcee"
"""
    
    if cfg["type"] == "hotspot":
        script += f"""
# --- Configuration Hotspot ---
/ip pool add name=ketrika-hs-pool ranges=10.5.50.10-10.5.50.254
/ip dhcp-server add name=ketrika-hs-dhcp interface=bridge address-pool=ketrika-hs-pool disabled=no
/ip hotspot profile add name=ketrika-hs hotspot-address=10.5.50.1 dns-name=ketrika.wifi
/ip hotspot add name=hs-ketrika interface=bridge address-pool=ketrika-hs-pool profile=ketrika-hs disabled=no
:put "[OK] Hotspot cree - Utilisez Mikhmon pour les tickets"
"""
    
    if cfg["type"] == "pppoe":
        script += """
# --- Serveur PPPoE ---
/ip pool add name=ketrika-ppp-pool ranges=10.10.10.2-10.10.10.254
/ppp profile add name=ketrika-ppp local-address=10.10.10.1 remote-address=ketrika-ppp-pool dns-server=1.1.1.1
/interface pppoe-server server add service-name=KETRIKA-NET interface=bridge default-profile=ketrika-ppp disabled=no
:put "[OK] PPPoE cree - Ajoutez les users dans PPP > Secrets"
"""
    
    # Wi-Fi si SSID fourni
    if opt.get("ssid"):
        script += f"""
# --- Configuration Wi-Fi ---
/interface wifi security
add name=ketrika-sec authentication-types=wpa2-psk,wpa3-psk passphrase="{opt['wifi_pass']}"
/interface wifi
set [find] ssid="{opt['ssid']}" security=ketrika-sec disabled=no
:put "[OK] Wi-Fi configure: {opt['ssid']}"
"""
    
    script += """
:put "==============================================="
:put "  KETRIKA MIKROTIK - Installation TERMINEE !"
:put "  Contact: 038 28 171 00"
:put "==============================================="
:log info "KETRIKA: Installation terminee avec succes"
"""
    return Response(script, mimetype="text/plain")

# ==========================================
# ADMIN
# ==========================================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        content = '<div class="card"><div class="error">❌ Identifiants incorrects</div></div>'
        return render("Admin", content)
    
    content = """
    <div class="card">
        <h2>🔐 Administration</h2>
        <form method="POST">
            <label>Utilisateur :</label>
            <input type="text" name="username" required>
            <label>Mot de passe :</label>
            <input type="password" name="password" required>
            <button type="submit">Connexion Admin</button>
        </form>
    </div>
    """
    return render("Admin", content)

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    
    stats = get_stats()
    
    dernieres_html = ""
    for lic in stats["dernieres_licences"]:
        dernieres_html += f"<tr><td>{lic[1]}</td><td>{lic[2]}</td><td>{lic[3]}</td><td>{lic[4]}</td><td>{lic[9]:,} Ar</td></tr>"
    
    content = f"""
    <div class="nav">
        <a href="/admin/dashboard">📊 Dashboard</a>
        <a href="/admin/creer-licence">➕ Créer Licence</a>
        <a href="/admin/logout">🚪 Déconnexion</a>
    </div>
    
    <div class="card">
        <h2>📊 Statistiques</h2>
        <div class="stat-grid">
            <div class="stat-card"><b>{stats['total_clients']}</b>Clients actifs</div>
            <div class="stat-card"><b>{stats['revenu_total']:,.0f} Ar</b>Revenu total</div>
            <div class="stat-card"><b>{stats['nb_configs']}</b>Configs générées</div>
        </div>
        
        <h3>📋 Dernières licences</h3>
        <table>
            <tr><th>Clé</th><th>Client</th><th>Téléphone</th><th>Type</th><th>Prix</th></tr>
            {dernieres_html}
        </table>
    </div>
    """
    return render("Admin Dashboard", content)

@app.route("/admin/creer-licence", methods=["GET", "POST"])
def admin_creer_licence():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    
    if request.method == "POST":
        client = request.form.get("client")
        telephone = request.form.get("telephone")
        type_abo = request.form.get("type_abo")
        prix = TARIFS[type_abo]["prix"]
        
        cle = creer_licence(client, telephone, type_abo, prix)
        
        content = f"""
        <div class="card">
            <div class="success">
                <h3>✅ Licence créée avec succès !</h3>
                <p>Envoyez cette clé au client :</p>
            </div>
            <div class="command-box">{cle}</div>
            <p style="margin-top:15px;">Client: <b>{client}</b> | Tél: <b>{telephone}</b> | Type: <b>{type_abo}</b> | Prix: <b>{prix:,} Ar</b></p>
            <a href="/admin/creer-licence" class="btn">➕ Créer une autre</a>
            <a href="/admin/dashboard" class="btn">📊 Dashboard</a>
        </div>
        """
        return render("Licence créée", content)
    
    tarifs_opt = "".join([f'<option value="{k}">{t["nom"]} - {t["prix"]:,} Ar</option>' for k, t in TARIFS.items()])
    
    content = f"""
    <div class="nav">
        <a href="/admin/dashboard">📊 Dashboard</a>
        <a href="/admin/creer-licence">➕ Créer Licence</a>
        <a href="/admin/logout">🚪 Déconnexion</a>
    </div>
    
    <div class="card">
        <h2>➕ Créer une nouvelle licence</h2>
        <form method="POST">
            <label>Nom du client :</label>
            <input type="text" name="client" required>
            <label>Téléphone :</label>
            <input type="text" name="telephone" placeholder="034 XX XXX XX" required>
            <label>Type d'abonnement :</label>
            <select name="type_abo" required>{tarifs_opt}</select>
            <button type="submit">Générer la clé</button>
        </form>
    </div>
    """
    return render("Créer licence", content)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)