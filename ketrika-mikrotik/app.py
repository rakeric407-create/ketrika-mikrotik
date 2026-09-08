# app.py - KETRIKA MIKROTIK - Thème Clair Complet
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
# 🎨 THÈME CLAIR MODERNE
# ============================================
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
    color: #2c3e50;
    min-height: 100vh;
    line-height: 1.6;
}

/* ===== NAVBAR ===== */
nav {
    background: #ffffff;
    padding: 15px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e1e8ed;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    position: sticky;
    top: 0;
    z-index: 100;
}
nav .logo {
    color: #00875a;
    font-size: 22px;
    font-weight: 700;
    text-decoration: none;
}
nav .logo span { color: #0066cc; }
nav .links a {
    color: #5a6c7d;
    text-decoration: none;
    margin-left: 25px;
    font-size: 14px;
    font-weight: 500;
    transition: color 0.2s;
}
nav .links a:hover { color: #00875a; }

/* ===== CONTAINER ===== */
.container { max-width: 1150px; margin: auto; padding: 30px 20px; }

/* ===== FLASH MESSAGES ===== */
.flash {
    padding: 14px 20px;
    border-radius: 10px;
    margin-bottom: 15px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.flash.success { background: #e6f9ee; border-left: 4px solid #00875a; color: #006644; }
.flash.error { background: #fde8e8; border-left: 4px solid #cc3333; color: #991111; }
.flash.warning { background: #fff8e1; border-left: 4px solid #f0a020; color: #8a5a00; }

/* ===== BOUTONS ===== */
.btn {
    padding: 12px 28px;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    transition: all 0.25s ease;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }

.btn-primary { background: linear-gradient(135deg, #00875a 0%, #00a86b 100%); color: #fff; }
.btn-primary:hover { background: linear-gradient(135deg, #006644 0%, #008554 100%); }

.btn-blue { background: linear-gradient(135deg, #0066cc 0%, #0088ee 100%); color: #fff; }
.btn-blue:hover { background: linear-gradient(135deg, #004c99 0%, #006bbb 100%); }

.btn-orange { background: linear-gradient(135deg, #e65c00 0%, #ff7722 100%); color: #fff; }
.btn-orange:hover { background: linear-gradient(135deg, #cc5200 0%, #dd6611 100%); }

.btn-danger { background: linear-gradient(135deg, #cc3333 0%, #ee5555 100%); color: #fff; }

/* ===== CARTES ===== */
.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 25px;
    border: 1px solid #e1e8ed;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s;
}
.card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }

/* ===== FORMULAIRES ===== */
label {
    display: block;
    margin: 10px 0 5px;
    color: #4a5568;
    font-size: 13px;
    font-weight: 600;
}
input, select, textarea {
    width: 100%;
    padding: 11px 14px;
    border: 1px solid #d1d9e0;
    border-radius: 8px;
    background: #f8fafc;
    color: #2c3e50;
    font-size: 14px;
    margin-bottom: 5px;
    transition: all 0.2s;
    font-family: inherit;
}
input:focus, select:focus, textarea:focus {
    border-color: #00875a;
    background: #fff;
    outline: none;
    box-shadow: 0 0 0 3px rgba(0,135,90,0.12);
}

/* ===== LAYOUT ===== */
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

/* ===== TITRES ===== */
h1 { color: #1a202c; font-weight: 700; }
h2 { color: #2d3748; font-weight: 600; }
h3 { color: #4a5568; font-weight: 600; }

/* ===== TABLE ===== */
table { width: 100%; border-collapse: collapse; }
thead tr { background: #f0f4f8; }
th { padding: 12px; text-align: left; color: #4a5568; font-size: 13px; font-weight: 600; }
td { padding: 12px; border-bottom: 1px solid #edf2f7; font-size: 13px; color: #2d3748; }
tbody tr:hover { background: #f8fafc; }

/* ===== FOOTER ===== */
footer {
    text-align: center;
    padding: 30px;
    color: #718096;
    border-top: 1px solid #e1e8ed;
    margin-top: 50px;
    background: #ffffff;
    font-size: 13px;
}

/* ===== BADGES ===== */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}
.badge-pending { background: #fff8e1; color: #8a5a00; }
.badge-validated { background: #e6f9ee; color: #006644; }
.badge-delivered { background: #e6f2fb; color: #004c99; }
.badge-rejected { background: #fde8e8; color: #991111; }

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: #f0f0f0; }
::-webkit-scrollbar-thumb { background: #b0b8c0; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #909a04; }

/* ===== ANIMATIONS ===== */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.card, .flash { animation: fadeIn 0.3s ease-out; }
"""


def wrap_page(title, body_html, extra_css="", extra_js=""):
    flash_html = """
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for cat, msg in messages %}<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}
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
        <a href="/">Accueil</a>
        <a href="/#plans">Plans</a>
        <a href="/faq">FAQ</a>
        <a href="/conditions">Conditions</a>
        <a href="/admin">Admin</a>
    </div>
</nav>
<div class="container">{flash_html}{body_html}</div>
<footer>© 2024 KETRIKA MIKROTIK - WiFi Zone Solutions | Powered by Starlink 🛰️</footer>
{extra_js}
</body></html>"""


# ============================================
# PAGE ACCUEIL
# ============================================
@app.route('/')
def index():
    plans_html = ""
    for key, p in PLANS.items():
        popular_border = f"border: 2px solid {p['color']}; transform: scale(1.02);" if p.get('popular') else ""
        badge = f'<div style="background:{p["color"]};color:#fff;padding:5px 15px;border-radius:20px;font-size:11px;position:absolute;top:-12px;left:50%;transform:translateX(-50%);font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,0.2);">⭐ POPULAIRE</div>' if p.get('popular') else ''
        features = "".join(f'<li style="padding:8px 0;font-size:14px;color:#4a5568;border-bottom:1px solid #f0f4f8;">✅ {f}</li>' for f in p['features'])
        plans_html += f"""
        <div class="card" style="text-align:center;position:relative;{popular_border}">
            {badge}
            <h3 style="color:{p['color']};font-size:20px;margin-bottom:5px;">{p['name']}</h3>
            <p style="color:#718096;font-size:13px;">{p['subtitle']}</p>
            <div style="font-size:36px;font-weight:700;color:{p['color']};margin:20px 0;">
                {p['price']:,} <small style="font-size:14px;color:#718096;font-weight:400;">{p['currency']}</small>
            </div>
            <ul style="list-style:none;text-align:left;margin:20px 0;">{features}</ul>
            <a href="/configure/{key}" class="btn" style="width:100%;background:{p['color']};color:#fff;margin-top:15px;">Configurer →</a>
        </div>"""

    models_html = "".join(f'<span style="background:#fff;padding:8px 16px;border-radius:20px;font-size:13px;color:#0066cc;border:1px solid #d1d9e0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">{m}</span>' for m in MIKROTIK_MODELS)

    body = f"""
    <!-- HERO -->
    <div style="text-align:center;padding:60px 20px 40px;background:linear-gradient(135deg,#ffffff 0%,#f0f9f4 100%);border-radius:16px;margin-bottom:30px;box-shadow:0 4px 20px rgba(0,0,0,0.05);">
        <h1 style="font-size:48px;color:#00875a;margin-bottom:10px;">🛰️ KETRIKA MIKROTIK</h1>
        <h2 style="color:#0066cc;font-weight:400;font-size:22px;">WiFi Zone Solutions pour Starlink</h2>
        <p style="color:#5a6c7d;font-size:16px;max-width:750px;margin:20px auto;line-height:1.7;">
            Configurez votre routeur MikroTik automatiquement avec protection anti-détection Starlink.
            Scripts RouterOS v7 prêts à l'emploi. <strong style="color:#00875a;">Aucun redémarrage nécessaire !</strong>
        </p>
        <a href="#plans" class="btn btn-primary" style="font-size:18px;padding:15px 45px;margin-top:15px;">⚡ VOIR NOS PLANS</a>
    </div>

    <!-- EFFICACITÉ -->
    <h2 style="text-align:center;color:#2d3748;margin:40px 0 25px;font-size:28px;">🛡️ Notre Efficacité</h2>
    <div class="row" style="margin-bottom:40px;">
        <div class="card" style="text-align:center;">
            <div style="font-size:45px;">🔒</div>
            <h3 style="color:#00875a;margin:10px 0;">Fix TTL</h3>
            <p style="color:#718096;font-size:13px;">TTL fixé à 65 sur tous les paquets. Starlink ne voit plus le routeur.</p>
        </div>
        <div class="card" style="text-align:center;">
            <div style="font-size:45px;">☁️</div>
            <h3 style="color:#0066cc;margin:10px 0;">WARP Tunnel</h3>
            <p style="color:#718096;font-size:13px;">Chiffrement total via Cloudflare WARP. Anti-DPI garanti.</p>
        </div>
        <div class="card" style="text-align:center;">
            <div style="font-size:45px;">🚫</div>
            <h3 style="color:#e65c00;margin:10px 0;">Anti-DPI</h3>
            <p style="color:#718096;font-size:13px;">Block ICMP, Clamp MSS, normalisation des paquets.</p>
        </div>
        <div class="card" style="text-align:center;">
            <div style="font-size:45px;">📶</div>
            <h3 style="color:#00875a;margin:10px 0;">Hotspot Pro</h3>
            <p style="color:#718096;font-size:13px;">Vouchers, PPPoE, limitation bande passante par client.</p>
        </div>
    </div>

    <!-- STATS -->
    <div class="row" style="margin:40px 0;">
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#f0f9f4 0%,#e6f9ee 100%);">
            <div style="font-size:32px;font-weight:700;color:#00875a;">500+</div>
            <div style="color:#718096;font-size:13px;">Routeurs configurés</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#f0f7ff 0%,#e6f2fb 100%);">
            <div style="font-size:32px;font-weight:700;color:#0066cc;">99.8%</div>
            <div style="color:#718096;font-size:13px;">Taux de réussite</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#fff8e1 0%,#fff3c4 100%);">
            <div style="font-size:32px;font-weight:700;color:#e65c00;">0</div>
            <div style="color:#718096;font-size:13px;">Redémarrage requis</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#fce4ec 0%,#f8bbd0 100%);">
            <div style="font-size:32px;font-weight:700;color:#c2185b;">24/7</div>
            <div style="color:#718096;font-size:13px;">Support technique</div>
        </div>
    </div>

    <!-- PLANS -->
    <h2 id="plans" style="text-align:center;color:#2d3748;margin:50px 0 25px;font-size:28px;">📦 Nos Plans</h2>
    <p style="text-align:center;color:#718096;margin-bottom:25px;">Choisissez le plan adapté à vos besoins</p>
    <div class="row">{plans_html}</div>

    <!-- MODÈLES -->
    <h2 style="text-align:center;color:#2d3748;margin:50px 0 15px;font-size:24px;">🖥️ Modèles MikroTik Supportés</h2>
    <p style="text-align:center;color:#718096;margin-bottom:20px;">Détection automatique du nombre de ports • RouterOS v7</p>
    <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;padding:20px 0;">{models_html}</div>
    """
    return render_template_string(wrap_page("Accueil", body))


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

    models_opts = "".join(f'<option value="{m}">{m}</option>' for m in MIKROTIK_MODELS)

    hotspot_extra = ""
    if plan_type == 'hotspot':
        hotspot_extra = """
        <h3 style="color:#0066cc;margin:25px 0 10px;">🌐 Options Hotspot</h3>
        <div class="row">
            <div><label>Nom Hotspot</label><input name="hotspot_name" value="WiFiZone"></div>
        </div>
        <div class="check"><input type="checkbox" name="pppoe" id="pppoe"><label for="pppoe" style="margin:0;">Activer serveur PPPoE</label></div>
        <div class="check"><input type="checkbox" name="voucher" id="voucher" checked><label for="voucher" style="margin:0;">Générer 10 vouchers pré-configurés</label></div>
        """

    body = f"""
    <div class="card">
        <div style="text-align:center;margin-bottom:30px;padding-bottom:20px;border-bottom:3px solid {plan['color']};">
            <h1 style="color:{plan['color']};font-size:28px;">⚙️ {plan['name']}</h1>
            <p style="color:#718096;margin-top:5px;">{plan['subtitle']} — <strong>{plan['price']:,} {plan['currency']}</strong></p>
        </div>

        <form method="POST">
            <h3 style="color:#0066cc;margin-bottom:10px;">👤 Vos Informations</h3>
            <div class="row">
                <div><label>Nom complet *</label><input name="client_name" required placeholder="Ex: Jean Rakoto"></div>
                <div><label>Email *</label><input name="client_email" type="email" required placeholder="jean@gmail.com"></div>
                <div><label>Téléphone</label><input name="client_phone" placeholder="+261 34 00 000 00"></div>
            </div>

            <h3 style="color:#0066cc;margin:25px 0 10px;">🖥️ Votre Routeur MikroTik</h3>
            <div class="row">
                <div>
                    <label>Modèle *</label>
                    <select name="mikrotik_model" id="modelSelect" required>
                        <option value="">-- Choisir votre modèle --</option>{models_opts}
                    </select>
                </div>
            </div>

            <div id="portPreview" style="background:#e6f9ee;border:1px solid #00875a;border-radius:10px;padding:18px;margin:15px 0;display:none;">
                <h4 style="color:#00875a;margin-bottom:10px;">📍 Ports détectés automatiquement :</h4>
                <div id="portVisual" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;"></div>
                <p id="portInfo" style="color:#4a5568;margin-top:10px;font-size:13px;"></p>
            </div>

            <h3 style="color:#0066cc;margin:25px 0 10px;">🌐 Configuration Réseau</h3>
            <div class="row">
                <div>
                    <label>Interface WAN (Starlink)</label>
                    <select name="wan_interface">
                        <option value="ether1">ether1 (recommandé)</option>
                        <option value="sfp1">sfp1</option>
                    </select>
                </div>
                <div><label>Réseau LAN</label><input name="lan_network" value="192.168.88.0/24"></div>
                <div><label>IP Gateway</label><input name="lan_gateway" value="192.168.88.1"></div>
            </div>
            <div class="row">
                <div><label>Pool DHCP</label><input name="dhcp_pool" value="192.168.88.10-192.168.88.250"></div>
                <div><label>Nom WiFi (SSID)</label><input name="ssid" value="WiFiZone-Ketrika"></div>
                <div><label>Mot de passe WiFi</label><input name="wifi_password" value="Ketrika2024"></div>
            </div>

            <h3 style="color:#0066cc;margin:25px 0 10px;">🛡️ Anti-Détection Starlink</h3>
            <div class="row">
                <div>
                    <label>Valeur TTL</label>
                    <select name="ttl_value">
                        <option value="64">64 (Linux/Android)</option>
                        <option value="65" selected>65 ⭐ Recommandé</option>
                        <option value="128">128 (Windows)</option>
                    </select>
                </div>
                <div>
                    <label>Download max / client</label>
                    <select name="dl_limit">
                        <option value="5M">5 Mbps</option>
                        <option value="10M" selected>10 Mbps</option>
                        <option value="20M">20 Mbps</option>
                        <option value="50M">50 Mbps</option>
                        <option value="100M">100 Mbps</option>
                    </select>
                </div>
                <div>
                    <label>Upload max / client</label>
                    <select name="ul_limit">
                        <option value="2M">2 Mbps</option>
                        <option value="5M" selected>5 Mbps</option>
                        <option value="10M">10 Mbps</option>
                        <option value="20M">20 Mbps</option>
                    </select>
                </div>
            </div>

            {hotspot_extra}

            <button type="submit" class="btn btn-primary" style="width:100%;padding:18px;font-size:17px;margin-top:30px;">
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
            var info=document.getElementById('portInfo');
            pv.style.display='block'; vis.innerHTML='';
            vis.innerHTML+='<span style="background:#cc3333;color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;">ether1 (WAN)</span>';
            for(var i=2;i<=d.ports;i++) vis.innerHTML+='<span style="background:#0066cc;color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;">ether'+i+' (LAN)</span>';
            if(d.wifi) vis.innerHTML+='<span style="background:#00875a;color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;">wlan1 (2.4G)</span>';
            if(d.wifi5g) vis.innerHTML+='<span style="background:#00a86b;color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;">wlan2 (5G)</span>';
            var t=d.ports+' ports Ethernet';
            if(d.wifi) t+=' • WiFi 2.4 GHz';
            if(d.wifi5g) t+=' • WiFi 5 GHz';
            if(d.poe) t+=' • PoE';
            info.textContent=t;
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
            flash('✅ Preuve envoyée avec succès ! En attente de validation.', 'success')
            return redirect(url_for('order_status', order_id=order.order_id))
        flash('Veuillez envoyer une preuve de paiement', 'error')

    body = f"""
    <div class="card" style="max-width:650px;margin:auto;">
        <h1 style="text-align:center;color:#00875a;">💳 Paiement Sécurisé</h1>
        <p style="text-align:center;color:#718096;margin-top:5px;">Commande: <strong>{order.order_id}</strong></p>

        <div style="text-align:center;margin:25px 0;padding:25px;background:linear-gradient(135deg,#f0f9f4 0%,#e6f9ee 100%);border-radius:12px;">
            <div style="font-size:42px;color:#00875a;font-weight:700;">{plan['price']:,} {plan['currency']}</div>
            <p style="color:#718096;margin-top:5px;">{plan['name']}</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <h3 style="color:#0066cc;margin-bottom:15px;">1️⃣ Choisir le mode de paiement</h3>
            <div class="row" style="margin:15px 0;">
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:18px;margin:0;">
                    <input type="radio" name="payment_method" value="mvola" checked style="width:auto;margin-bottom:8px;">
                    <div style="font-size:28px;">📱</div>
                    <strong style="color:#00875a;">MVola</strong>
                </label>
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:18px;margin:0;">
                    <input type="radio" name="payment_method" value="orange" style="width:auto;margin-bottom:8px;">
                    <div style="font-size:28px;">🟠</div>
                    <strong style="color:#e65c00;">Orange Money</strong>
                </label>
                <label class="card" style="flex:1;text-align:center;cursor:pointer;padding:18px;margin:0;">
                    <input type="radio" name="payment_method" value="airtel" style="width:auto;margin-bottom:8px;">
                    <div style="font-size:28px;">🔴</div>
                    <strong style="color:#cc3333;">Airtel Money</strong>
                </label>
            </div>

            <div style="background:#fff8e1;border-left:4px solid #f0a020;padding:20px;border-radius:8px;margin:20px 0;">
                <h4 style="color:#8a5a00;margin-bottom:10px;">📝 Instructions :</h4>
                <p style="color:#4a5568;margin-bottom:5px;">Envoyez <strong style="color:#00875a;">{plan['price']:,} Ar</strong> au numéro :</p>
                <p style="font-size:26px;color:#00875a;font-weight:700;margin:10px 0;">034 00 000 00</p>
                <p style="color:#718096;font-size:13px;">Nom: KETRIKA MIKROTIK</p>
                <p style="color:#718096;font-size:13px;">Référence à indiquer: <strong>{order.order_id}</strong></p>
            </div>

            <h3 style="color:#0066cc;margin:25px 0 10px;">2️⃣ Envoyer la preuve de paiement</h3>
            <div style="border:2px dashed #00875a;border-radius:12px;padding:35px;text-align:center;margin:15px 0;cursor:pointer;background:#f8fafc;transition:all 0.2s;"
                 onmouseover="this.style.background='#f0f9f4'"
                 onmouseout="this.style.background='#f8fafc'"
                 onclick="document.getElementById('fileInput').click()">
                <div style="font-size:50px;">📸</div>
                <p id="fileName" style="color:#4a5568;margin-top:10px;font-weight:600;">Cliquez pour envoyer une capture d'écran</p>
                <p style="color:#a0aec0;font-size:12px;">JPG, PNG ou PDF — Max 5 MB</p>
                <input type="file" id="fileInput" name="payment_proof" accept="image/*,.pdf" required style="display:none;"
                       onchange="document.getElementById('fileName').textContent='✅ '+this.files[0].name;document.getElementById('fileName').style.color='#00875a'">
            </div>

            <button type="submit" class="btn btn-primary" style="width:100%;padding:16px;font-size:16px;margin-top:15px;">
                ✅ Envoyer la preuve de paiement
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
    color = {'pending': '#f0a020', 'validated': '#00875a', 'delivered': '#0066cc', 'rejected': '#cc3333'}.get(order.status, '#718096')

    action_btn = ""
    msg_status = ""
    if order.status == 'pending':
        msg_status = f'Votre paiement est en cours de vérification.<br>Vous recevrez un email à <strong>{order.client_email}</strong> dès validation.'
    elif order.status in ['validated', 'delivered']:
        msg_status = '🎉 Votre configuration est prête !'
        action_btn = f'<a href="/result/{order.order_id}" class="btn btn-primary" style="margin-top:20px;">📥 Voir ma configuration</a>'
    elif order.status == 'rejected':
        msg_status = 'Votre commande a été rejetée. Contactez le support.'

    body = f"""
    <div class="card" style="max-width:550px;margin:40px auto;text-align:center;">
        <h1 style="color:#0066cc;">📦 Suivi de Commande</h1>
        <p style="font-size:18px;margin:15px 0;color:#4a5568;">Commande <strong>{order.order_id}</strong></p>

        <div style="font-size:70px;margin:25px 0;">{icon}</div>
        <h2 style="color:{color};font-size:24px;">{order.status_badge}</h2>

        <p style="color:#718096;margin-top:20px;line-height:1.6;">{msg_status}</p>

        {action_btn}

        <div style="text-align:left;margin-top:30px;padding-top:20px;border-top:1px solid #e1e8ed;">
            <p style="color:#4a5568;margin:8px 0;"><strong>Plan:</strong> {order.plan_type.upper()}</p>
            <p style="color:#4a5568;margin:8px 0;"><strong>Modèle:</strong> {order.mikrotik_model}</p>
            <p style="color:#4a5568;margin:8px 0;"><strong>Date:</strong> {order.created_at.strftime('%d/%m/%Y à %H:%M')}</p>
            <p style="color:#4a5568;margin:8px 0;"><strong>Montant:</strong> {order.plan_price:,} Ar</p>
        </div>
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
    <div style="text-align:center;padding:30px;background:linear-gradient(135deg,#f0f9f4 0%,#e6f9ee 100%);border:2px solid #00875a;border-radius:16px;margin-bottom:25px;">
        <div style="font-size:60px;">✅</div>
        <h1 style="color:#00875a;font-size:32px;">Configuration Prête !</h1>
        <p style="color:#718096;margin-top:5px;">Commande {order.order_id}</p>
        <div style="font-size:26px;letter-spacing:4px;color:#00875a;background:#fff;padding:15px 25px;border-radius:10px;display:inline-block;margin:20px 0;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
            {order.license_key}
        </div>
        <p style="color:#4a5568;">Conservez précieusement cette clé de licence</p>
    </div>

    <h2 style="text-align:center;color:#2d3748;margin:30px 0 15px;">📥 3 Méthodes pour appliquer votre configuration</h2>
    <p style="text-align:center;color:#718096;margin-bottom:25px;">⚠️ <strong>Aucun redémarrage nécessaire !</strong></p>

    <!-- MÉTHODE 1 -->
    <div class="card" style="border-left:5px solid #00875a;margin:15px 0;">
        <h3 style="color:#00875a;">📋 Méthode 1 — Terminal WinBox (recommandé)</h3>
        <p style="color:#718096;margin:10px 0;">La méthode la plus simple et la plus rapide</p>
        <ol style="color:#4a5568;margin:15px 0 15px 20px;line-height:2;">
            <li>Ouvrez <strong>WinBox</strong> et connectez-vous</li>
            <li>Menu <strong>New Terminal</strong> (icône terminal en haut)</li>
            <li>Cliquez le bouton ci-dessous pour copier le script</li>
            <li>Dans le terminal : <strong>Clic droit → Paste</strong></li>
            <li>Attendez 30 secondes ⏱️ ✅</li>
        </ol>
        <button class="btn btn-blue" onclick="copyScript()" style="margin:10px 0;">📋 Copier tout le script</button>
        <pre id="scriptBox" style="background:#1e2a3a;color:#a3e635;border-radius:8px;padding:20px;max-height:400px;overflow-y:auto;font-size:12px;line-height:1.6;white-space:pre-wrap;font-family:'Consolas',monospace;margin-top:10px;">{order.script_content}</pre>
    </div>

    <!-- MÉTHODE 2 -->
    <div class="card" style="border-left:5px solid #0066cc;margin:15px 0;">
        <h3 style="color:#0066cc;">📁 Méthode 2 — Upload fichier .rsc</h3>
        <p style="color:#718096;margin:10px 0;">Idéale si le copier/coller pose problème</p>
        <ol style="color:#4a5568;margin:15px 0 15px 20px;line-height:2;">
            <li>Téléchargez le fichier : <a href="/download/{order.order_id}" class="btn btn-blue" style="padding:6px 15px;font-size:13px;margin-left:10px;">📥 Télécharger .rsc</a></li>
            <li>Ouvrez <strong>WinBox → Files</strong> (menu de gauche)</li>
            <li><strong>Glissez-déposez</strong> le fichier dans la fenêtre Files</li>
            <li>New Terminal → Tapez :</li>
        </ol>
        <code style="background:#1e2a3a;color:#38bdf8;padding:12px 18px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin-top:10px;">
            /import file-name=ketrika_{order.order_id}.rsc
        </code>
    </div>

    <!-- MÉTHODE 3 -->
    <div class="card" style="border-left:5px solid #e65c00;margin:15px 0;">
        <h3 style="color:#e65c00;">💻 Méthode 3 — Via SSH (avancé)</h3>
        <p style="color:#718096;margin:10px 0;">Pour utilisateurs expérimentés</p>
        <ol style="color:#4a5568;margin:15px 0 15px 20px;line-height:2;">
            <li>Ouvrez un terminal (CMD/PowerShell/Terminal Mac-Linux)</li>
            <li>Connectez-vous :</li>
        </ol>
        <code style="background:#1e2a3a;color:#fb923c;padding:12px 18px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;">
            ssh admin@{order.lan_gateway}
        </code>
        <p style="color:#4a5568;margin-top:15px;">Puis transférez et importez le fichier :</p>
        <code style="background:#1e2a3a;color:#fb923c;padding:12px 18px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;">
            scp ketrika_{order.order_id}.rsc admin@{order.lan_gateway}:/
        </code>
        <code style="background:#1e2a3a;color:#fb923c;padding:12px 18px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;">
            /import file-name=ketrika_{order.order_id}.rsc
        </code>
    </div>

    <!-- VÉRIFICATION -->
    <div class="card" style="border:2px solid #00875a;margin-top:25px;background:#f0f9f4;">
        <h3 style="color:#00875a;">🔍 Vérification après installation</h3>
        <p style="color:#4a5568;margin:10px 0;">Tapez ces commandes dans le terminal MikroTik :</p>
        <code style="background:#1e2a3a;color:#a3e635;padding:10px 15px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;font-size:13px;">/ip firewall mangle print where comment~"KETRIKA"</code>
        <code style="background:#1e2a3a;color:#a3e635;padding:10px 15px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;font-size:13px;">/tool traceroute 1.1.1.1</code>
        <code style="background:#1e2a3a;color:#a3e635;padding:10px 15px;border-radius:6px;display:block;font-family:'Consolas',monospace;margin:5px 0;font-size:13px;">/ping 1.1.1.1 count=3</code>
        <p style="color:#00875a;margin-top:15px;font-weight:600;">✅ Le TTL doit afficher <strong>{order.ttl_value}</strong> partout</p>
    </div>
    """

    extra_js = """<script>
    function copyScript(){
        var t=document.getElementById('scriptBox').textContent;
        navigator.clipboard.writeText(t).then(function(){
            var b=event.target;
            b.textContent='✅ Script copié !';
            b.style.background='linear-gradient(135deg,#00875a 0%,#00a86b 100%)';
            setTimeout(function(){
                b.textContent='📋 Copier tout le script';
                b.style.background='linear-gradient(135deg,#0066cc 0%,#0088ee 100%)';
            },3000);
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
    <div style="max-width:400px;margin:80px auto;">
        <div class="card">
            <h2 style="text-align:center;color:#00875a;margin-bottom:25px;">🔐 Espace Admin</h2>
            <form method="POST">
                <label>Nom d'utilisateur</label><input name="username" required autofocus>
                <label>Mot de passe</label><input name="password" type="password" required>
                <button type="submit" class="btn btn-primary" style="width:100%;margin-top:20px;">Connexion</button>
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
    total = Order.query.count()
    revenue = db.session.query(db.func.sum(Order.plan_price)).filter(
        Order.status.in_(['validated','delivered'])).scalar() or 0

    rows = ""
    for o in orders:
        badge_class = f'badge-{o.status}'
        actions = ""
        if o.status == 'pending' and o.payment_proof:
            actions += f"""
            <form method="POST" action="/admin/validate/{o.id}" style="display:inline;">
                <button name="action" value="validate" style="background:#00875a;color:#fff;padding:5px 12px;border:none;border-radius:5px;font-size:11px;cursor:pointer;font-weight:600;">✅ Valider</button>
            </form>
            <form method="POST" action="/admin/validate/{o.id}" style="display:inline;">
                <button name="action" value="reject" style="background:#cc3333;color:#fff;padding:5px 10px;border:none;border-radius:5px;font-size:11px;cursor:pointer;">❌</button>
            </form>"""
        if o.payment_proof:
            actions += f' <a href="/admin/proof/{o.id}" target="_blank" style="background:#0066cc;color:#fff;padding:5px 10px;border-radius:5px;font-size:11px;text-decoration:none;">📸</a>'
        if o.license_key:
            actions += f'<br><small style="color:#00875a;font-size:10px;margin-top:5px;display:inline-block;">🔑 {o.license_key}</small>'

        rows += f"""<tr>
            <td><strong>{o.order_id}</strong></td>
            <td>{o.created_at.strftime('%d/%m %H:%M')}</td>
            <td>{o.client_name}<br><small style="color:#718096">{o.client_email}</small></td>
            <td>{o.plan_type.upper()}</td>
            <td style="font-size:11px;">{o.mikrotik_model}</td>
            <td>{o.plan_price:,} Ar</td>
            <td><span class="badge {badge_class}">{o.status_badge}</span></td>
            <td>{actions}</td>
        </tr>"""

    body = f"""
    <h1 style="color:#00875a;">🔐 Tableau de Bord Admin</h1>
    <p style="color:#718096;margin-bottom:20px;">Bienvenue <strong>{current_user.username}</strong> | <a href="/admin/logout" style="color:#cc3333;">Déconnexion</a></p>

    <div class="row" style="margin:20px 0;">
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#f0f7ff 0%,#e6f2fb 100%);">
            <div style="font-size:32px;font-weight:700;color:#0066cc;">{total}</div>
            <div style="color:#718096;font-size:13px;">Total commandes</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#fff8e1 0%,#fff3c4 100%);">
            <div style="font-size:32px;font-weight:700;color:#f0a020;">{pending}</div>
            <div style="color:#718096;font-size:13px;">En attente</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#f0f9f4 0%,#e6f9ee 100%);">
            <div style="font-size:32px;font-weight:700;color:#00875a;">{delivered}</div>
            <div style="color:#718096;font-size:13px;">Livrées</div>
        </div>
        <div class="card" style="text-align:center;background:linear-gradient(135deg,#fce4ec 0%,#f8bbd0 100%);">
            <div style="font-size:28px;font-weight:700;color:#c2185b;">{revenue:,} Ar</div>
            <div style="color:#718096;font-size:13px;">Revenus totaux</div>
        </div>
    </div>

    <div class="card" style="overflow-x:auto;">
        <h2 style="color:#0066cc;margin-bottom:15px;">📋 Toutes les commandes</h2>
        <table>
            <thead><tr>
                <th>ID</th><th>Date</th><th>Client</th><th>Plan</th>
                <th>Modèle</th><th>Prix</th><th>Statut</th><th>Actions</th>
            </tr></thead>
            <tbody>{rows if rows else '<tr><td colspan="8" style="text-align:center;color:#718096;padding:30px;">Aucune commande pour l\\'instant</td></tr>'}</tbody>
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

        try:
            msg = Message(
                subject=f"🔑 Votre Clé KETRIKA - {order.order_id}",
                recipients=[order.client_email]
            )
            msg.html = f"""
            <div style="font-family:Arial;max-width:600px;margin:auto;background:#ffffff;padding:30px;border-radius:12px;border:1px solid #e1e8ed;">
                <h1 style="color:#00875a;text-align:center;">🛰️ KETRIKA MIKROTIK</h1>
                <p style="color:#4a5568;">Bonjour <strong>{order.client_name}</strong>,</p>
                <p style="color:#4a5568;">Votre paiement a été validé avec succès ! 🎉</p>
                <div style="background:#f0f9f4;padding:25px;border-radius:10px;text-align:center;margin:25px 0;border:1px solid #00875a;">
                    <p style="color:#718096;margin-bottom:10px;">Votre Clé de Licence</p>
                    <h2 style="color:#00875a;letter-spacing:3px;">{order.license_key}</h2>
                </div>
                <p style="text-align:center;">👉 <a href="https://VOTRE-DOMAINE/result/{order.order_id}" style="background:#00875a;color:#fff;padding:12px 25px;text-decoration:none;border-radius:6px;display:inline-block;">📥 Voir ma configuration</a></p>
                <p style="color:#718096;font-size:12px;text-align:center;margin-top:30px;">© 2024 KETRIKA MIKROTIK</p>
            </div>"""
            mail.send(msg)
            order.status = 'delivered'
            order.delivered_at = datetime.utcnow()
            db.session.commit()
            flash(f'✅ {order.order_id} validé + email envoyé', 'success')
        except Exception as e:
            flash(f'⚠️ Validé mais email échoué. Clé: {order.license_key}', 'warning')

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
# FAQ
# ============================================
@app.route('/faq')
def faq():
    faqs = [
        ("Comment Starlink détecte le partage de connexion ?",
         "Starlink analyse le <strong>TTL</strong> (Time To Live) des paquets. Quand un routeur est présent, le TTL diminue d'1. Notre script fixe le TTL à 65 pour masquer le routeur."),
        ("Faut-il redémarrer le routeur après configuration ?",
         "<strong>NON !</strong> Les 3 méthodes (Terminal, Upload .rsc, SSH) s'appliquent instantanément sans redémarrage. La configuration prend effet immédiatement."),
        ("Quelle version de RouterOS est supportée ?",
         "Nos scripts sont compatibles <strong>RouterOS v7</strong> (7.x et supérieur). Contactez-nous pour v6."),
        ("Qu'est-ce que le plan WARP ?",
         "Le plan WARP utilise un tunnel <strong>WireGuard vers Cloudflare WARP</strong> pour chiffrer tout le trafic. Starlink ne peut plus analyser vos paquets (DPI)."),
        ("En combien de temps je reçois ma configuration ?",
         "Après validation de votre paiement (1 à 24 heures), vous recevez automatiquement votre clé et le script par email."),
        ("Puis-je utiliser la clé sur plusieurs routeurs ?",
         "Non, chaque clé est valable pour un seul routeur. Pour plusieurs routeurs, contactez-nous pour une offre volume."),
    ]

    items = ""
    for q, a in faqs:
        items += f"""
        <div class="card" style="margin:12px 0;cursor:pointer;transition:all 0.2s;"
             onclick="var a=this.querySelector('.a');a.style.display=a.style.display==='block'?'none':'block';this.querySelector('.arrow').textContent=a.style.display==='block'?'▼':'▶'">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <strong style="color:#2d3748;">{q}</strong>
                <span class="arrow" style="color:#00875a;">▶</span>
            </div>
            <div class="a" style="display:none;color:#4a5568;margin-top:12px;padding-top:12px;border-top:1px solid #e1e8ed;">{a}</div>
        </div>"""

    body = f"""
    <h1 style="text-align:center;color:#00875a;margin-bottom:30px;">❓ Questions Fréquentes</h1>
    <p style="text-align:center;color:#718096;margin-bottom:25px;">Cliquez sur une question pour voir la réponse</p>
    {items}
    """
    return render_template_string(wrap_page("FAQ", body))


# ============================================
# CONDITIONS
# ============================================
@app.route('/conditions')
def conditions():
    body = """
    <h1 style="text-align:center;color:#00875a;margin-bottom:30px;">📜 Conditions d'Utilisation</h1>
    <div class="card">
        <h3 style="color:#0066cc;">1. Service</h3>
        <p style="color:#4a5568;margin:10px 0;">KETRIKA MIKROTIK fournit des scripts de configuration pour routeurs MikroTik RouterOS v7.
        Nos scripts sont conçus pour optimiser la connexion avec le FAI Starlink et éviter la détection de partage.</p>

        <h3 style="color:#0066cc;margin-top:20px;">2. Licence</h3>
        <p style="color:#4a5568;margin:10px 0;">Chaque clé de licence est valable pour <strong>un seul routeur</strong>.
        La revente, le partage ou la duplication de licence sont strictement interdits.</p>

        <h3 style="color:#0066cc;margin-top:20px;">3. Responsabilité</h3>
        <p style="color:#4a5568;margin:10px 0;">L'utilisateur est seul responsable de l'utilisation des scripts sur son propre réseau.
        KETRIKA MIKROTIK n'est pas responsable des modifications apportées à votre routeur ou des conséquences avec votre FAI.</p>

        <h3 style="color:#0066cc;margin-top:20px;">4. Paiement</h3>
        <p style="color:#4a5568;margin:10px 0;">Le paiement est requis avant la livraison du script.
        Une fois validé et le script généré, <strong>aucun remboursement</strong> n'est possible (produit numérique).</p>

        <h3 style="color:#0066cc;margin-top:20px;">5. Support</h3>
        <p style="color:#4a5568;margin:10px 0;">Un support technique par email est inclus pendant <strong>30 jours</strong> après l'achat.
        Contact : support@ketrika-mikrotik.mg</p>

        <h3 style="color:#0066cc;margin-top:20px;">6. Protection des données</h3>
        <p style="color:#4a5568;margin:10px 0;">Vos données personnelles (nom, email, téléphone) sont utilisées uniquement pour le traitement de votre commande
        et ne sont jamais partagées avec des tiers.</p>
    </div>
    """
    return render_template_string(wrap_page("Conditions", body))


# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
