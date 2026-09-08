# app.py - KETRIKA MIKROTIK - Application Complète
import os
import io
from flask import (Flask, render_template_string, request, redirect,
                   url_for, flash, send_file, session, jsonify)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

from database import db, Admin, Order, MIKROTIK_MODELS, PLANS
from warp_api import generate_full_script

# ============================================
# INIT APP
# ============================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ketrika-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ketrika.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email (configure tes variables d'environnement)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_SENDER', 'ketrika@mikrotik.com')

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Créer tables + admin par défaut
with app.app_context():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash(os.environ.get('ADMIN_PASS', 'KetrikaAdmin2024!'))
        )
        db.session.add(admin)
        db.session.commit()


# ============================================
# TEMPLATE DE BASE (tout dans app.py)
# ============================================
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #0a0a2e; color: #e0e0e0; }
nav { background: #0d0d35; padding: 15px 30px; display: flex;
      justify-content: space-between; align-items: center; border-bottom: 1px solid #222; }
nav .logo { color: #00ff88; font-size: 22px; font-weight: bold; text-decoration: none; }
nav .logo span { color: #00ccff; }
nav .links a { color: #aaa; text-decoration: none; margin-left: 20px; font-size: 14px; }
nav .links a:hover { color: #00ff88; }
.container { max-width: 1100px; margin: auto; padding: 30px 20px; }
.flash { padding: 12px 20px; border-radius: 8px; margin-bottom: 15px; }
.flash.success { background: #0a3a0a; border: 1px solid #00ff88; color: #00ff88; }
.flash.error { background: #3a0a0a; border: 1px solid #ff4444; color: #ff4444; }
.flash.warning { background: #3a3a0a; border: 1px solid #ffaa00; color: #ffaa00; }
.btn { padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px;
       font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
.btn-primary { background: #00ff88; color: #000; }
.btn-primary:hover { background: #00cc66; }
.btn-blue { background: #00ccff; color: #000; }
.btn-orange { background: #ff6600; color: #fff; }
.btn-danger { background: #ff4444; color: #fff; }
.card { background: #111140; border-radius: 12px; padding: 25px; border: 1px solid #222; }
label { display: block; margin: 8px 0 4px; color: #aaa; font-size: 13px; }
input, select { width: 100%; padding: 10px; border: 1px solid #333;
                border-radius: 6px; background: #1a1a4e; color: #fff;
                font-size: 14px; margin-bottom: 5px; }
input:focus, select:focus { border-color: #00ff88; outline: none; }
.row { display: flex; gap: 15px; flex-wrap: wrap; }
.row > div { flex: 1; min-width: 220px; }
.check { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.check input { width: auto; }
footer { text-align: center; padding: 30px; color: #444; border-top: 1px solid #222; margin-top: 50px; }
"""

def wrap_page(title, body_html, extra_css="", extra_js=""):
    """Enveloppe le contenu dans le layout de base"""
    flash_html = """
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for cat, msg in messages %}
            <div class="flash {{ cat }}">{{ msg }}</div>
        {% endfor %}
    {% endif %}
    {% endwith %}
    """
    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - KETRIKA MIKROTIK</title>
<style>{BASE_CSS}{extra_css}</style>
</head><body>
<nav>
    <a href="/" class="logo">🛰️ KETRIKA <span>MIKROTIK</span></a>
    <div class="links">
        <a href="/">Accueil</a><a href="/plans">Plans</a>
        <a href="/faq">FAQ</a><a href="/conditions">Conditions</a>
        <a href="/admin">Admin</a>
    </div>
</nav>
<div class="container">{flash_html}{body_html}</div>
<footer>© 2024 KETRIKA MIKROTIK - WiFi Zone Solutions</footer>
{extra_js}
</body></html>"""


# ============================================
# PAGE ACCUEIL
# ============================================
@app.route('/')
def index():
    plans_html = ""
    for key, p in PLANS.items():
        popular = 'style="border-color:#00ff88;"' if p.get('popular') else ''
        badge = '<div style="background:#00ff88;color:#000;padding:3px 12px;border-radius:20px;font-size:11px;position:absolute;top:-10px;left:50%;transform:translateX(-50%);font-weight:bold;">⭐ POPULAIRE</div>' if p.get('popular') else ''
        features = "".join(f'<li style="padding:4px 0;font-size:13px;color:#bbb;">✅ {f}</li>' for f in p['features'])
        plans_html += f"""
        <div class="card" style="text-align:center;position:relative;{popular}">
            {badge}
            <h3 style="color:{p['color']}">{p['name']}</h3>
            <p style="color:#888">{p['subtitle']}</p>
            <div style="font-size:32px;font-weight:bold;color:{p['color']};margin:15px 0;">
                {p['price']:,} <small style="font-size:14px;color:#888">{p['currency']}</small>
            </div>
            <ul style="list-style:none;text-align:left;margin:15px 0;">{features}</ul>
            <a href="/configure/{key}" class="btn" style="width:100%;background:{p['color']};color:#000;">Configurer →</a>
        </div>"""

    models_html = "".join(f'<span style="background:#1a1a4e;padding:6px 14px;border-radius:20px;font-size:12px;color:#00ccff;border:1px solid #333;">{m}</span>' for m in MIKROTIK_MODELS)

    body = f"""
    <div style="text-align:center;padding:50px 20px;">
        <h1 style="font-size:44px;color:#00ff88;">🛰️ KETRIKA MIKROTIK</h1>
        <h2 style="color:#00ccff;font-weight:normal;">WiFi Zone Solutions pour Starlink</h2>
        <p style="color:#888;font-size:16px;max-width:700px;margin:15px auto;">
            Configurez votre routeur MikroTik automatiquement avec protection anti-détection.
            Scripts RouterOS v7. <strong>Sans redémarrage !</strong>
        </p>
        <a href="/plans" class="btn btn-primary" style="font-size:18px;padding:15px 40px;margin-top:20px;">⚡ VOIR LES PLANS</a>
    </div>

    <h2 style="text-align:center;color:#00ccff;margin:40px 0 20px;">🛡️ Notre Efficacité</h2>
    <div class="row">
        <div class="card" style="text-align:center;flex:1;">
            <div style="font-size:40px;">🔒</div><h3 style="color:#00ccff;">Fix TTL</h3>
            <p style="color:#888;font-size:13px;">TTL fixé à 65, Starlink ne voit pas le routeur</p>
        </div>
        <div class="card" style="text-align:center;flex:1;">
            <div style="font-size:40px;">☁️</div><h3 style="color:#00ccff;">WARP Tunnel</h3>
            <p style="color:#888;font-size:13px;">Chiffrement total via Cloudflare WARP</p>
        </div>
        <div class="card" style="text-align:center;flex:1;">
            <div style="font-size:40px;">🚫</div><h3 style="color:#00ccff;">Anti-DPI</h3>
            <p style="color:#888;font-size:13px;">Block ICMP + Clamp MSS + Normalisation</p>
        </div>
        <div class="card" style="text-align:center;flex:1;">
            <div style="font-size:40px;">📶</div><h3 style="color:#00ccff;">Hotspot Pro</h3>
            <p style="color:#888;font-size:13px;">Vouchers, PPPoE, limitation par client</p>
        </div>
    </div>

    <div class="row" style="margin:30px 0;">
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">500+</div><div style="color:#888;">Routeurs configurés</div></div>
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">99.8%</div><div style="color:#888;">Réussite</div></div>
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">0</div><div style="color:#888;">Redémarrage requis</div></div>
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">24/7</div><div style="color:#888;">Support</div></div>
    </div>

    <h2 style="text-align:center;color:#00ccff;margin:40px 0 20px;">📦 Nos Plans</h2>
    <div class="row">{plans_html}</div>

    <h2 style="text-align:center;color:#00ccff;margin:40px 0 15px;">🖥️ Modèles Supportés (RouterOS v7)</h2>
    <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;">{models_html}</div>
    <p style="text-align:center;color:#666;margin-top:10px;">Détection auto du nombre de ports</p>
    """
    return render_template_string(wrap_page("Accueil", body))


# ============================================
# PLANS
# ============================================
@app.route('/plans')
def plans():
    return redirect(url_for('index'))


# ============================================
# CONFIGURATEUR
# ============================================
@app.route('/configure/<plan_type>', methods=['GET', 'POST'])
def configure(plan_type):
    if plan_type not in PLANS:
        flash('Plan invalide', 'error')
        return redirect(url_for('index'))

    plan = PLANS[plan_type]

    if request.method == 'POST':
        order = Order()
        order.generate_order_id()
        order.plan_type = plan_type
        order.plan_price = plan['price']
        order.client_name = request.form['client_name']
        order.client_email = request.form['client_email']
        order.client_phone = request.form.get('client_phone', '')
        order.mikrotik_model = request.form['mikrotik_model']
        order.wan_interface = request.form.get('wan_interface', 'ether1')
        order.lan_network = request.form.get('lan_network', '192.168.88.0/24')
        order.lan_gateway = request.form.get('lan_gateway', '192.168.88.1')
        order.dhcp_pool = request.form.get('dhcp_pool', '192.168.88.10-192.168.88.250')
        order.ssid = request.form.get('ssid', 'WiFiZone-Ketrika')
        order.wifi_password = request.form.get('wifi_password', 'Ketrika2024')
        order.ttl_value = int(request.form.get('ttl_value', 65))
        order.dl_limit = request.form.get('dl_limit', '10M')
        order.ul_limit = request.form.get('ul_limit', '5M')

        if plan_type == 'hotspot':
            order.hotspot_name = request.form.get('hotspot_name', 'WiFiZone')
            order.pppoe_enabled = 'pppoe' in request.form
            order.voucher_enabled = 'voucher' in request.form

        order.status = 'pending'
        db.session.add(order)
        db.session.commit()
        return redirect(url_for('payment', order_id=order.order_id))

    # Formulaire
    models_opts = "".join(f'<option value="{m}">{m}</option>' for m in MIKROTIK_MODELS)

    hotspot_extra = ""
    if plan_type == 'hotspot':
        hotspot_extra = """
        <h3 style="color:#00ccff;margin:20px 0 10px;">🌐 Options Hotspot</h3>
        <div class="row">
            <div><label>Nom Hotspot</label><input name="hotspot_name" value="WiFiZone"></div>
        </div>
        <div class="check"><input type="checkbox" name="pppoe" id="pppoe"><label for="pppoe">Activer PPPoE</label></div>
        <div class="check"><input type="checkbox" name="voucher" id="voucher" checked><label for="voucher">Générer vouchers</label></div>
        """

    body = f"""
    <div class="card">
        <div style="text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid {plan['color']};">
            <h1 style="color:{plan['color']}">⚙️ {plan['name']}</h1>
            <p style="color:#888;">{plan['subtitle']} — {plan['price']:,} {plan['currency']}</p>
        </div>
        <form method="POST">
            <h3 style="color:#00ccff;margin-bottom:10px;">👤 Vos Informations</h3>
            <div class="row">
                <div><label>Nom complet *</label><input name="client_name" required></div>
                <div><label>Email *</label><input name="client_email" type="email" required></div>
                <div><label>Téléphone</label><input name="client_phone"></div>
            </div>

            <h3 style="color:#00ccff;margin:20px 0 10px;">🖥️ Routeur MikroTik</h3>
            <div class="row">
                <div>
                    <label>Modèle *</label>
                    <select name="mikrotik_model" id="modelSelect" required>
                        <option value="">-- Choisir --</option>{models_opts}
                    </select>
                </div>
            </div>
            <div id="portPreview" style="background:#0a3a0a;border:1px solid #00ff88;border-radius:8px;padding:15px;margin:10px 0;display:none;">
                <h4 style="color:#00ff88;">📍 Ports détectés :</h4>
                <div id="portVisual" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;"></div>
            </div>

            <h3 style="color:#00ccff;margin:20px 0 10px;">🌐 Réseau</h3>
            <div class="row">
                <div><label>WAN (Starlink)</label>
                    <select name="wan_interface"><option value="ether1">ether1</option><option value="sfp1">sfp1</option></select></div>
                <div><label>Réseau LAN</label><input name="lan_network" value="192.168.88.0/24"></div>
                <div><label>Gateway</label><input name="lan_gateway" value="192.168.88.1"></div>
            </div>
            <div class="row">
                <div><label>Pool DHCP</label><input name="dhcp_pool" value="192.168.88.10-192.168.88.250"></div>
                <div><label>SSID WiFi</label><input name="ssid" value="WiFiZone-Ketrika"></div>
                <div><label>Mot de passe WiFi</label><input name="wifi_password" value="Ketrika2024"></div>
            </div>

            <h3 style="color:#00ccff;margin:20px 0 10px;">🛡️ Anti-Détection</h3>
            <div class="row">
                <div><label>TTL</label>
                    <select name="ttl_value"><option value="64">64</option><option value="65" selected>65 ⭐</option><option value="128">128</option></select></div>
                <div><label>Download / client</label>
                    <select name="dl_limit"><option value="5M">5M</option><option value="10M" selected>10M</option><option value="20M">20M</option><option value="50M">50M</option></select></div>
                <div><label>Upload / client</label>
                    <select name="ul_limit"><option value="2M">2M</option><option value="5M" selected>5M</option><option value="10M">10M</option></select></div>
            </div>

            {hotspot_extra}

            <button type="submit" class="btn btn-primary" style="width:100%;padding:18px;font-size:18px;margin-top:25px;">
                💳 Passer au Paiement — {plan['price']:,} {plan['currency']}
            </button>
        </form>
    </div>
    """

    extra_js = """<script>
    document.getElementById('modelSelect').addEventListener('change', function(){
        var m = this.value;
        if(!m){document.getElementById('portPreview').style.display='none';return;}
        fetch('/api/model/'+encodeURIComponent(m)).then(r=>r.json()).then(d=>{
            var pv=document.getElementById('portPreview');
            var vis=document.getElementById('portVisual');
            pv.style.display='block'; vis.innerHTML='';
            vis.innerHTML+='<span style="background:#ff4444;color:#fff;padding:6px 12px;border-radius:6px;font-size:12px;">ether1 WAN</span>';
            for(var i=2;i<=d.ports;i++) vis.innerHTML+='<span style="background:#00ccff;color:#000;padding:6px 12px;border-radius:6px;font-size:12px;">ether'+i+' LAN</span>';
            if(d.wifi) vis.innerHTML+='<span style="background:#00ff88;color:#000;padding:6px 12px;border-radius:6px;font-size:12px;">wlan1 2.4G</span>';
            if(d.wifi5g) vis.innerHTML+='<span style="background:#00ff88;color:#000;padding:6px 12px;border-radius:6px;font-size:12px;">wlan2 5G</span>';
        });
    });
    </script>"""

    return render_template_string(wrap_page("Configurer", body, extra_js=extra_js))


# ============================================
# API MODÈLE
# ============================================
@app.route('/api/model/<model_name>')
def api_model(model_name):
    info = MIKROTIK_MODELS.get(model_name)
    if info:
        return jsonify(info)
    return jsonify({'error': 'Non trouvé'}), 404


# ============================================
# PAIEMENT
# ============================================
@app.route('/payment/<order_id>', methods=['GET', 'POST'])
def payment(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    plan = PLANS[order.plan_type]

    if request.method == 'POST':
        file = request.files.get('payment_proof')
        if file and file.filename:
            filename = secure_filename(f"{order.order_id}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            order.payment_proof = filepath
            order.payment_method = request.form.get('payment_method', 'mvola')
            db.session.commit()
            flash('Preuve envoyée ! En attente de validation.', 'success')
            return redirect(url_for('order_status', order_id=order.order_id))
        flash('Envoyez une preuve de paiement', 'error')

    body = f"""
    <div class="card" style="max-width:600px;margin:auto;">
        <h1 style="text-align:center;color:#00ff88;">💳 Paiement</h1>
        <p style="text-align:center;color:#888;">Commande: <strong>{order.order_id}</strong></p>
        <div style="text-align:center;margin:20px 0;">
            <div style="font-size:42px;color:#00ff88;font-weight:bold;">{plan['price']:,} {plan['currency']}</div>
            <p style="color:#888;">{plan['name']}</p>
        </div>
        <form method="POST" enctype="multipart/form-data">
            <h3 style="color:#00ccff;">1. Mode de paiement</h3>
            <div class="row" style="margin:15px 0;">
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:15px;">
                    <input type="radio" name="payment_method" value="mvola" checked style="width:auto;"> 📱 MVola
                </label>
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:15px;">
                    <input type="radio" name="payment_method" value="orange" style="width:auto;"> 🟠 Orange
                </label>
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:15px;">
                    <input type="radio" name="payment_method" value="airtel" style="width:auto;"> 🔴 Airtel
                </label>
            </div>
            <div class="card" style="background:#1a1a4e;text-align:center;margin:15px 0;">
                <p>Envoyez <strong>{plan['price']:,} Ar</strong> au:</p>
                <p style="font-size:24px;color:#00ff88;margin:10px 0;">034 00 000 00</p>
                <p style="color:#888;">Réf: {order.order_id}</p>
            </div>
            <h3 style="color:#00ccff;margin-top:20px;">2. Preuve de paiement</h3>
            <div style="border:2px dashed #333;border-radius:10px;padding:30px;text-align:center;margin:10px 0;cursor:pointer;"
                 onclick="document.getElementById('fileInput').click()">
                <div style="font-size:40px;">📸</div>
                <p id="fileName">Cliquez pour envoyer une capture</p>
                <input type="file" id="fileInput" name="payment_proof" accept="image/*,.pdf" required style="display:none;"
                       onchange="document.getElementById('fileName').textContent=this.files[0].name">
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%;padding:16px;font-size:16px;">
                ✅ Envoyer la preuve
            </button>
        </form>
    </div>
    """
    return render_template_string(wrap_page("Paiement", body))


# ============================================
# STATUT COMMANDE
# ============================================
@app.route('/status/<order_id>')
def order_status(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()

    icon = {'pending': '🟡', 'validated': '🟢', 'delivered': '✅', 'rejected': '🔴'}.get(order.status, '❓')
    action_btn = ""
    if order.status in ['validated', 'delivered']:
        action_btn = f'<a href="/result/{order.order_id}" class="btn btn-primary" style="margin-top:15px;">📥 Voir ma configuration</a>'

    body = f"""
    <div class="card" style="max-width:500px;margin:auto;text-align:center;">
        <h1 style="color:#00ccff;">📦 Suivi Commande</h1>
        <p style="font-size:18px;margin:10px 0;">{order.order_id}</p>
        <div style="font-size:60px;margin:20px 0;">{icon}</div>
        <h2>{order.status_badge}</h2>
        <p style="color:#888;margin-top:15px;">
            {'Votre paiement est en cours de vérification. Vous recevrez un email à ' + order.client_email if order.status == 'pending' else 'Votre configuration est prête !'}
        </p>
        {action_btn}
    </div>
    """
    return render_template_string(wrap_page("Statut", body))


# ============================================
# RÉSULTAT + 3 MÉTHODES
# ============================================
@app.route('/result/<order_id>')
def result(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()

    if order.status not in ['validated', 'delivered']:
        flash('Commande pas encore validée', 'warning')
        return redirect(url_for('order_status', order_id=order.order_id))

    if not order.script_content:
        order.script_content = generate_full_script(order)
        db.session.commit()

    body = f"""
    <div style="text-align:center;padding:25px;background:#0a3a0a;border:2px solid #00ff88;border-radius:12px;margin-bottom:25px;">
        <div style="font-size:50px;">✅</div>
        <h1 style="color:#00ff88;">Configuration Prête !</h1>
        <p style="color:#888;">{order.order_id}</p>
        <div style="font-size:24px;letter-spacing:3px;color:#00ff88;background:#0a0a2e;padding:12px 20px;border-radius:8px;display:inline-block;margin:15px 0;">
            {order.license_key}
        </div>
    </div>

    <h2 style="text-align:center;color:#00ccff;margin:25px 0;">📥 3 Méthodes (sans redémarrage)</h2>

    <div class="card" style="border-left:4px solid #00ff88;margin:15px 0;">
        <h3 style="color:#00ff88;">📋 Méthode 1 — Terminal WinBox (la plus simple)</h3>
        <p style="color:#888;margin:8px 0;">1. Ouvrez <strong>WinBox</strong> → connectez-vous<br>
        2. Menu <strong>New Terminal</strong><br>
        3. <strong>Copiez</strong> le script ci-dessous → <strong>Clic droit → Paste</strong><br>
        4. Attendez 30 secondes ✅</p>
        <button class="btn btn-blue" onclick="copyScript()" style="margin:10px 0;">📋 Copier tout le script</button>
        <pre id="scriptBox" style="background:#050520;border:1px solid #333;border-radius:8px;padding:15px;max-height:350px;overflow-y:auto;font-size:11px;color:#00ff88;line-height:1.5;white-space:pre-wrap;">{order.script_content}</pre>
    </div>

    <div class="card" style="border-left:4px solid #00ccff;margin:15px 0;">
        <h3 style="color:#00ccff;">📁 Méthode 2 — Upload fichier .rsc</h3>
        <p style="color:#888;margin:8px 0;">1. <a href="/download/{order.order_id}" class="btn btn-blue" style="padding:6px 15px;font-size:13px;">📥 Télécharger le .rsc</a><br>
        2. WinBox → <strong>Files</strong> → Drag & Drop le fichier<br>
        3. New Terminal → Taper: <code style="background:#050520;padding:3px 8px;border-radius:4px;color:#00ccff;">/import file-name=ketrika_{order.order_id}.rsc</code></p>
    </div>

    <div class="card" style="border-left:4px solid #ff6600;margin:15px 0;">
        <h3 style="color:#ff6600;">💻 Méthode 3 — SSH</h3>
        <p style="color:#888;margin:8px 0;">1. Terminal PC: <code style="background:#050520;padding:3px 8px;border-radius:4px;color:#ff6600;">ssh admin@{order.lan_gateway}</code><br>
        2. Transférer: <code style="background:#050520;padding:3px 8px;border-radius:4px;color:#ff6600;">scp ketrika.rsc admin@{order.lan_gateway}:/</code><br>
        3. Importer: <code style="background:#050520;padding:3px 8px;border-radius:4px;color:#ff6600;">/import file-name=ketrika.rsc</code></p>
    </div>

    <div class="card" style="border:1px solid #00ff88;margin-top:20px;">
        <h3 style="color:#00ff88;">🔍 Vérification</h3>
        <code style="display:block;background:#050520;padding:8px;border-radius:4px;color:#00ff88;margin:5px 0;font-size:12px;">/ip firewall mangle print where comment~"KETRIKA"</code>
        <code style="display:block;background:#050520;padding:8px;border-radius:4px;color:#00ff88;margin:5px 0;font-size:12px;">/tool traceroute 1.1.1.1</code>
        <p style="color:#888;margin-top:8px;">✅ TTL doit être <strong>{order.ttl_value}</strong></p>
    </div>
    """

    extra_js = """<script>
    function copyScript(){
        var t=document.getElementById('scriptBox').textContent;
        navigator.clipboard.writeText(t).then(function(){
            var b=event.target; b.textContent='✅ Copié !'; b.style.background='#00ff88';
            setTimeout(function(){b.textContent='📋 Copier tout le script';b.style.background='#00ccff';},3000);
        });
    }
    </script>"""

    return render_template_string(wrap_page("Résultat", body, extra_js=extra_js))


@app.route('/download/<order_id>')
def download(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    if order.status not in ['validated', 'delivered']:
        flash('Pas encore validé', 'error')
        return redirect(url_for('index'))
    if not order.script_content:
        order.script_content = generate_full_script(order)
        db.session.commit()
    return send_file(
        io.BytesIO(order.script_content.encode('utf-8')),
        mimetype='text/plain', as_attachment=True,
        download_name=f'ketrika_{order.order_id}.rsc'
    )


# ============================================
# ADMIN
# ============================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username']).first()
        if admin and check_password_hash(admin.password_hash, request.form['password']):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('Identifiants incorrects', 'error')
    body = """
    <div style="max-width:380px;margin:80px auto;">
        <div class="card">
            <h2 style="text-align:center;color:#00ff88;margin-bottom:20px;">🔐 Admin</h2>
            <form method="POST">
                <label>Utilisateur</label><input name="username" required autofocus>
                <label>Mot de passe</label><input name="password" type="password" required>
                <button type="submit" class="btn btn-primary" style="width:100%;margin-top:15px;">Connexion</button>
            </form>
        </div>
    </div>"""
    return render_template_string(wrap_page("Admin Login", body))

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    pending = Order.query.filter_by(status='pending').count()
    delivered = Order.query.filter_by(status='delivered').count()
    revenue = db.session.query(db.func.sum(Order.plan_price)).filter(
        Order.status.in_(['validated','delivered'])).scalar() or 0

    rows = ""
    for o in orders:
        badge_cls = {'pending':'#ffaa00','validated':'#00ff88','delivered':'#00ccff','rejected':'#ff4444'}.get(o.status,'#888')
        actions = ""
        if o.status == 'pending' and o.payment_proof:
            actions += f"""
            <form method="POST" action="/admin/validate/{o.id}" style="display:inline;">
                <button name="action" value="validate" style="background:#00ff88;color:#000;padding:4px 10px;border:none;border-radius:4px;font-size:11px;cursor:pointer;">✅ Valider</button>
            </form>
            <form method="POST" action="/admin/validate/{o.id}" style="display:inline;">
                <button name="action" value="reject" style="background:#ff4444;color:#fff;padding:4px 10px;border:none;border-radius:4px;font-size:11px;cursor:pointer;">❌</button>
            </form>"""
        if o.payment_proof:
            actions += f' <a href="/admin/proof/{o.id}" target="_blank" style="color:#00ccff;font-size:11px;">📸</a>'
        if o.license_key:
            actions += f' <span style="color:#00ff88;font-size:10px;">🔑{o.license_key}</span>'

        rows += f"""<tr>
            <td><strong>{o.order_id}</strong></td>
            <td>{o.created_at.strftime('%d/%m %H:%M')}</td>
            <td>{o.client_name}<br><small style="color:#888">{o.client_email}</small></td>
            <td>{o.plan_type.upper()}</td>
            <td style="font-size:11px;">{o.mikrotik_model}</td>
            <td>{o.plan_price:,} Ar</td>
            <td><span style="color:{badge_cls};font-size:12px;">{o.status_badge}</span></td>
            <td>{actions}</td>
        </tr>"""

    body = f"""
    <h1 style="color:#00ff88;">🔐 Admin KETRIKA</h1>
    <p style="color:#888;">Bienvenue | <a href="/admin/logout" style="color:#ff4444;">Déconnexion</a></p>
    <div class="row" style="margin:20px 0;">
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#ffaa00;">{pending}</div><div style="color:#888;">En attente</div></div>
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">{delivered}</div><div style="color:#888;">Livrées</div></div>
        <div class="card" style="text-align:center;flex:1;"><div style="font-size:28px;font-weight:bold;color:#00ff88;">{revenue:,} Ar</div><div style="color:#888;">Revenus</div></div>
    </div>
    <div class="card" style="overflow-x:auto;">
        <h2 style="color:#00ccff;">📋 Commandes</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:15px;">
            <thead><tr style="background:#1a1a4e;">
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">ID</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Date</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Client</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Plan</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Modèle</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Prix</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Statut</th>
                <th style="padding:10px;text-align:left;color:#00ccff;font-size:12px;">Actions</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""
    return render_template_string(wrap_page("Admin", body))


@app.route('/admin/validate/<int:order_id>', methods=['POST'])
@login_required
def admin_validate(order_id):
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')

    if action == 'validate':
        order.generate_license_key()
        order.script_content = generate_full_script(order)
        order.status = 'validated'
        order.validated_at = datetime.utcnow()
        db.session.commit()

        # Envoyer email
        try:
            msg = Message(
                subject=f"🔑 Clé KETRIKA - {order.order_id}",
                recipients=[order.client_email]
            )
            msg.html = f"""
            <div style="font-family:Arial;max-width:600px;margin:auto;background:#0a0a2e;color:#fff;padding:30px;border-radius:10px;">
                <h1 style="color:#00ff88;text-align:center;">🛰️ KETRIKA MIKROTIK</h1>
                <p>Bonjour <strong>{order.client_name}</strong>,</p>
                <p>Votre paiement est validé !</p>
                <div style="background:#1a1a4e;padding:20px;border-radius:8px;text-align:center;margin:20px 0;">
                    <p style="color:#aaa;">Votre Clé</p>
                    <h2 style="color:#00ff88;letter-spacing:3px;">{order.license_key}</h2>
                </div>
                <p>👉 <a href="https://VOTRE-DOMAINE/result/{order.order_id}" style="color:#00ff88;">Voir ma configuration</a></p>
                <p style="color:#888;font-size:12px;">© KETRIKA MIKROTIK</p>
            </div>"""
            mail.send(msg)
            order.status = 'delivered'
            order.delivered_at = datetime.utcnow()
            db.session.commit()
            flash(f'✅ {order.order_id} validé + email envoyé', 'success')
        except Exception as e:
            flash(f'⚠️ Validé mais email échoué: {e}. Clé: {order.license_key}', 'warning')

    elif action == 'reject':
        order.status = 'rejected'
        db.session.commit()
        flash(f'🔴 {order.order_id} rejeté', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/proof/<int:order_id>')
@login_required
def admin_proof(order_id):
    order = Order.query.get_or_404(order_id)
    if order.payment_proof and os.path.exists(order.payment_proof):
        return send_file(order.payment_proof)
    flash('Preuve non trouvée', 'error')
    return redirect(url_for('admin_dashboard'))


# ============================================
# FAQ & CONDITIONS
# ============================================
@app.route('/faq')
def faq():
    body = """
    <h1 style="text-align:center;color:#00ff88;margin-bottom:25px;">❓ FAQ</h1>
    <div class="card" style="margin:10px 0;cursor:pointer;" onclick="this.querySelector('.a').style.display=this.querySelector('.a').style.display==='block'?'none':'block'">
        <strong>Comment Starlink détecte le partage ?</strong>
        <div class="a" style="display:none;color:#888;margin-top:10px;">Starlink analyse le TTL. Un routeur diminue le TTL de 1. Notre script fixe le TTL à 65 pour masquer le routeur.</div>
    </div>
    <div class="card" style="margin:10px 0;cursor:pointer;" onclick="this.querySelector('.a').style.display=this.querySelector('.a').style.display==='block'?'none':'block'">
        <strong>Faut-il redémarrer le routeur ?</strong>
        <div class="a" style="display:none;color:#888;margin-top:10px;"><strong>NON !</strong> Les 3 méthodes (Terminal, Upload .rsc, SSH) s'appliquent instantanément sans redémarrage.</div>
    </div>
    <div class="card" style="margin:10px 0;cursor:pointer;" onclick="this.querySelector('.a').style.display=this.querySelector('.a').style.display==='block'?'none':'block'">
        <strong>Quelle version RouterOS ?</strong>
        <div class="a" style="display:none;color:#888;margin-top:10px;">RouterOS v7 (7.x+). Contactez-nous pour v6.</div>
    </div>
    <div class="card" style="margin:10px 0;cursor:pointer;" onclick="this.querySelector('.a').style.display=this.querySelector('.a').style.display==='block'?'none':'block'">
        <strong>Qu'est-ce que WARP ?</strong>
        <div class="a" style="display:none;color:#888;margin-top:10px;">Tunnel WireGuard vers Cloudflare WARP. Chiffre tout le trafic. Starlink ne peut plus inspecter les paquets (DPI).</div>
    </div>
    <div class="card" style="margin:10px 0;cursor:pointer;" onclick="this.querySelector('.a').style.display=this.querySelector('.a').style.display==='block'?'none':'block'">
        <strong>Délai de livraison ?</strong>
        <div class="a" style="display:none;color:#888;margin-top:10px;">1 à 24h après validation du paiement. Email automatique avec la clé.</div>
    </div>"""
    return render_template_string(wrap_page("FAQ", body))


@app.route('/conditions')
def conditions():
    body = """
    <h1 style="text-align:center;color:#00ff88;margin-bottom:25px;">📜 Conditions</h1>
    <div class="card">
        <h3 style="color:#00ccff;">1. Service</h3><p>Scripts de configuration MikroTik RouterOS v7 pour Starlink.</p>
        <h3 style="color:#00ccff;margin-top:15px;">2. Licence</h3><p>1 clé = 1 routeur. Revente interdite.</p>
        <h3 style="color:#00ccff;margin-top:15px;">3. Responsabilité</h3><p>L'utilisateur est responsable de l'utilisation sur son réseau.</p>
        <h3 style="color:#00ccff;margin-top:15px;">4. Paiement</h3><p>Paiement avant livraison. Pas de remboursement (produit numérique).</p>
        <h3 style="color:#00ccff;margin-top:15px;">5. Support</h3><p>Support technique inclus 30 jours.</p>
    </div>"""
    return render_template_string(wrap_page("Conditions", body))


# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
