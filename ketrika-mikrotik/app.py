# app.py - KETRIKA MIKROTIK (Version Stable Render)
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

# --- CONFIGURATION SÉCURISÉE RENDER ---
app.secret_key = os.environ.get('SECRET_KEY', 'ketrika-cle-secrete-production-2024')

# Correction automatique postgres:// -> postgresql:// pour Render
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ketrika.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail Config
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_SENDER', 'ketrika@mikrotik.com')

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialisation extensions
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Création tables et admin par défaut
with app.app_context():
    try:
        db.create_all()
        admin_user = os.environ.get('ADMIN_USER', 'admin')
        admin_pass = os.environ.get('ADMIN_PASS', 'KetrikaAdmin2024!')
        if not Admin.query.filter_by(username=admin_user).first():
            admin = Admin(
                username=admin_user,
                password_hash=generate_password_hash(admin_pass)
            )
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        print(f"Erreur initialisation DB: {e}")


# --- CSS THÈME CLAIR ---
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    background: #f4f7f6;
    color: #2c3e50;
    min-height: 100vh;
    line-height: 1.6;
}
nav {
    background: #ffffff;
    padding: 15px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e1e8ed;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
nav .logo { color: #00875a; font-size: 22px; font-weight: 700; text-decoration: none; }
nav .logo span { color: #0066cc; }
nav .links a {
    color: #5a6c7d;
    text-decoration: none;
    margin-left: 20px;
    font-size: 14px;
    font-weight: 500;
}
nav .links a:hover { color: #00875a; }
.container { max-width: 1100px; margin: auto; padding: 30px 20px; }
.flash {
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 15px;
    font-size: 14px;
}
.flash.success { background: #e6f9ee; border-left: 4px solid #00875a; color: #006644; }
.flash.error { background: #fde8e8; border-left: 4px solid #cc3333; color: #991111; }
.flash.warning { background: #fff8e1; border-left: 4px solid #f0a020; color: #8a5a00; }
.btn {
    padding: 12px 28px;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
}
.btn-primary { background: #00875a; color: #fff; }
.btn-primary:hover { background: #006644; }
.btn-blue { background: #0066cc; color: #fff; }
.btn-blue:hover { background: #004c99; }
.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 25px;
    border: 1px solid #e1e8ed;
    box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}
label { display: block; margin: 10px 0 5px; color: #4a5568; font-size: 13px; font-weight: 600; }
input, select {
    width: 100%;
    padding: 11px;
    border: 1px solid #d1d9e0;
    border-radius: 8px;
    background: #f8fafc;
    color: #2c3e50;
    font-size: 14px;
    margin-bottom: 5px;
}
input:focus, select:focus {
    border-color: #00875a;
    background: #fff;
    outline: none;
}
.row { display: flex; gap: 15px; flex-wrap: wrap; }
.row > div { flex: 1; min-width: 220px; }
.check {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0;
    padding: 10px;
    background: #f8fafc;
    border-radius: 6px;
}
.check input { width: auto; }
footer {
    text-align: center;
    padding: 30px;
    color: #718096;
    border-top: 1px solid #e1e8ed;
    margin-top: 50px;
    background: #ffffff;
}
table { width: 100%; border-collapse: collapse; }
th { padding: 12px; text-align: left; background: #f0f4f8; font-size: 13px; color: #4a5568; }
td { padding: 12px; border-bottom: 1px solid #edf2f7; font-size: 13px; }
"""

def wrap_page(title, body_html, extra_js=""):
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
<title>{title} - KETRIKA</title>
<style>{BASE_CSS}</style>
</head><body>
<nav>
    <a href="/" class="logo">🛰️ KETRIKA <span>MIKROTIK</span></a>
    <div class="links">
        <a href="/">Accueil</a>
        <a href="/faq">FAQ</a>
        <a href="/conditions">Conditions</a>
        <a href="/admin">Admin</a>
    </div>
</nav>
<div class="container">{flash_html}{body_html}</div>
<footer>© 2024 KETRIKA MIKROTIK - Solutions WiFi Zone Starlink 🛰️</footer>
{extra_js}
</body></html>"""


# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    plans_html = ""
    for key, p in PLANS.items():
        border = f"border: 2px solid {p['color']};" if p.get('popular') else ""
        badge = f'<div style="background:{p["color"]};color:#fff;padding:4px 12px;border-radius:12px;font-size:11px;font-weight:700;display:inline-block;margin-bottom:10px;">⭐ RECOMMANDÉ</div><br>' if p.get('popular') else ''
        features = "".join(f'<li style="padding:6px 0;font-size:13px;border-bottom:1px solid #edf2f7;">✅ {f}</li>' for f in p['features'])
        plans_html += f"""
        <div class="card" style="text-align:center;flex:1;min-width:280px;{border}">
            {badge}
            <h3 style="color:{p['color']};font-size:20px;">{p['name']}</h3>
            <p style="color:#718096;font-size:13px;margin:5px 0 15px;">{p['subtitle']}</p>
            <div style="font-size:32px;font-weight:700;color:{p['color']};margin-bottom:15px;">
                {p['price']:,} <small style="font-size:14px;color:#718096;">{p['currency']}</small>
            </div>
            <ul style="list-style:none;text-align:left;margin-bottom:20px;">{features}</ul>
            <a href="/configure/{key}" class="btn" style="width:100%;background:{p['color']};color:#fff;">Configurer →</a>
        </div>"""

    models_html = "".join(f'<span style="background:#fff;padding:6px 12px;border-radius:15px;font-size:12px;color:#0066cc;border:1px solid #d1d9e0;">{m}</span>' for m in MIKROTIK_MODELS)

    body = f"""
    <div style="text-align:center;padding:50px 20px;background:#fff;border-radius:16px;border:1px solid #e1e8ed;margin-bottom:30px;">
        <h1 style="font-size:42px;color:#00875a;margin-bottom:10px;">🛰️ KETRIKA MIKROTIK</h1>
        <h2 style="color:#0066cc;font-weight:400;font-size:20px;">Configuration Automatique Anti-Détection Starlink</h2>
        <p style="color:#5a6c7d;max-width:700px;margin:15px auto;">
            Configurez votre routeur MikroTik en 1 clic. <strong>Sans redémarrage requis !</strong>
        </p>
    </div>

    <h2 style="text-align:center;color:#2d3748;margin:30px 0 20px;">📦 Nos Plans Disponibles</h2>
    <div class="row">{plans_html}</div>

    <h2 style="text-align:center;color:#2d3748;margin:40px 0 15px;font-size:20px;">🖥️ Modèles MikroTik Compatibles (RouterOS v7)</h2>
    <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;">{models_html}</div>
    """
    return render_template_string(wrap_page("Accueil", body))


@app.route('/configure/<plan_type>', methods=['GET', 'POST'])
def configure(plan_type):
    if plan_type not in PLANS:
        flash('Plan sélectionné invalide', 'error')
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

    models_opts = "".join(f'<option value="{m}">{m}</option>' for m in MIKROTIK_MODELS)

    hotspot_extra = ""
    if plan_type == 'hotspot':
        hotspot_extra = """
        <h3 style="color:#0066cc;margin:20px 0 10px;">🌐 Configuration Hotspot & PPPoE</h3>
        <div class="row">
            <div><label>Nom Hotspot</label><input name="hotspot_name" value="WiFiZone"></div>
        </div>
        <div class="check"><input type="checkbox" name="pppoe" id="pppoe"><label for="pppoe" style="margin:0;">Activer serveur PPPoE</label></div>
        <div class="check"><input type="checkbox" name="voucher" id="voucher" checked><label for="voucher" style="margin:0;">Générer vouchers automatiques</label></div>
        """

    body = f"""
    <div class="card">
        <h2 style="color:{plan['color']};text-align:center;">⚙️ {plan['name']}</h2>
        <p style="text-align:center;color:#718096;margin-bottom:20px;">Prix : <strong>{plan['price']:,} {plan['currency']}</strong></p>

        <form method="POST">
            <h3 style="color:#0066cc;margin-bottom:10px;">👤 Informations Client</h3>
            <div class="row">
                <div><label>Nom complet *</label><input name="client_name" required placeholder="Jean Dupont"></div>
                <div><label>Email (pour recevoir la clé) *</label><input name="client_email" type="email" required placeholder="client@gmail.com"></div>
                <div><label>Téléphone</label><input name="client_phone" placeholder="034 00 000 00"></div>
            </div>

            <h3 style="color:#0066cc;margin:20px 0 10px;">🖥️ Routeur MikroTik</h3>
            <div class="row">
                <div>
                    <label>Modèle MikroTik *</label>
                    <select name="mikrotik_model" id="modelSelect" required>
                        <option value="">-- Choisir le modèle --</option>{models_opts}
                    </select>
                </div>
            </div>
            <div id="portPreview" style="background:#e6f9ee;padding:12px;border-radius:8px;margin:10px 0;display:none;">
                <strong style="color:#00875a;">📍 Ports détectés :</strong>
                <div id="portVisual" style="display:flex;gap:6px;margin-top:5px;flex-wrap:wrap;"></div>
            </div>

            <h3 style="color:#0066cc;margin:20px 0 10px;">🌐 Paramètres Réseau</h3>
            <div class="row">
                <div><label>Interface WAN (Starlink)</label><select name="wan_interface"><option value="ether1">ether1</option><option value="sfp1">sfp1</option></select></div>
                <div><label>Réseau LAN</label><input name="lan_network" value="192.168.88.0/24"></div>
                <div><label>IP Passerelle</label><input name="lan_gateway" value="192.168.88.1"></div>
            </div>
            <div class="row">
                <div><label>Pool DHCP</label><input name="dhcp_pool" value="192.168.88.10-192.168.88.250"></div>
                <div><label>Nom WiFi (SSID)</label><input name="ssid" value="WiFiZone-Ketrika"></div>
                <div><label>Mot de passe WiFi</label><input name="wifi_password" value="Ketrika2024"></div>
            </div>

            <h3 style="color:#0066cc;margin:20px 0 10px;">🛡️ Anti-Détection & Limites</h3>
            <div class="row">
                <div><label>TTL Fixé</label><select name="ttl_value"><option value="65" selected>65 (Recommandé Starlink)</option><option value="64">64</option></select></div>
                <div><label>Download max / client</label><select name="dl_limit"><option value="5M">5 Mbps</option><option value="10M" selected>10 Mbps</option><option value="20M">20 Mbps</option></select></div>
                <div><label>Upload max / client</label><select name="ul_limit"><option value="2M">2 Mbps</option><option value="5M" selected>5 Mbps</option><option value="10M">10 Mbps</option></select></div>
            </div>

            {hotspot_extra}

            <button type="submit" class="btn btn-primary" style="width:100%;margin-top:25px;padding:15px;font-size:16px;">
                💳 Valider et passer au paiement
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
            vis.innerHTML+='<span style="background:#cc3333;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;">ether1 (WAN)</span>';
            for(var i=2;i<=d.ports;i++) vis.innerHTML+='<span style="background:#0066cc;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;">ether'+i+' (LAN)</span>';
            if(d.wifi) vis.innerHTML+='<span style="background:#00875a;color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;">WiFi</span>';
        });
    });
    </script>"""

    return render_template_string(wrap_page("Configurer", body, extra_js=extra_js))


@app.route('/api/model/<model_name>')
def api_model(model_name):
    info = MIKROTIK_MODELS.get(model_name)
    if info:
        return jsonify(info)
    return jsonify({'error': 'Non trouvé'}), 404


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
            flash('Preuve de paiement enregistrée ! Validation en cours.', 'success')
            return redirect(url_for('order_status', order_id=order.order_id))
        flash('Veuillez ajouter une capture de votre paiement', 'error')

    body = f"""
    <div class="card" style="max-width:600px;margin:auto;">
        <h2 style="color:#00875a;text-align:center;">💳 Paiement de la commande</h2>
        <p style="text-align:center;color:#718096;">Référence : <strong>{order.order_id}</strong></p>

        <div style="background:#f0f9f4;padding:20px;text-align:center;border-radius:8px;margin:20px 0;">
            <div style="font-size:36px;font-weight:700;color:#00875a;">{plan['price']:,} {plan['currency']}</div>
            <p style="color:#718096;">{plan['name']}</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <h3 style="color:#0066cc;">1. Envoyez le montant au numéro suivant :</h3>
            <div style="background:#fff8e1;padding:15px;border-radius:8px;border-left:4px solid #f0a020;margin:10px 0;">
                <p>📱 <strong>MVola / Orange Money / Airtel Money</strong></p>
                <p style="font-size:22px;color:#00875a;font-weight:700;margin:5px 0;">034 00 000 00</p>
                <p style="font-size:12px;color:#718096;">Nom : KETRIKA | Référence à mentionner : {order.order_id}</p>
            </div>

            <h3 style="color:#0066cc;margin-top:20px;">2. Uploader la preuve de transfert :</h3>
            <div style="border:2px dashed #00875a;padding:25px;text-align:center;border-radius:8px;margin:10px 0;cursor:pointer;"
                 onclick="document.getElementById('fileInput').click()">
                <p id="fileName">📸 Cliquez ici pour choisir la capture d'écran</p>
                <input type="file" id="fileInput" name="payment_proof" accept="image/*,.pdf" required style="display:none;"
                       onchange="document.getElementById('fileName').textContent='Fichier sélectionné : '+this.files[0].name">
            </div>

            <button type="submit" class="btn btn-primary" style="width:100%;margin-top:15px;">
                ✅ Confirmer l'envoi de la preuve
            </button>
        </form>
    </div>
    """
    return render_template_string(wrap_page("Paiement", body))


@app.route('/status/<order_id>')
def order_status(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()

    btn_result = ""
    if order.status in ['validated', 'delivered']:
        btn_result = f'<a href="/result/{order.order_id}" class="btn btn-primary" style="margin-top:15px;">📥 Voir mon script MikroTik</a>'

    body = f"""
    <div class="card" style="max-width:500px;margin:40px auto;text-align:center;">
        <h2 style="color:#0066cc;">📦 État de votre commande</h2>
        <p style="margin:10px 0;">Réf : <strong>{order.order_id}</strong></p>
        <div style="font-size:50px;margin:15px 0;">
            {'🟡' if order.status=='pending' else '✅'}
        </div>
        <h3>{order.status_badge}</h3>
        <p style="color:#718096;margin:15px 0;">
            {'Votre paiement est en cours de vérification par un administrateur.' if order.status=='pending' else 'Votre configuration est prête !'}
        </p>
        {btn_result}
    </div>
    """
    return render_template_string(wrap_page("Statut", body))


@app.route('/result/<order_id>')
def result(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()

    if order.status not in ['validated', 'delivered']:
        flash('Commande en attente de validation', 'warning')
        return redirect(url_for('order_status', order_id=order.order_id))

    if not order.script_content:
        order.script_content = generate_full_script(order)
        db.session.commit()

    body = f"""
    <div class="card" style="background:#e6f9ee;border:2px solid #00875a;text-align:center;margin-bottom:25px;">
        <h2 style="color:#00875a;">🎉 Votre Configuration est Prête !</h2>
        <p>Licence Unique : <strong style="font-size:18px;color:#0066cc;">{order.license_key}</strong></p>
    </div>

    <div class="card" style="margin-bottom:20px;">
        <h3 style="color:#00875a;">📋 Méthode 1 : Copier dans WinBox Terminal (Recommandé)</h3>
        <p style="font-size:13px;color:#718096;margin:5px 0 10px;">Ouvrez WinBox → New Terminal → Collez le script ci-dessous. <strong>Aucun redémarrage requis !</strong></p>
        <button class="btn btn-blue" onclick="navigator.clipboard.writeText(document.getElementById('rscCode').innerText);alert('Script copié !');" style="margin-bottom:10px;">
            📋 Copier tout le Script
        </button>
        <pre id="rscCode" style="background:#1e2a3a;color:#a3e635;padding:15px;border-radius:8px;max-height:350px;overflow-y:auto;font-size:12px;">{order.script_content}</pre>
    </div>

    <div class="card">
        <h3 style="color:#0066cc;">📁 Méthode 2 : Télécharger le fichier .rsc</h3>
        <p style="font-size:13px;color:#718096;margin:5px 0 10px;">Téléchargez le fichier et glissez-le dans WinBox (Menu Files), puis tapez <code>/import file-name=ketrika_{order.order_id}.rsc</code></p>
        <a href="/download/{order.order_id}" class="btn btn-primary">📥 Télécharger ketrika_{order.order_id}.rsc</a>
    </div>
    """
    return render_template_string(wrap_page("Configuration", body))


@app.route('/download/<order_id>')
def download(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    if order.status not in ['validated', 'delivered']:
        flash('Accès non autorisé', 'error')
        return redirect(url_for('index'))
    return send_file(
        io.BytesIO(order.script_content.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f'ketrika_{order.order_id}.rsc'
    )


# ============================================
# ESPACE ADMIN
# ============================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username']).first()
        if admin and check_password_hash(admin.password_hash, request.form['password']):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('Identifiants admin incorrects', 'error')
    body = """
    <div class="card" style="max-width:380px;margin:80px auto;">
        <h2 style="color:#00875a;text-align:center;margin-bottom:20px;">🔐 Connexion Admin</h2>
        <form method="POST">
            <label>Utilisateur</label><input name="username" required>
            <label>Mot de passe</label><input name="password" type="password" required>
            <button type="submit" class="btn btn-primary" style="width:100%;margin-top:15px;">Se Connecter</button>
        </form>
    </div>
    """
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
    rows = ""
    for o in orders:
        actions = ""
        if o.status == 'pending':
            actions = f"""
            <form method="POST" action="/admin/validate/{o.id}" style="display:inline;">
                <button style="background:#00875a;color:#fff;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;">✅ Valider</button>
            </form>
            """
        if o.payment_proof:
            actions += f' <a href="/admin/proof/{o.id}" target="_blank" style="text-decoration:none;">📸 Voir preuve</a>'

        rows += f"""<tr>
            <td><strong>{o.order_id}</strong></td>
            <td>{o.client_name}<br><small style="color:#718096;">{o.client_email}</small></td>
            <td>{o.plan_type.upper()}</td>
            <td>{o.plan_price:,} Ar</td>
            <td>{o.status_badge}</td>
            <td>{actions}</td>
        </tr>"""

    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h1 style="color:#00875a;">Tableau de Bord Admin</h1>
        <a href="/admin/logout" class="btn" style="background:#cc3333;color:#fff;padding:8px 15px;font-size:12px;">Déconnexion</a>
    </div>
    <div class="card" style="overflow-x:auto;">
        <table>
            <thead><tr><th>ID</th><th>Client</th><th>Plan</th><th>Prix</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;">Aucune commande</td></tr>'}</tbody>
        </table>
    </div>
    """
    return render_template_string(wrap_page("Admin", body))

@app.route('/admin/validate/<int:order_id>', methods=['POST'])
@login_required
def admin_validate(order_id):
    order = Order.query.get_or_404(order_id)
    order.generate_license_key()
    order.script_content = generate_full_script(order)
    order.status = 'delivered'
    order.validated_at = datetime.utcnow()
    db.session.commit()

    # Tentative envoi email (sans crasher si SMTP non configuré)
    try:
        if app.config['MAIL_USERNAME']:
            msg = Message(f"🔑 Clé KETRIKA - Commande {order.order_id}", recipients=[order.client_email])
            msg.body = f"Bonjour {order.client_name},\nVotre commande est validée !\nClé : {order.license_key}"
            mail.send(msg)
    except Exception as e:
        print(f"Erreur envoi email: {e}")

    flash(f"Commande {order.order_id} validée et générée !", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/proof/<int:order_id>')
@login_required
def admin_proof(order_id):
    order = Order.query.get_or_404(order_id)
    if order.payment_proof and os.path.exists(order.payment_proof):
        return send_file(order.payment_proof)
    flash("Fichier preuve introuvable", "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/faq')
def faq():
    body = """
    <div class="card">
        <h2 style="color:#00875a;margin-bottom:15px;">❓ Foire Aux Questions</h2>
        <p><strong>Comment Starlink détecte le partage ?</strong><br>Starlink surveille le TTL des paquets IP. Notre script normalise le TTL à 65 pour masquer le routeur.</p><br>
        <p><strong>Faut-il redémarrer le MikroTik ?</strong><br>Non, les règles de Firewall et Mangle s'appliquent immédiatement sans coupure ni redémarrage.</p>
    </div>
    """
    return render_template_string(wrap_page("FAQ", body))

@app.route('/conditions')
def conditions():
    body = """
    <div class="card">
        <h2 style="color:#00875a;margin-bottom:15px;">📜 Conditions Générales</h2>
        <p>1 licence générée = 1 routeur MikroTik. Tout script fourni est vérifié pour RouterOS v7.</p>
    </div>
    """
    return render_template_string(wrap_page("Conditions", body))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
