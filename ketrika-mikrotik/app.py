from flask import Flask, request, Response, render_template_string, session, redirect, url_for
from database import *
from warp_api import creer_config_warp_complete
import secrets
import string
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

init_db()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "base": {"nom": "🛡️ Pack Essentiel (Anti-Bridage Standard)", "prix": 10000, "desc": "TTL 64 + DNS DoH + Blocage IPv6/Torrent"},
    "warp": {"nom": "🚀 Pack Blindé (Tunnel WARP VPN Unique)", "prix": 20000, "desc": "Pack Essentiel + Chiffrement WireGuard 100%"},
    "hotspot": {"nom": "🎫 Pack Wi-Fi Zone (Hotspot + VPN)", "prix": 30000, "desc": "Pack Blindé + Système Tickets Hotspot"},
    "pro": {"nom": "🏢 Pack Pro Business (PPPoE + Hotspot + VPN)", "prix": 50000, "desc": "La totale pour revendeurs et petits WISP"}
}

MODELES_MIKROTIK = [
    "hAP ax2", "hAP ax3", "hAP ac2", "hAP ac3", "hAP lite",
    "RB750Gr3 (hEX)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011",
    "CCR1009", "CCR2004", "CCR2116",
    "mANTBox ax 15s", "mANTBox 19s", "LHG 5", "SXTsq",
    "Chateau LTE/5G", "Autre RouterOS v7"
]

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK - Starlink Optimizer</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #090d16;
            --card-bg: #111827;
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --accent-green: #00ff88;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-glow: rgba(0, 242, 254, 0.2);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 20px; background-image: radial-gradient(circle at top right, rgba(0, 242, 254, 0.05), transparent 400px); }
        .container { max-width: 850px; margin: auto; }
        
        /* HEADER */
        .header { text-align: center; padding: 25px 0; }
        .header h1 { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 900; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px; }
        .header p { color: var(--text-muted); font-size: 14px; margin-top: 5px; }

        /* CARDS */
        .card { background: var(--card-bg); border: 1px solid var(--border-glow); border-radius: 16px; padding: 25px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 18px; color: var(--accent-cyan); margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }

        /* FORMS */
        label { display: block; font-size: 13px; font-weight: 600; color: var(--text-muted); margin-top: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        input, select { width: 100%; padding: 14px; margin-top: 8px; background: #1a2234; border: 1px solid #2d3748; border-radius: 10px; color: #fff; font-size: 15px; transition: 0.3s; }
        input:focus, select:focus { outline: none; border-color: var(--accent-cyan); box-shadow: 0 0 12px rgba(0, 242, 254, 0.3); }

        /* BUTTONS */
        .btn-primary { width: 100%; padding: 15px; margin-top: 20px; background: linear-gradient(135deg, #00f2fe, #4facfe); color: #000; border: none; border-radius: 10px; font-size: 16px; font-weight: 700; cursor: pointer; transition: 0.3s; font-family: 'Orbitron', sans-serif; letter-spacing: 1px; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 242, 254, 0.4); }

        /* PRICING GRID */
        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-top: 15px; }
        .pricing-card { background: #161f30; border: 1px solid #2d3748; border-radius: 12px; padding: 18px; text-align: center; transition: 0.3s; position: relative; }
        .pricing-card:hover { border-color: var(--accent-cyan); transform: translateY(-3px); }
        .pricing-card b { font-size: 15px; color: #fff; display: block; }
        .pricing-card .price { font-family: 'Orbitron', sans-serif; font-size: 22px; color: var(--accent-green); margin: 10px 0; }
        .pricing-card small { color: var(--text-muted); font-size: 12px; display: block; line-height: 1.4; }

        /* PAYMENT BOX */
        .payment-banner { background: linear-gradient(135deg, rgba(255, 170, 0, 0.1), rgba(255, 115, 0, 0.05)); border: 1px solid #ffaa00; border-radius: 12px; padding: 20px; margin-top: 20px; text-align: center; }
        .payment-phone { font-family: 'Orbitron', sans-serif; font-size: 28px; color: #ffaa00; margin: 10px 0; font-weight: bold; letter-spacing: 2px; }

        /* TERMINAL BOX */
        .terminal-box { background: #05080f; border: 1px solid var(--accent-green); color: var(--accent-green); padding: 20px; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 13px; word-break: break-all; margin-top: 15px; position: relative; box-shadow: 0 0 15px rgba(0, 255, 136, 0.15); }

        /* CHECKBOXES */
        .options-list { background: #161f30; padding: 15px; border-radius: 10px; margin-top: 10px; }
        .option-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #232d42; }
        .option-item:last-child { border-bottom: none; }
        .option-item input { width: 18px; height: 18px; accent-color: var(--accent-cyan); cursor: pointer; }

        .badge { background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan); padding: 4px 10px; border-radius: 20px; font-size: 12px; border: 1px solid var(--accent-cyan); }
        .alert { padding: 15px; border-radius: 10px; margin-bottom: 15px; font-size: 14px; }
        .alert-error { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #fca5a5; }
        .alert-success { background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #6ee7b7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p>Système Professionnel d'Optimisation & Anti-Bridage Starlink</p>
        </div>
        {{ content|safe }}
        <div style="text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 30px;">
            KETRIKA MIKROTIK PRO © 2025 • Ingénierie Réseau Avancée
        </div>
    </div>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content)

@app.route("/")
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    cards_html = ""
    for k, v in TARIFS_MODULES.items():
        cards_html += f"""
        <div class="pricing-card">
            <b>{v['nom']}</b>
            <div class="price">{v['prix']:,} Ar</div>
            <small>{v['desc']}</small>
        </div>"""
    
    content = f"""
    <div class="card">
        <div class="card-title">🔐 ESPACE D'ACTIVATION</div>
        <form method="POST" action="/login">
            <label>Entrez votre Clé de Licence reçue par SMS :</label>
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing: 2px;">
            <button type="submit" class="btn-primary">ACCÉDER AU SYSTÈME</button>
        </form>
    </div>

    <div class="card">
        <div class="card-title">💰 TARIFS SELON LA CONFIGURATION</div>
        <div class="pricing-grid">{cards_html}</div>
        
        <div class="payment-banner">
            <div style="font-size: 14px; color: #ffaa00; font-weight: bold;">POUR OBTENIR VOTRE CLÉ IMMÉDIATEMENT :</div>
            <p style="margin-top: 5px; font-size: 13px; color: var(--text-muted);">Envoyez le montant correspondant par Mobile Money au :</p>
            <div class="payment-phone">{NUMERO_PAIEMENT}</div>
            <p style="font-size: 13px; color: #fff;">✅ Mvola | ✅ Orange Money | ✅ Airtel Money</p>
            <small style="display:block; margin-top: 8px; color: var(--text-muted);">Envoyez votre SMS de transfert, votre clé est expédiée en 2 minutes.</small>
        </div>
    </div>
    """
    return render(content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé de licence introuvable ou expirée.</div><a href="/" class="btn-primary" style="text-decoration:none; display:block; text-align:center;">Retour</a></div>')
    
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
    
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])
    
    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
        <span class="badge">Session : {session['client']}</span>
        <a href="/logout" style="color:#ef4444; font-size:13px; text-decoration:none;">Déconnexion</a>
    </div>

    <div class="card">
        <div class="card-title">⚙️ GÉNÉRATEUR DE CONFIGURATION MIKROTIK</div>
        <form method="POST" action="/generate">
            <label>1. Modèle exact de votre équipement :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Architecture réseau désirée :</label>
            <select name="type_config" required>
                <option value="base">🌐 Simple Débridage & Partage LAN</option>
                <option value="hotspot">🎫 Hotspot Wi-Fi Zone (Tickets)</option>
                <option value="pppoe">🔑 Fournisseur PPPoE (Abonnements fixes)</option>
            </select>

            <label>3. Identifiant du client final :</label>
            <input type="text" name="client_final" placeholder="Ex: Client_Starlink_01" required>

            <label>4. Modules de Sécurité & Anti-Bridage :</label>
            <div class="options-list">
                <div class="option-item">
                    <input type="checkbox" name="ttl" id="ttl" checked>
                    <label for="ttl" style="margin:0; text-transform:none; color:#fff;">🛡️ <b>Mangle TTL = 64</b> (Masquage multi-appareils Starlink)</label>
                </div>
                <div class="option-item">
                    <input type="checkbox" name="dns" id="dns" checked>
                    <label for="dns" style="margin:0; text-transform:none; color:#fff;">🔒 <b>DNS Cloudflare DoH</b> (Requêtes web 100% chiffrées)</label>
                </div>
                <div class="option-item">
                    <input type="checkbox" name="ipv6" id="ipv6" checked>
                    <label for="ipv6" style="margin:0; text-transform:none; color:#fff;">🚫 <b>Bloqueur IPv6</b> (Supprime les fuites de paquets Starlink)</label>
                </div>
                <div class="option-item">
                    <input type="checkbox" name="torrent" id="torrent" checked>
                    <label for="torrent" style="margin:0; text-transform:none; color:#fff;">⛔ <b>Filtre Anti-P2P / Torrent</b> (Évite les alertes de bande passante)</label>
                </div>
                <div class="option-item">
                    <input type="checkbox" name="warp" id="warp" checked>
                    <label for="warp" style="margin:0; text-transform:none; color:#00ff88;">⚡ <b>Cloudflare WARP Tunnel</b> (Clé WireGuard dédiée invisible)</label>
                </div>
            </div>

            <button type="submit" class="btn-primary">GÉNÉRER L'INJECTION MIKROTIK</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    
    modele = request.form.get("modele")
    type_config = request.form.get("type_config")
    client_final = request.form.get("client_final").replace(" ", "_")
    
    options = {
        "ttl": request.form.get("ttl") == "on",
        "dns": request.form.get("dns") == "on",
        "ipv6": request.form.get("ipv6") == "on",
        "torrent": request.form.get("torrent") == "on",
        "warp": request.form.get("warp") == "on"
    }
    
    warp_data = creer_config_warp_complete() if options["warp"] else {}
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    sauvegarder_config(session["licence"], client_final, modele, type_config, options, warp_data, config_id)
    incrementer_utilisation(session["licence"])
    
    host = request.host_url.replace("http://", "https://")
    command = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    
    content = f"""
    <div class="card">
        <div class="alert alert-success">
            <b>✅ Script d'Injection Prêt pour : {client_final} ({modele})</b>
        </div>

        <div class="card-title">📋 COMMANDE À INJECTER DANS LE MIKROTIK</div>
        <p style="font-size:13px; color:var(--text-muted);">Copiez cette ligne et collez-la directement dans <b>Winbox ➡️ New Terminal</b> :</p>
        
        <div class="terminal-box">{command}</div>

        <div style="margin-top:20px; font-size:13px; color:var(--text-muted); line-height: 1.6;">
            <b>Instructions rapides :</b><br>
            1. Connectez-vous au routeur client via Winbox.<br>
            2. Ouvrez le Terminal et collez la commande ci-dessus.<br>
            3. Appuyez sur Entrée : l'optimisation s'applique en 3 secondes chrono.
        </div>

        <a href="/dashboard" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:20px;">CRÉER UNE AUTRE CONFIGURATION</a>
    </div>
    """
    return render(content)

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("# Invalide", mimetype="text/plain")
    
    opt = cfg["options"]
    script = f"# KETRIKA MIKROTIK PRO - {cfg['client']} ({cfg['modele']})\n"
    
    if opt.get("ttl"):
        script += '/ip firewall mangle remove [find comment="KETRIKA-TTL"]\n/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"\n'
    if opt.get("dns"):
        script += '/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes\n/ip firewall nat remove [find comment="KETRIKA-DNS"]\n/ip firewall nat add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n'
    if opt.get("ipv6"):
        script += '/ipv6 settings set disable-ipv6=yes\n'
    if opt.get("torrent"):
        script += '/ip firewall filter remove [find comment="KETRIKA-P2P"]\n/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P"\n'
    if opt.get("warp") and cfg.get("warp_private"):
        script += f"""/interface wireguard remove [find name="warp-ketrika"]
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
    return Response(script, mimetype="text/plain")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ACCÈS ADMINISTRATEUR</div><form method="POST"><label>Utilisateur :</label><input type="text" name="username" required><label>Mot de passe :</label><input type="password" name="password" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    stats = get_stats()
    return render(f"""
    <div class="card">
        <div class="card-title">📊 TABLEAU DE BORD BUSINESS</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin:20px 0;">
            <div style="background:#161f30; padding:15px; border-radius:10px; text-align:center;">
                <b style="font-size:26px; color:var(--accent-cyan);">{stats["total_clients"]}</b>
                <div style="font-size:12px; color:var(--text-muted); margin-top:5px;">Clients Total</div>
            </div>
            <div style="background:#161f30; padding:15px; border-radius:10px; text-align:center;">
                <b style="font-size:26px; color:var(--accent-green);">{stats["nb_configs"]}</b>
                <div style="font-size:12px; color:var(--text-muted); margin-top:5px;">Configs Injectées</div>
            </div>
        </div>
        <a href="/admin/creer" class="btn-primary" style="text-decoration:none; display:block; text-align:center;">➕ CRÉER UNE NOUVELLE CLÉ CLIENT</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        type_formule = request.form.get("type")
        prix = TARIFS_MODULES.get(type_formule, {}).get("prix", 10000)
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), type_formule, prix)
        return render(f"""
        <div class="card">
            <div class="alert alert-success">✅ Nouvelle clé générée !</div>
            <div class="terminal-box">{cle}</div>
            <p style="margin-top:15px; font-size:14px;">Envoyez cette clé par SMS au client : <b>{request.form.get('client')}</b> ({request.form.get('tel')})</p>
            <a href="/admin/dashboard" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:20px;">RETOUR DASHBOARD</a>
        </div>
        """)
    return render("""
    <div class="card">
        <div class="card-title">➕ ÉMISSION D'UNE CLÉ CLIENT</div>
        <form method="POST">
            <label>Nom du client :</label>
            <input type="text" name="client" placeholder="Ex: Jean Rakoto" required>
            <label>Numéro de téléphone :</label>
            <input type="text" name="tel" placeholder="034 XX XXX XX" required>
            <label>Formule choisie :</label>
            <select name="type">
                <option value="base">🛡️ Pack Essentiel (10 000 Ar)</option>
                <option value="warp">🚀 Pack Blindé VPN (20 000 Ar)</option>
                <option value="hotspot">🎫 Pack Hotspot Wi-Fi (30 000 Ar)</option>
                <option value="pro">🏢 Pack Pro WISP (50 000 Ar)</option>
            </select>
            <button type="submit" class="btn-primary">GÉNÉRER LA CLÉ DE LICENCE</button>
        </form>
    </div>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
