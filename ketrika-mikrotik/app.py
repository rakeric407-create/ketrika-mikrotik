from flask import Flask, request, Response, render_template_string, session, redirect, url_for
from database import *
from warp_api import creer_config_warp_complete
import sqlite3
import secrets
import string
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

init_db()

# Table supplémentaire pour les commandes en attente
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
    "base": {"nom": "🛡️ Pack Essentiel (Anti-Bridage)", "prix": 10000, "desc": "TTL 64 + DNS DoH + Blocage IPv6 & Torrents"},
    "warp": {"nom": "🚀 Pack Blindé (Tunnel WARP VPN)", "prix": 20000, "desc": "Pack Essentiel + Chiffrement Total WireGuard"},
    "hotspot": {"nom": "🎫 Pack Wi-Fi Zone (Hotspot + VPN)", "prix": 30000, "desc": "Pack Blindé + Système Tickets Hotspot"},
    "pro": {"nom": "🏢 Pack Pro WISP (PPPoE + Hotspot + VPN)", "prix": 50000, "desc": "Solution intégrale pour revendeurs"}
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
            --accent-green: #00ff88;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-glow: rgba(0, 242, 254, 0.2);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 15px; }
        .container { max-width: 800px; margin: auto; }
        .header { text-align: center; padding: 20px 0; }
        .header h1 { font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 900; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .card { background: var(--card-bg); border: 1px solid var(--border-glow); border-radius: 14px; padding: 22px; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.4); }
        .card-title { font-family: 'Orbitron', sans-serif; font-size: 16px; color: var(--accent-cyan); margin-bottom: 12px; }
        label { display: block; font-size: 12px; font-weight: 600; color: var(--text-muted); margin-top: 12px; text-transform: uppercase; }
        input, select { width: 100%; padding: 12px; margin-top: 6px; background: #1a2234; border: 1px solid #2d3748; border-radius: 8px; color: #fff; font-size: 15px; }
        input:focus, select:focus { outline: none; border-color: var(--accent-cyan); }
        .btn-primary { width: 100%; padding: 14px; margin-top: 18px; background: linear-gradient(135deg, #00f2fe, #4facfe); color: #000; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Orbitron', sans-serif; }
        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 10px; }
        .plan-option { background: #161f30; border: 2px solid #2d3748; padding: 12px; border-radius: 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .plan-option input { width: 20px; height: 20px; accent-color: var(--accent-cyan); margin: 0; }
        .terminal-box { background: #05080f; border: 1px solid var(--accent-green); color: var(--accent-green); padding: 15px; border-radius: 8px; font-family: monospace; font-size: 13px; word-break: break-all; margin-top: 10px; }
        .badge { background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan); padding: 3px 8px; border-radius: 12px; font-size: 11px; border: 1px solid var(--accent-cyan); }
        .alert { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; }
        .alert-success { background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; color: #6ee7b7; }
        .alert-error { background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #fca5a5; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        table th, table td { padding: 10px; border-bottom: 1px solid #2d3748; text-align: left; }
        table th { color: var(--accent-cyan); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p style="color:var(--text-muted); font-size:13px; margin-top:4px;">Anti-Bridage Starlink & Configuration Réseau</p>
        </div>
        {{ content|safe }}
        <div style="text-align: center; color: var(--text-muted); font-size: 11px; margin-top: 25px;">
            KETRIKA MIKROTIK © 2025 • Support : 038 28 171 00
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
    <!-- ONGLET 1 : COMMANDER UN PLAN -->
    <div class="card">
        <div class="card-title">🛒 1. CHOISIR VOTRE PACK DE CONFIGURATION</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">
                {plans_html}
            </div>

            <div style="background:#161f30; padding:15px; border-radius:10px; margin-top:15px; border-left:4px solid #ffaa00;">
                <b style="color:#ffaa00; font-size:13px;">📱 PAIEMENT MOBILE MONEY</b>
                <div style="font-size:13px; color:#fff; margin-top:4px;">Envoyez le montant correspondant au :</div>
                <div style="font-size:22px; font-weight:bold; color:#ffaa00; font-family:'Orbitron'; margin:5px 0;">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted);">Mvola / Orange Money / Airtel Money</small>
            </div>

            <label>Votre Nom complet :</label>
            <input type="text" name="nom" placeholder="Ex: Jean Rakoto" required>

            <label>Votre Numéro de Téléphone (réception de clé) :</label>
            <input type="text" name="tel" placeholder="Ex: 034 XX XXX XX" required>

            <label>Référence du SMS de Paiement :</label>
            <input type="text" name="ref_paiement" placeholder="Ex: Réf Mvola / Orange / Airtel" required>

            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <!-- ONGLET 2 : ENTRER UNE CLÉ REÇUE -->
    <div class="card">
        <div class="card-title">🔐 2. DÉJÀ UNE CLÉ ? ACTIVEZ VOTRE ROUTEUR</div>
        <form method="POST" action="/login">
            <label>Votre Clé de Licence :</label>
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase;">
            <button type="submit" class="btn-primary" style="background:linear-gradient(135deg, #10b981, #059669); color:#fff;">OUVRIR LE GÉNÉRATEUR</button>
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
        <div class="alert alert-success">
            <b>✅ Commande enregistrée avec succès !</b>
        </div>
        <p style="font-size:14px; line-height:1.6;">
            Merci <b>{nom}</b> ! Votre paiement pour le pack <b>{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar) est en cours de validation.<br><br>
            Votre clé vous sera expédiée par SMS au <b>{tel}</b> d'ici quelques minutes.
        </p>
        <a href="/" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:20px;">RETOUR À L'ACCUEIL</a>
    </div>
    """
    return render(content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé invalide ou expirée !</div><a href="/" class="btn-primary" style="text-decoration:none; display:block; text-align:center;">Retour</a></div>')
    
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
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span class="badge">Session : {session['client']}</span>
        <a href="/logout" style="color:#ef4444; font-size:12px; text-decoration:none;">Déconnexion</a>
    </div>

    <div class="card">
        <div class="card-title">⚙️ GÉNÉRATEUR D'INJECTION MIKROTIK</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Type de réseau :</label>
            <select name="type_config" required>
                <option value="base">🌐 Simple Débridage LAN</option>
                <option value="hotspot">🎫 Hotspot Tickets Wi-Fi</option>
                <option value="pppoe">🔑 Fournisseur PPPoE</option>
            </select>

            <label>3. Nom du client final :</label>
            <input type="text" name="client_final" placeholder="Ex: Boutique_Rakoto" required>

            <label>4. Options Incluses :</label>
            <div style="background:#161f30; padding:12px; border-radius:8px; margin-top:8px; font-size:13px;">
                <div>✅ Masquage TTL = 64 (Starlink)</div>
                <div>✅ DNS Sécurisé DoH Cloudflare</div>
                <div>✅ Blocage IPv6 & Anti-Fuite</div>
                <div>✅ Blocage Torrent & Anti-Flood</div>
                <div>✅ Tunnel VPN WARP WireGuard Unique</div>
            </div>

            <button type="submit" class="btn-primary">GÉNÉRER LA COMMANDE</button>
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
    
    options = {"ttl": True, "dns": True, "ipv6": True, "torrent": True, "warp": True}
    warp_data = creer_config_warp_complete()
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    sauvegarder_config(session["licence"], client_final, modele, type_config, options, warp_data, config_id)
    incrementer_utilisation(session["licence"])
    
    host = request.host_url.replace("http://", "https://")
    command = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    
    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Injection prête pour : {client_final}</b></div>
        <div class="card-title">COMMANDE TERMINAL WINBOX :</div>
        <div class="terminal-box">{command}</div>
        <a href="/dashboard" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:15px;">NOUVELLE CONFIGURATION</a>
    </div>
    """
    return render(content)

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("# Invalide", mimetype="text/plain")
    
    opt = cfg["options"]
    script = f"# KETRIKA MIKROTIK - {cfg['client']}\n"
    script += '/ip firewall mangle remove [find comment="KETRIKA-TTL"]\n/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"\n'
    script += '/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes\n/ip firewall nat remove [find comment="KETRIKA-DNS"]\n/ip firewall nat add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n'
    script += '/ipv6 settings set disable-ipv6=yes\n'
    script += '/ip firewall filter remove [find comment="KETRIKA-P2P"]\n/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P"\n'
    if cfg.get("warp_private"):
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
            <td>{cmd[3]}<br><b>{cmd[4]:,} Ar</b></td>
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
        <a href="/admin/creer" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:20px;">➕ CRÉER UNE CLÉ MANUELLE</a>
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
        <div class="alert alert-success">✅ Commande validée pour {cmd[1]} !</div>
        <div class="card-title">CLÉ GÉNÉRÉE À ENVOYER PAR SMS AU {cmd[2]} :</div>
        <div class="terminal-box">{cle}</div>
        <a href="/admin/dashboard" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:15px;">RETOUR AUX COMMANDES</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="text-decoration:none; display:block; text-align:center; margin-top:15px;">Dashboard</a></div>')
    return render("""<div class="card"><div class="card-title">Créer une Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="base">Pack Essentiel (10k)</option><option value="warp">Pack Blindé (20k)</option><option value="hotspot">Pack Hotspot (30k)</option><option value="pro">Pack Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
