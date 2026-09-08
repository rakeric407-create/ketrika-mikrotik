# app.py - KETRIKA MIKROTIK - Application Complete
import os
import io
from datetime import datetime
from flask import (Flask, render_template_string, request, redirect,
                   url_for, flash, send_file, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db, Admin, Order, MIKROTIK_MODELS, PLANS
from warp_api import generate_full_script

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ketrika-secret-2024')

dbu = os.environ.get('DATABASE_URL', 'sqlite:///ketrika.db')
if dbu.startswith("postgres://"):
    dbu = dbu.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = dbu
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_SENDER', app.config['MAIL_USERNAME'])

UPLOAD = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD, exist_ok=True)

db.init_app(app)
mail = Mail(app)
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'admin_login'

@lm.user_loader
def load_user(uid):
    return Admin.query.get(int(uid))

with app.app_context():
    try:
        db.create_all()
        au = os.environ.get('ADMIN_USER', 'admin')
        ap = os.environ.get('ADMIN_PASS', 'KetrikaAdmin2024!')
        if not Admin.query.filter_by(username=au).first():
            db.session.add(Admin(username=au, password_hash=generate_password_hash(ap)))
            db.session.commit()
    except Exception as e:
        print(f"DB Error: {e}")

# ==================== CSS ====================
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#f4f7f6;color:#2c3e50;min-height:100vh;line-height:1.6}
nav{background:#fff;padding:14px 25px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e1e8ed;box-shadow:0 2px 8px rgba(0,0,0,.05);position:sticky;top:0;z-index:100}
nav .logo{color:#00875a;font-size:21px;font-weight:700;text-decoration:none}
nav .logo span{color:#0066cc}
nav .links a{color:#5a6c7d;text-decoration:none;margin-left:16px;font-size:13px;font-weight:500}
nav .links a:hover{color:#00875a}
.container{max-width:1100px;margin:auto;padding:25px 15px}
.flash{padding:12px 18px;border-radius:8px;margin-bottom:12px;font-size:14px}
.flash.success{background:#e6f9ee;border-left:4px solid #00875a;color:#006644}
.flash.error{background:#fde8e8;border-left:4px solid #cc3333;color:#991111}
.flash.warning{background:#fff8e1;border-left:4px solid #f0a020;color:#8a5a00}
.btn{padding:11px 24px;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;transition:all .2s}
.btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.12)}
.btn-g{background:#00875a;color:#fff}.btn-g:hover{background:#006644}
.btn-b{background:#0066cc;color:#fff}.btn-b:hover{background:#004c99}
.btn-o{background:#e65c00;color:#fff}
.btn-r{background:#cc3333;color:#fff}
.card{background:#fff;border-radius:12px;padding:22px;border:1px solid #e1e8ed;box-shadow:0 2px 8px rgba(0,0,0,.03)}
label{display:block;margin:8px 0 4px;color:#4a5568;font-size:13px;font-weight:600}
input,select,textarea{width:100%;padding:10px;border:1px solid #d1d9e0;border-radius:8px;background:#f8fafc;color:#2c3e50;font-size:14px;margin-bottom:4px}
input:focus,select:focus{border-color:#00875a;background:#fff;outline:none;box-shadow:0 0 0 3px rgba(0,135,90,.1)}
.row{display:flex;gap:14px;flex-wrap:wrap}
.row>div{flex:1;min-width:210px}
.check{display:flex;align-items:center;gap:8px;margin:8px 0;padding:8px;background:#f8fafc;border-radius:6px}
.check input{width:auto}
footer{text-align:center;padding:25px;color:#718096;border-top:1px solid #e1e8ed;margin-top:40px;background:#fff;font-size:12px}
table{width:100%;border-collapse:collapse}
th{padding:10px;text-align:left;background:#f0f4f8;font-size:12px;color:#4a5568}
td{padding:10px;border-bottom:1px solid #edf2f7;font-size:13px}
"""

def wrap(title, body, js=""):
    fl = """{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for c,m in messages %}<div class="flash {{c}}">{{m}}</div>{% endfor %}{% endif %}{% endwith %}"""
    return f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} - KETRIKA</title><style>{CSS}</style></head><body>
<nav><a href="/" class="logo">🛰️ KETRIKA <span>MIKROTIK</span></a><div class="links">
<a href="/">Accueil</a><a href="/pourquoi-nous" style="color:#00875a;font-weight:700">Pourquoi Nous</a><a href="/track">🔍 Suivi</a><a href="/faq">FAQ</a><a href="/admin">Admin</a>
</div></nav><div class="container">{fl}{body}</div><footer>© 2024 KETRIKA MIKROTIK - WiFi Zone Solutions 🛰️</footer>{js}</body></html>"""


# ==================== ROUTES ====================

@app.route('/')
def index():
    ph = ""
    for k, p in PLANS.items():
        bd = f"border:2px solid {p['color']};" if p.get('popular') else ""
        bg = f'<div style="background:{p["color"]};color:#fff;padding:3px 10px;border-radius:10px;font-size:10px;font-weight:700;display:inline-block;margin-bottom:8px">⭐ POPULAIRE</div><br>' if p.get('popular') else ''
        ft = "".join(f'<li style="padding:5px 0;font-size:12px;border-bottom:1px solid #edf2f7">✅ {f}</li>' for f in p['features'])
        ph += f'<div class="card" style="text-align:center;flex:1;min-width:270px;{bd}">{bg}<h3 style="color:{p["color"]};font-size:18px">{p["name"]}</h3><p style="color:#718096;font-size:12px;margin:4px 0 12px">{p["subtitle"]}</p><div style="font-size:30px;font-weight:700;color:{p["color"]};margin-bottom:12px">{p["price"]:,} <small style="font-size:13px;color:#718096">{p["currency"]}</small></div><ul style="list-style:none;text-align:left;margin-bottom:15px">{ft}</ul><a href="/configure/{k}" class="btn" style="width:100%;background:{p["color"]};color:#fff">Configurer →</a></div>'
    mh = "".join(f'<span style="background:#fff;padding:5px 10px;border-radius:12px;font-size:11px;color:#0066cc;border:1px solid #d1d9e0">{m}</span>' for m in MIKROTIK_MODELS)
    body = f"""
    <div style="text-align:center;padding:45px 20px;background:#fff;border-radius:14px;border:1px solid #e1e8ed;margin-bottom:25px">
        <h1 style="font-size:38px;color:#00875a">🛰️ KETRIKA MIKROTIK</h1>
        <h2 style="color:#0066cc;font-weight:400;font-size:18px">Configuration Automatique WiFi Zone</h2>
        <p style="color:#5a6c7d;max-width:650px;margin:12px auto">Scripts MikroTik RouterOS v7 avec optimisation réseau avancée. <strong>Sans redémarrage !</strong></p>
        <div style="margin-top:15px"><a href="/track" class="btn btn-b" style="font-size:13px">🔍 Déjà commandé ? Entrer votre code</a></div>
    </div>
    <h2 style="text-align:center;color:#2d3748;margin:25px 0 15px">📦 Nos Plans</h2>
    <div class="row">{ph}</div>
    <h2 style="text-align:center;color:#2d3748;margin:35px 0 12px;font-size:18px">🖥️ Modèles Compatibles (RouterOS v7)</h2>
    <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center">{mh}</div>"""
    return render_template_string(wrap("Accueil", body))


@app.route('/pourquoi-nous')
def pourquoi_nous():
    body = """
    <div style="text-align:center;padding:50px 25px;background:linear-gradient(135deg,#00875a,#0066cc);border-radius:14px;color:#fff;margin-bottom:30px">
        <h1 style="color:#fff;font-size:34px">Pourquoi Choisir KETRIKA ?</h1>
        <p style="font-size:16px;opacity:.95;max-width:650px;margin:12px auto 0">La référence Malgache en configuration MikroTik pour opérateurs WiFi Zone</p>
    </div>
    <div class="row" style="margin-bottom:30px">
        <div class="card" style="text-align:center;flex:1;background:linear-gradient(135deg,#f0f9f4,#e6f9ee)"><div style="font-size:38px;font-weight:800;color:#00875a">500+</div><div style="color:#4a5568;font-weight:600">Routeurs Configurés</div><div style="color:#718096;font-size:11px">à Madagascar</div></div>
        <div class="card" style="text-align:center;flex:1;background:linear-gradient(135deg,#f0f7ff,#e6f2fb)"><div style="font-size:38px;font-weight:800;color:#0066cc">99.9%</div><div style="color:#4a5568;font-weight:600">Taux de Réussite</div><div style="color:#718096;font-size:11px">Configurations validées</div></div>
        <div class="card" style="text-align:center;flex:1;background:linear-gradient(135deg,#fff8e1,#fff3c4)"><div style="font-size:38px;font-weight:800;color:#f0a020">&lt;30s</div><div style="color:#4a5568;font-weight:600">Temps d'Application</div><div style="color:#718096;font-size:11px">Sans redémarrage</div></div>
        <div class="card" style="text-align:center;flex:1;background:linear-gradient(135deg,#fce4ec,#f8bbd0)"><div style="font-size:38px;font-weight:800;color:#c2185b">24/7</div><div style="color:#4a5568;font-weight:600">Support Client</div><div style="color:#718096;font-size:11px">Assistance dédiée</div></div>
    </div>
    <h2 style="text-align:center;color:#2d3748;margin:30px 0 15px">🎯 Nos Avantages</h2>
    <div class="row">
        <div class="card" style="flex:1;min-width:270px"><div style="font-size:35px">⚡</div><h3 style="color:#00875a;margin:8px 0">Génération Automatique</h3><p style="color:#4a5568;font-size:13px">Script personnalisé selon votre modèle exact. Détection auto des ports et interfaces WiFi.</p></div>
        <div class="card" style="flex:1;min-width:270px"><div style="font-size:35px">🛡️</div><h3 style="color:#0066cc;margin:8px 0">Safe-Mode Intégré</h3><p style="color:#4a5568;font-size:13px">Scripts avec <strong>Safe-Mode RouterOS v7</strong>, délais intelligents et gestion d'erreurs. <strong>Aucune coupure !</strong></p></div>
        <div class="card" style="flex:1;min-width:270px"><div style="font-size:35px">🔐</div><h3 style="color:#e65c00;margin:8px 0">Licence Unique</h3><p style="color:#4a5568;font-size:13px">Clé unique par routeur. Support technique prioritaire 30 jours inclus.</p></div>
    </div>
    <h2 style="text-align:center;color:#2d3748;margin:35px 0 15px">🚀 Technologies</h2>
    <div class="card"><div class="row">
        <div style="flex:1;min-width:260px"><h3 style="color:#00875a">✅ Optimisation Réseau</h3><ul style="list-style:none;color:#4a5568;font-size:13px"><li style="padding:6px 0;border-bottom:1px solid #edf2f7">🔧 Normalisation TTL (64/65/128)</li><li style="padding:6px 0;border-bottom:1px solid #edf2f7">📊 Clamp MSS & PMTU</li><li style="padding:6px 0;border-bottom:1px solid #edf2f7">🚫 Filtrage ICMP</li><li style="padding:6px 0">🔒 Firewall Layer 7</li></ul></div>
        <div style="flex:1;min-width:260px"><h3 style="color:#0066cc">☁️ Tunnel Cloudflare</h3><ul style="list-style:none;color:#4a5568;font-size:13px"><li style="padding:6px 0;border-bottom:1px solid #edf2f7">🔐 WireGuard AES-256</li><li style="padding:6px 0;border-bottom:1px solid #edf2f7">🌐 DNS over HTTPS</li><li style="padding:6px 0;border-bottom:1px solid #edf2f7">⚡ Latence optimisée</li><li style="padding:6px 0">🛡️ Bypass DPI</li></ul></div>
    </div></div>
    <h2 style="text-align:center;color:#2d3748;margin:35px 0 15px">📋 Comment ça marche ?</h2>
    <div class="row">
        <div class="card" style="flex:1;text-align:center"><div style="background:#00875a;color:#fff;width:40px;height:40px;border-radius:50%;line-height:40px;font-size:18px;font-weight:800;margin:auto">1</div><h4 style="margin:10px 0 5px;color:#00875a">Choisir</h4><p style="color:#718096;font-size:12px">Plan adapté</p></div>
        <div class="card" style="flex:1;text-align:center"><div style="background:#0066cc;color:#fff;width:40px;height:40px;border-radius:50%;line-height:40px;font-size:18px;font-weight:800;margin:auto">2</div><h4 style="margin:10px 0 5px;color:#0066cc">Configurer</h4><p style="color:#718096;font-size:12px">Modèle & options</p></div>
        <div class="card" style="flex:1;text-align:center"><div style="background:#f0a020;color:#fff;width:40px;height:40px;border-radius:50%;line-height:40px;font-size:18px;font-weight:800;margin:auto">3</div><h4 style="margin:10px 0 5px;color:#f0a020">Payer</h4><p style="color:#718096;font-size:12px">MVola / Orange / Airtel</p></div>
        <div class="card" style="flex:1;text-align:center"><div style="background:#c2185b;color:#fff;width:40px;height:40px;border-radius:50%;line-height:40px;font-size:18px;font-weight:800;margin:auto">4</div><h4 style="margin:10px 0 5px;color:#c2185b">Appliquer</h4><p style="color:#718096;font-size:12px">30 secondes !</p></div>
    </div>
    <h2 style="text-align:center;color:#2d3748;margin:35px 0 15px">💬 Témoignages</h2>
    <div class="row">
        <div class="card" style="flex:1;min-width:260px"><div style="color:#f0a020">⭐⭐⭐⭐⭐</div><p style="color:#4a5568;font-style:italic;margin:10px 0;font-size:13px">"3 routeurs configurés en 5 minutes. Aucune coupure. Je recommande !"</p><p style="color:#00875a;font-weight:700;font-size:13px">— Rakoto H., Tana</p></div>
        <div class="card" style="flex:1;min-width:260px"><div style="color:#f0a020">⭐⭐⭐⭐⭐</div><p style="color:#4a5568;font-style:italic;margin:10px 0;font-size:13px">"Le plan Hotspot est parfait pour mon business. Vouchers, PPPoE, tout pré-configuré."</p><p style="color:#00875a;font-weight:700;font-size:13px">— Faly R., Toamasina</p></div>
        <div class="card" style="flex:1;min-width:260px"><div style="color:#f0a020">⭐⭐⭐⭐⭐</div><p style="color:#4a5568;font-style:italic;margin:10px 0;font-size:13px">"Plus aucun problème de restriction FAI depuis le plan WARP. Vitesse stable !"</p><p style="color:#00875a;font-weight:700;font-size:13px">— Andry N., Fianarantsoa</p></div>
    </div>
    <div style="text-align:center;padding:40px 25px;background:linear-gradient(135deg,#f0f9f4,#e6f2fb);border-radius:14px;margin-top:30px">
        <h2 style="color:#00875a;margin-bottom:10px">Prêt à Optimiser Votre Réseau ?</h2>
        <p style="color:#4a5568;margin-bottom:15px">Rejoignez les 500+ opérateurs WiFi Zone</p>
        <a href="/" class="btn btn-g" style="padding:14px 35px;font-size:15px">🚀 Commencer</a>
    </div>"""
    return render_template_string(wrap("Pourquoi Nous", body))


@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        o = Order.query.filter((Order.order_id == code) | (Order.license_key == code)).first()
        if not o:
            flash(f"Aucune commande trouvée : {code}", "error")
            return redirect(url_for('track'))
        if o.status in ('validated', 'delivered'):
            return redirect(url_for('result', order_id=o.order_id))
        return redirect(url_for('order_status', order_id=o.order_id))
    body = """
    <div class="card" style="max-width:500px;margin:40px auto;text-align:center">
        <h2 style="color:#00875a">🔍 Récupérer Votre Configuration</h2>
        <p style="color:#718096;margin:10px 0 20px;font-size:13px">Entrez votre code commande (ex: KTK-260908-7F9A29)</p>
        <form method="POST">
            <input name="code" placeholder="KTK-XXXXXX-XXXXXX" required style="font-size:16px;text-align:center;letter-spacing:1px;font-weight:600;padding:14px">
            <button type="submit" class="btn btn-g" style="width:100%;margin-top:10px;padding:14px">🚀 Accéder à ma configuration</button>
        </form>
    </div>"""
    return render_template_string(wrap("Suivi", body))


@app.route('/configure/<pt>', methods=['GET', 'POST'])
def configure(pt):
    if pt not in PLANS:
        flash('Plan invalide', 'error')
        return redirect(url_for('index'))
    plan = PLANS[pt]
    if request.method == 'POST':
        o = Order()
        o.generate_order_id()
        o.plan_type = pt
        o.plan_price = plan['price']
        o.client_name = request.form['client_name']
        o.client_email = request.form['client_email']
        o.client_phone = request.form.get('client_phone', '')
        o.mikrotik_model = request.form['mikrotik_model']
        o.wan_interface = request.form.get('wan_interface', 'ether1')
        o.lan_network = request.form.get('lan_network', '192.168.88.0/24')
        o.lan_gateway = request.form.get('lan_gateway', '192.168.88.1')
        o.dhcp_pool = request.form.get('dhcp_pool', '192.168.88.10-192.168.88.250')
        o.ssid = request.form.get('ssid', 'WiFiZone-Ketrika')
        o.wifi_password = request.form.get('wifi_password', 'Ketrika2024')
        o.ttl_value = int(request.form.get('ttl_value', 65))
        lm2 = request.form.get('limit_mode', 'preset')
        if lm2 == 'nolimit':
            o.dl_limit = 'nolimit'
            o.ul_limit = 'nolimit'
        elif lm2 == 'custom':
            o.dl_limit = request.form.get('dl_custom', '10M').strip()
            o.ul_limit = request.form.get('ul_custom', '5M').strip()
        else:
            o.dl_limit = request.form.get('dl_preset', '10M')
            o.ul_limit = request.form.get('ul_preset', '5M')
        if pt == 'hotspot':
            o.hotspot_name = request.form.get('hotspot_name', 'WiFiZone')
            o.pppoe_enabled = 'pppoe' in request.form
            o.voucher_enabled = 'voucher' in request.form
        o.status = 'pending'
        db.session.add(o)
        db.session.commit()
        return redirect(url_for('payment', order_id=o.order_id))

    mo = "".join(f'<option value="{m}">{m}</option>' for m in MIKROTIK_MODELS)
    hs = ""
    if pt == 'hotspot':
        hs = """<h3 style="color:#0066cc;margin:18px 0 8px">🌐 Hotspot & PPPoE</h3>
        <div class="row"><div><label>Nom Hotspot</label><input name="hotspot_name" value="WiFiZone"></div></div>
        <div class="check"><input type="checkbox" name="pppoe" id="pppoe"><label for="pppoe" style="margin:0">Activer PPPoE</label></div>
        <div class="check"><input type="checkbox" name="voucher" id="voucher" checked><label for="voucher" style="margin:0">Générer vouchers</label></div>"""

    body = f"""
    <div class="card">
        <h2 style="color:{plan['color']};text-align:center">⚙️ {plan['name']}</h2>
        <p style="text-align:center;color:#718096;margin-bottom:18px"><strong>{plan['price']:,} {plan['currency']}</strong></p>
        <form method="POST">
            <h3 style="color:#0066cc;margin-bottom:8px">👤 Informations</h3>
            <div class="row">
                <div><label>Nom *</label><input name="client_name" required placeholder="Jean Rakoto"></div>
                <div><label>Email *</label><input name="client_email" type="email" required placeholder="jean@gmail.com"></div>
                <div><label>Téléphone</label><input name="client_phone" placeholder="034 00 000 00"></div>
            </div>
            <h3 style="color:#0066cc;margin:18px 0 8px">🖥️ Routeur MikroTik</h3>
            <div class="row"><div><label>Modèle *</label><select name="mikrotik_model" id="ms" required><option value="">-- Choisir --</option>{mo}</select></div></div>
            <div id="pp" style="background:#e6f9ee;padding:10px;border-radius:8px;margin:8px 0;display:none"><strong style="color:#00875a">📍 Ports :</strong> <span id="pv" style="display:flex;gap:5px;flex-wrap:wrap;margin-top:4px"></span></div>
            <h3 style="color:#0066cc;margin:18px 0 8px">🌐 Réseau</h3>
            <div class="row">
                <div><label>WAN</label><select name="wan_interface"><option value="ether1">ether1</option><option value="sfp1">sfp1</option></select></div>
                <div><label>LAN</label><input name="lan_network" value="192.168.88.0/24"></div>
                <div><label>Gateway</label><input name="lan_gateway" value="192.168.88.1"></div>
            </div>
            <div class="row">
                <div><label>DHCP Pool</label><input name="dhcp_pool" value="192.168.88.10-192.168.88.250"></div>
                <div><label>SSID</label><input name="ssid" value="WiFiZone-Ketrika"></div>
                <div><label>Mot de passe WiFi</label><input name="wifi_password" value="Ketrika2024"></div>
            </div>
            <h3 style="color:#0066cc;margin:18px 0 8px">🛡️ Optimisation Réseau</h3>
            <div class="row">
                <div><label>TTL</label><select name="ttl_value"><option value="65" selected>65 (Recommandé)</option><option value="64">64</option><option value="128">128</option></select></div>
                <div><label>Mode Limitation</label><select name="limit_mode" id="lm" onchange="tl()"><option value="preset">📊 Prédéfini</option><option value="nolimit">🚀 Sans Limite</option><option value="custom">⚙️ Personnalisé</option></select></div>
            </div>
            <div id="pl" class="row">
                <div><label>Download / client</label><select name="dl_preset"><option value="5M">5 Mbps</option><option value="10M" selected>10 Mbps</option><option value="20M">20 Mbps</option><option value="50M">50 Mbps</option><option value="100M">100 Mbps</option></select></div>
                <div><label>Upload / client</label><select name="ul_preset"><option value="2M">2 Mbps</option><option value="5M" selected>5 Mbps</option><option value="10M">10 Mbps</option><option value="20M">20 Mbps</option></select></div>
            </div>
            <div id="cl" class="row" style="display:none">
                <div><label>Download (ex: 25M, 500k)</label><input name="dl_custom" placeholder="25M" value="25M"></div>
                <div><label>Upload (ex: 10M, 200k)</label><input name="ul_custom" placeholder="10M" value="10M"></div>
            </div>
            <div id="nl" class="card" style="background:#e6f9ee;border-left:4px solid #00875a;padding:12px;display:none"><p style="color:#00875a;font-weight:600">🚀 Mode Illimité</p><p style="color:#4a5568;font-size:12px">Aucune restriction. Vitesse maximale pour tous.</p></div>
            {hs}
            <button type="submit" class="btn btn-g" style="width:100%;margin-top:20px;padding:14px;font-size:15px">💳 Passer au paiement — {plan['price']:,} {plan['currency']}</button>
        </form>
    </div>"""
    js = """<script>
    document.getElementById('ms').addEventListener('change',function(){var m=this.value;if(!m){document.getElementById('pp').style.display='none';return}fetch('/api/model/'+encodeURIComponent(m)).then(r=>r.json()).then(d=>{document.getElementById('pp').style.display='block';var v=document.getElementById('pv');v.innerHTML='<span style="background:#cc3333;color:#fff;padding:3px 8px;border-radius:4px;font-size:11px">ether1 WAN</span>';for(var i=2;i<=d.ports;i++)v.innerHTML+='<span style="background:#0066cc;color:#fff;padding:3px 8px;border-radius:4px;font-size:11px">ether'+i+'</span>';if(d.wifi)v.innerHTML+='<span style="background:#00875a;color:#fff;padding:3px 8px;border-radius:4px;font-size:11px">WiFi</span>'})});
    function tl(){var m=document.getElementById('lm').value;document.getElementById('pl').style.display=m==='preset'?'flex':'none';document.getElementById('cl').style.display=m==='custom'?'flex':'none';document.getElementById('nl').style.display=m==='nolimit'?'block':'none'}
    </script>"""
    return render_template_string(wrap("Configurer", body, js))


@app.route('/api/model/<mn>')
def api_model(mn):
    i = MIKROTIK_MODELS.get(mn)
    return jsonify(i) if i else (jsonify({'error': 'x'}), 404)


@app.route('/payment/<oid>', methods=['GET', 'POST'])
def payment(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    p = PLANS[o.plan_type]
    if request.method == 'POST':
        f = request.files.get('proof')
        if f and f.filename:
            fn = secure_filename(f"{o.order_id}_{f.filename}")
            fp = os.path.join(UPLOAD, fn)
            f.save(fp)
            o.payment_proof = fp
            o.payment_method = request.form.get('pm', 'mvola')
            db.session.commit()
            flash('Preuve reçue ! Validation en cours.', 'success')
            return redirect(url_for('order_status', order_id=o.order_id))
        flash('Ajoutez une capture', 'error')
    body = f"""
    <div class="card" style="max-width:580px;margin:auto">
        <h2 style="color:#00875a;text-align:center">💳 Paiement</h2>
        <p style="text-align:center;color:#718096">Code : <strong style="color:#0066cc">{o.order_id}</strong></p>
        <div style="background:#f0f9f4;padding:18px;text-align:center;border-radius:8px;margin:15px 0"><div style="font-size:32px;font-weight:700;color:#00875a">{p['price']:,} {p['currency']}</div><p style="color:#718096">{p['name']}</p></div>
        <form method="POST" enctype="multipart/form-data">
            <h3 style="color:#0066cc">1. Envoyez le montant :</h3>
            <div style="background:#fff8e1;padding:12px;border-radius:8px;border-left:4px solid #f0a020;margin:8px 0">
                <p>📱 MVola / Orange / Airtel : <strong style="font-size:20px;color:#00875a">034 00 000 00</strong></p>
                <p style="font-size:11px;color:#718096">Réf : {o.order_id}</p>
            </div>
            <h3 style="color:#0066cc;margin-top:15px">2. Preuve de paiement :</h3>
            <div style="border:2px dashed #00875a;padding:20px;text-align:center;border-radius:8px;cursor:pointer" onclick="document.getElementById('fi').click()">
                <p id="fn">📸 Cliquez pour choisir la capture</p>
                <input type="file" id="fi" name="proof" accept="image/*,.pdf" required style="display:none" onchange="document.getElementById('fn').textContent='✅ '+this.files[0].name">
            </div>
            <button type="submit" class="btn btn-g" style="width:100%;margin-top:12px">✅ Envoyer</button>
        </form>
    </div>"""
    return render_template_string(wrap("Paiement", body))


@app.route('/status/<oid>')
def order_status(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    btn = f'<a href="/result/{o.order_id}" class="btn btn-g" style="margin-top:12px">📥 Voir mon script</a>' if o.status in ('validated','delivered') else ''
    body = f"""
    <div class="card" style="max-width:480px;margin:35px auto;text-align:center">
        <h2 style="color:#0066cc">📦 Suivi Commande</h2>
        <p style="margin:8px 0"><strong>{o.order_id}</strong></p>
        <div style="font-size:45px;margin:12px 0">{'🟡' if o.status=='pending' else '✅'}</div>
        <h3>{o.status_badge}</h3>
        <p style="color:#718096;margin:12px 0">{'Validation en cours...' if o.status=='pending' else 'Configuration prête !'}</p>
        {btn}
    </div>"""
    return render_template_string(wrap("Statut", body))


@app.route('/result/<oid>')
def result(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    if o.status not in ('validated', 'delivered'):
        flash('Commande en attente', 'warning')
        return redirect(url_for('order_status', order_id=o.order_id))
    if not o.script_content:
        o.script_content = generate_full_script(o)
        db.session.commit()
    lim = "🚀 Illimitée" if o.dl_limit == 'nolimit' else f"⬇️ {o.dl_limit} / ⬆️ {o.ul_limit}"
    body = f"""
    <div class="card" style="background:#e6f9ee;border:2px solid #00875a;text-align:center;margin-bottom:20px">
        <h2 style="color:#00875a">🎉 Configuration Prête !</h2>
        <p>Code : <strong>{o.order_id}</strong> | Licence : <strong style="color:#0066cc">{o.license_key}</strong></p>
        <p style="color:#4a5568;font-size:13px;margin-top:5px">Modèle : {o.mikrotik_model} | Bande passante : {lim}</p>
    </div>
    <div class="card" style="background:#fff8e1;border-left:4px solid #f0a020;margin-bottom:15px">
        <h3 style="color:#8a5a00">⚠️ Avant de coller le script</h3>
        <p style="color:#4a5568;font-size:13px;margin:8px 0"><strong>🔒 Safe-Mode activé :</strong> Notre script utilise des délais et protections. Aucune déconnexion !</p>
        <p style="color:#4a5568;font-size:13px"><strong>💡 Conseil :</strong> Appuyez sur <strong>F4</strong> dans le terminal WinBox (Safe Mode) avant de coller.</p>
    </div>
    <div class="card" style="margin-bottom:15px">
        <h3 style="color:#00875a">📋 Méthode 1 : Terminal WinBox</h3>
        <p style="color:#718096;font-size:12px;margin:5px 0 8px">WinBox → New Terminal → F4 (Safe Mode) → Coller</p>
        <button class="btn btn-b" onclick="navigator.clipboard.writeText(document.getElementById('sc').innerText);this.textContent='✅ Copié !';setTimeout(()=>this.textContent='📋 Copier le script',2000)">📋 Copier le script</button>
        <pre id="sc" style="background:#1e2a3a;color:#a3e635;padding:12px;border-radius:8px;max-height:300px;overflow-y:auto;font-size:11px;margin-top:8px">{o.script_content}</pre>
    </div>
    <div class="card" style="border:2px solid #0066cc">
        <h3 style="color:#0066cc">📁 Méthode 2 : Fichier .rsc (⭐ Recommandé)</h3>
        <p style="color:#718096;font-size:12px;margin:5px 0">100% sans risque. WinBox → Files → Drag & Drop → Terminal : <code>/import file-name=ketrika_{o.order_id}.rsc</code></p>
        <a href="/download/{o.order_id}" class="btn btn-g" style="margin-top:8px">📥 Télécharger .rsc</a>
    </div>"""
    return render_template_string(wrap("Résultat", body))


@app.route('/download/<oid>')
def download(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    if o.status not in ('validated', 'delivered'):
        flash('Non autorisé', 'error')
        return redirect(url_for('index'))
    if not o.script_content:
        o.script_content = generate_full_script(o)
        db.session.commit()
    return send_file(io.BytesIO(o.script_content.encode()), mimetype='text/plain', as_attachment=True, download_name=f'ketrika_{o.order_id}.rsc')


# ==================== ADMIN ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        a = Admin.query.filter_by(username=request.form['username']).first()
        if a and check_password_hash(a.password_hash, request.form['password']):
            login_user(a)
            return redirect(url_for('admin_dash'))
        flash('Incorrect', 'error')
    return render_template_string(wrap("Admin", """<div class="card" style="max-width:360px;margin:70px auto"><h2 style="color:#00875a;text-align:center;margin-bottom:15px">🔐 Admin</h2><form method="POST"><label>Utilisateur</label><input name="username" required><label>Mot de passe</label><input name="password" type="password" required><button type="submit" class="btn btn-g" style="width:100%;margin-top:12px">Connexion</button></form></div>"""))

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dash():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    pend = sum(1 for o in orders if o.status == 'pending')
    deli = sum(1 for o in orders if o.status == 'delivered')
    rev = sum(o.plan_price for o in orders if o.status in ('validated','delivered'))
    rows = ""
    for o in orders:
        ac = ""
        if o.status == 'pending':
            ac = f'<form method="POST" action="/admin/val/{o.id}" style="display:inline"><button name="a" value="v" style="background:#00875a;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">✅</button></form> '
            ac += f'<form method="POST" action="/admin/val/{o.id}" style="display:inline"><button name="a" value="r" style="background:#cc3333;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px">❌</button></form>'
        if o.payment_proof:
            ac += f' <a href="/admin/proof/{o.id}" target="_blank">📸</a>'
        if o.license_key:
            ac += f'<br><small style="color:#00875a">🔑{o.license_key}</small>'
        rows += f'<tr><td><strong>{o.order_id}</strong></td><td>{o.client_name}<br><small style="color:#718096">{o.client_email}</small></td><td>{o.plan_type.upper()}</td><td>{o.mikrotik_model}</td><td>{o.plan_price:,}</td><td>{o.status_badge}</td><td>{ac}</td></tr>'
    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px"><h1 style="color:#00875a">Admin KETRIKA</h1><a href="/admin/logout" class="btn btn-r" style="padding:6px 12px;font-size:12px">Déconnexion</a></div>
    <div class="row" style="margin-bottom:15px">
        <div class="card" style="text-align:center;flex:1"><div style="font-size:26px;font-weight:700;color:#f0a020">{pend}</div><div style="color:#718096;font-size:12px">En attente</div></div>
        <div class="card" style="text-align:center;flex:1"><div style="font-size:26px;font-weight:700;color:#00875a">{deli}</div><div style="color:#718096;font-size:12px">Livrées</div></div>
        <div class="card" style="text-align:center;flex:1"><div style="font-size:24px;font-weight:700;color:#0066cc">{rev:,} Ar</div><div style="color:#718096;font-size:12px">Revenus</div></div>
    </div>
    <div class="card" style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Client</th><th>Plan</th><th>Modèle</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead><tbody>{rows if rows else '<tr><td colspan="7" style="text-align:center;color:#718096">Aucune commande</td></tr>'}</tbody></table></div>"""
    return render_template_string(wrap("Admin", body))

@app.route('/admin/val/<int:oid>', methods=['POST'])
@login_required
def admin_val(oid):
    o = Order.query.get_or_404(oid)
    if request.form.get('a') == 'v':
        o.generate_license_key()
        o.script_content = generate_full_script(o)
        o.status = 'delivered'
        o.validated_at = datetime.utcnow()
        db.session.commit()
        try:
            if app.config['MAIL_USERNAME']:
                msg = Message(f"🔑 Clé KETRIKA - {o.order_id}", recipients=[o.client_email])
                msg.body = f"Bonjour {o.client_name},\nCommande {o.order_id} validée !\nClé : {o.license_key}\nScript : {request.host_url}result/{o.order_id}"
                mail.send(msg)
        except:
            pass
        flash(f'{o.order_id} validé !', 'success')
    else:
        o.status = 'rejected'
        db.session.commit()
        flash(f'{o.order_id} rejeté', 'error')
    return redirect(url_for('admin_dash'))

@app.route('/admin/proof/<int:oid>')
@login_required
def admin_proof(oid):
    o = Order.query.get_or_404(oid)
    if o.payment_proof and os.path.exists(o.payment_proof):
        return send_file(o.payment_proof)
    flash('Introuvable', 'error')
    return redirect(url_for('admin_dash'))


@app.route('/faq')
def faq():
    body = """
    <div class="card"><h2 style="color:#00875a;margin-bottom:12px">❓ FAQ</h2>
    <p style="margin:8px 0"><strong>Comment fonctionne l'optimisation réseau ?</strong><br><span style="color:#4a5568">Notre script normalise le TTL et optimise les paquets pour éviter les restrictions FAI.</span></p>
    <p style="margin:8px 0"><strong>Faut-il redémarrer ?</strong><br><span style="color:#4a5568">Non. Safe-Mode + délais = aucune coupure.</span></p>
    <p style="margin:8px 0"><strong>Version RouterOS ?</strong><br><span style="color:#4a5568">v7 uniquement. Contactez-nous pour v6.</span></p></div>"""
    return render_template_string(wrap("FAQ", body))

@app.route('/conditions')
def conditions():
    body = """<div class="card"><h2 style="color:#00875a;margin-bottom:12px">📜 Conditions</h2><p style="color:#4a5568">1 licence = 1 routeur. Pas de remboursement (produit numérique). Support 30 jours.</p></div>"""
    return render_template_string(wrap("Conditions", body))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
