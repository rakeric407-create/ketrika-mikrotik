# app.py - KETRIKA MIKROTIK - Plateforme SaaS Professionnelle
import os
import io
import secrets
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
app.secret_key = os.environ.get('SECRET_KEY', 'ketrika-pro-key-2024')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///ketrika.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_SENDER', app.config['MAIL_USERNAME'])

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(uid):
    return Admin.query.get(int(uid))

with app.app_context():
    try:
        db.create_all()
        admin_u = os.environ.get('ADMIN_USER', 'admin')
        admin_p = os.environ.get('ADMIN_PASS', 'KetrikaAdmin2024!')
        if not Admin.query.filter_by(username=admin_u).first():
            db.session.add(Admin(username=admin_u, password_hash=generate_password_hash(admin_p)))
            db.session.commit()
    except Exception as e:
        print(f"DB Error: {e}")

def wrap(title, body_content, extra_js=""):
    flashes = """
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        <div class="max-w-4xl mx-auto mt-4 px-4">
            {% for cat, msg in messages %}
                <div class="p-4 rounded-xl mb-3 flex items-center gap-3 text-sm {% if cat=='success' %}bg-emerald-50 text-emerald-800 border-l-4 border-emerald-500{% elif cat=='error' %}bg-rose-50 text-rose-800 border-l-4 border-rose-500{% else %}bg-amber-50 text-amber-800 border-l-4 border-amber-500{% endif %}">
                    <span class="text-lg">{% if cat=='success' %}✅{% elif cat=='error' %}❌{% else %}⚠️{% endif %}</span>
                    <p class="font-semibold">{{ msg }}</p>
                </div>
            {% endfor %}
        </div>
    {% endif %}
    {% endwith %}
    """
    return f"""<!DOCTYPE html>
<html lang="fr" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - KETRIKA MIKROTIK</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col antialiased">
    <nav class="bg-white/90 backdrop-blur-md sticky top-0 z-50 border-b border-slate-100 shadow-sm">
        <div class="max-w-5xl mx-auto px-4 h-16 flex justify-between items-center">
            <a href="/" class="flex items-center gap-2 text-xl font-extrabold text-emerald-600 tracking-tight">
                🛰️ KETRIKA <span class="text-sky-600 font-medium text-lg">MIKROTIK</span>
            </a>
            <div class="hidden md:flex items-center gap-6">
                <a href="/" class="text-sm font-semibold text-slate-600 hover:text-emerald-600 transition">Accueil</a>
                <a href="/pourquoi-nous" class="text-sm font-semibold text-slate-600 hover:text-emerald-600 transition">⭐ Pourquoi Nous</a>
                <a href="/track" class="text-sm font-semibold text-slate-600 hover:text-emerald-600 transition">🔍 Suivi Commande</a>
                <a href="/faq" class="text-sm font-semibold text-slate-600 hover:text-emerald-600 transition">FAQ</a>
                <a href="/admin" class="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700 transition">Espace Admin</a>
            </div>
        </div>
    </nav>
    <main class="flex-grow py-8">
        {flashes}
        <div class="max-w-4xl mx-auto px-4">{body_content}</div>
    </main>
    <footer class="bg-white border-t border-slate-100 py-10 mt-16 text-center text-xs text-slate-400">
        <p class="font-bold text-slate-700 text-sm">🛰️ KETRIKA MIKROTIK - Solutions Professionnelles RouterOS v7</p>
        <p class="mt-1">Optimisation réseau & stabilité multi-clients pour opérateurs WiFi Zone</p>
    </footer>
    {extra_js}
</body>
</html>"""

@app.route('/')
def index():
    plans_html = ""
    for key, p in PLANS.items():
        border_cls = "ring-2 ring-emerald-500 shadow-xl relative scale-[1.02] md:scale-105" if p.get('popular') else "border border-slate-100 shadow-md"
        badge = '<div class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-white px-4 py-1 rounded-full text-[10px] font-bold tracking-wider shadow">⭐ RECOMMANDÉ</div>' if p.get('popular') else ''
        features = "".join(f'<li class="py-2.5 text-xs text-slate-600 border-b border-slate-50 flex items-start gap-2">✅ <span class="flex-1">{f}</span></li>' for f in p['features'])
        plans_html += f"""
        <div class="bg-white rounded-2xl p-6 flex flex-col justify-between {border_cls}">
            {badge}
            <div class="text-center">
                <h3 class="text-lg font-bold" style="color:{p['color']}">{p['name']}</h3>
                <p class="text-xs text-slate-400 mt-1">{p['subtitle']}</p>
                <div class="my-6">
                    <span class="text-3xl font-extrabold" style="color:{p['color']}">{p['price']:,}</span>
                    <span class="text-xs text-slate-400 font-bold ml-1">{p['currency']}</span>
                </div>
            </div>
            <ul class="space-y-1 mb-8">{features}</ul>
            <a href="/configure/{key}" class="w-full text-center py-3 rounded-xl text-xs font-bold text-white transition hover:-translate-y-0.5" style="background:{p['color']}">Configurer & Commander →</a>
        </div>"""

    models_html = "".join(f'<span class="bg-white border border-slate-200 text-sky-600 text-[11px] font-semibold px-3 py-1.5 rounded-full shadow-sm">{m}</span>' for m in MIKROTIK_MODELS)

    body = f"""
    <div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-sm text-center mb-12">
        <span class="bg-emerald-50 text-emerald-700 text-xs font-bold px-3 py-1.5 rounded-full uppercase tracking-wider">Solution SaaS Professionnelle</span>
        <h1 class="text-3xl md:text-4xl font-extrabold text-slate-900 mt-4 leading-tight">Optimisation Réseau Multi-Clients</h1>
        <p class="text-slate-500 text-sm max-w-xl mx-auto mt-3">Configuration MikroTik RouterOS v7 automatisée pour opérateurs WiFi Zone. <strong>Débit stable, aucune coupure, installation en 30 secondes.</strong></p>
        <div class="mt-6 flex flex-wrap justify-center gap-4">
            <a href="#plans" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-xl text-xs font-bold shadow-md transition">🚀 Découvrir nos Packs</a>
            <a href="/track" class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-6 py-3 rounded-xl text-xs font-bold transition">🔍 Récupérer ma Configuration</a>
        </div>
    </div>
    
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm text-center">
            <div class="text-2xl font-extrabold text-emerald-600">500+</div>
            <p class="text-xs font-semibold text-slate-400 mt-1">Opérateurs actifs</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm text-center">
            <div class="text-2xl font-extrabold text-sky-600">99.9%</div>
            <p class="text-xs font-semibold text-slate-400 mt-1">Stabilité connexion</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm text-center">
            <div class="text-2xl font-extrabold text-amber-500">&lt; 30s</div>
            <p class="text-xs font-semibold text-slate-400 mt-1">Installation rapide</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm text-center">
            <div class="text-2xl font-extrabold text-rose-500">∞</div>
            <p class="text-xs font-semibold text-slate-400 mt-1">Débit illimité (Premium)</p>
        </div>
    </div>
    
    <h2 id="plans" class="text-xl font-extrabold text-slate-900 text-center mb-8">📦 Nos Packs Professionnels</h2>
    <div class="grid md:grid-cols-3 gap-6 mb-12">{plans_html}</div>
    <div class="bg-slate-100/60 rounded-3xl p-8 border border-slate-200/50 text-center">
        <h3 class="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">🖥️ Matériels compatibles avec détection automatique</h3>
        <div class="flex flex-wrap justify-center gap-2">{models_html}</div>
    </div>"""
    return render_template_string(wrap("Accueil", body))

@app.route('/pourquoi-nous')
def pourquoi_nous():
    body = """
    <div class="bg-gradient-to-br from-emerald-600 to-sky-600 rounded-3xl p-8 text-white text-center mb-10 shadow-lg">
        <h1 class="text-3xl font-extrabold leading-tight">Pourquoi choisir KETRIKA ?</h1>
        <p class="text-emerald-50 text-sm mt-2 max-w-xl mx-auto">La référence à Madagascar pour l'optimisation MikroTik multi-clients avec Cloudflare Secure Tunnel.</p>
    </div>
    
    <div class="grid md:grid-cols-3 gap-6 mb-10">
        <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <div class="text-3xl mb-3">⚡</div>
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">Configuration Sans Erreur</h3>
            <p class="text-xs text-slate-500 leading-relaxed">Notre système génère un script personnalisé garanti sans conflit, testé sur des centaines de routeurs MikroTik.</p>
        </div>
        <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <div class="text-3xl mb-3">☁️</div>
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">Cloudflare Secure Tunnel</h3>
            <p class="text-xs text-slate-500 leading-relaxed">Débit <strong>illimité et stable</strong> via l'infrastructure Cloudflare mondiale. Chiffrement AES-256, aucune perte de vitesse.</p>
        </div>
        <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <div class="text-3xl mb-3">🔒</div>
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">Zéro Déconnexion</h3>
            <p class="text-xs text-slate-500 leading-relaxed">L'assignation asynchrone des ports élimine tout risque de coupure lors du copier-coller dans WinBox.</p>
        </div>
    </div>
    
    <div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-sm mb-8">
        <h2 class="text-lg font-bold text-slate-900 mb-4">🚀 Avantages du Cloudflare Secure Tunnel</h2>
        <ul class="space-y-3 text-sm">
            <li class="flex gap-3"><span class="text-emerald-500 font-bold text-lg">✓</span><div><strong class="text-slate-800">Débit illimité stable :</strong> <span class="text-slate-500">Aucun bridage, la bande passante Starlink est préservée intégralement.</span></div></li>
            <li class="flex gap-3"><span class="text-emerald-500 font-bold text-lg">✓</span><div><strong class="text-slate-800">Faible latence :</strong> <span class="text-slate-500">Le réseau Cloudflare Anycast garantit un temps de réponse minimal.</span></div></li>
            <li class="flex gap-3"><span class="text-emerald-500 font-bold text-lg">✓</span><div><strong class="text-slate-800">Chiffrement professionnel :</strong> <span class="text-slate-500">Protocole WireGuard avec chiffrement AES-256, standard bancaire.</span></div></li>
            <li class="flex gap-3"><span class="text-emerald-500 font-bold text-lg">✓</span><div><strong class="text-slate-800">Multi-clients stable :</strong> <span class="text-slate-500">Gère plusieurs dizaines d'utilisateurs simultanés sans dégradation.</span></div></li>
            <li class="flex gap-3"><span class="text-emerald-500 font-bold text-lg">✓</span><div><strong class="text-slate-800">Reconnexion automatique :</strong> <span class="text-slate-500">Keepalive de 25 secondes garantit une connexion permanente.</span></div></li>
        </ul>
    </div>
    
    <div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900 mb-4">📋 Processus en 4 étapes</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div><div class="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center mb-3">1</div><h4 class="text-xs font-bold text-slate-800">Choix du Pack</h4><p class="text-[11px] text-slate-400 mt-1">Sélectionnez votre formule idéale.</p></div>
            <div><div class="w-8 h-8 rounded-full bg-sky-100 text-sky-700 font-bold flex items-center justify-center mb-3">2</div><h4 class="text-xs font-bold text-slate-800">Configuration</h4><p class="text-[11px] text-slate-400 mt-1">Renseignez les paramètres réseau.</p></div>
            <div><div class="w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-bold flex items-center justify-center mb-3">3</div><h4 class="text-xs font-bold text-slate-800">Paiement Mobile</h4><p class="text-[11px] text-slate-400 mt-1">MVola, Orange, Airtel.</p></div>
            <div><div class="w-8 h-8 rounded-full bg-rose-100 text-rose-700 font-bold flex items-center justify-center mb-3">4</div><h4 class="text-xs font-bold text-slate-800">Livraison Instantanée</h4><p class="text-[11px] text-slate-400 mt-1">Copier-coller et c'est prêt !</p></div>
        </div>
    </div>"""
    return render_template_string(wrap("Pourquoi Nous", body))

@app.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        o = Order.query.filter((Order.order_id == code) | (Order.license_key == code)).first()
        if not o:
            flash(f"Aucune commande trouvée pour : {code}", "error")
            return redirect(url_for('track'))
        if o.status in ('validated', 'delivered'):
            return redirect(url_for('result', oid=o.order_id))
        return redirect(url_for('order_status', oid=o.order_id))
    body = """
    <div class="max-w-md mx-auto bg-white rounded-3xl p-8 border border-slate-100 shadow-md text-center">
        <h2 class="text-xl font-bold text-slate-900">🔍 Récupérer ma Configuration</h2>
        <p class="text-xs text-slate-400 mt-2 mb-6">Entrez votre code de commande (ex: KTK-XXXXXX-XXXXXX)</p>
        <form method="POST" class="space-y-4">
            <input name="code" placeholder="KTK-XXXXXX-XXXXXX" required class="w-full text-center font-bold tracking-wider py-3.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 rounded-xl text-xs shadow-md transition">🚀 Accéder à mon script</button>
        </form>
    </div>"""
    return render_template_string(wrap("Suivi", body))

@app.route('/configure/<pt>', methods=['GET', 'POST'])
def configure(pt):
    if pt not in PLANS:
        flash('Pack invalide.', 'error')
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
        
        lm_val = request.form.get('limit_mode', 'preset')
        if lm_val == 'nolimit':
            o.dl_limit = 'nolimit'
            o.ul_limit = 'nolimit'
        elif lm_val == 'custom':
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
        return redirect(url_for('payment', oid=o.order_id))

    mo = "".join(f'<option value="{m}">{m}</option>' for m in MIKROTIK_MODELS)
    hs = ""
    if pt == 'hotspot':
        hs = """
        <div class="pt-6 border-t border-slate-100">
            <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">🌐 Options Hotspot</h3>
            <div class="grid grid-cols-1 gap-4 mb-4">
                <div>
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Nom du Hotspot</label>
                    <input name="hotspot_name" value="WiFiZone" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                </div>
            </div>
            <div class="flex flex-col gap-3 mt-4">
                <div class="flex items-center gap-3 p-3 bg-slate-50 rounded-xl hover:bg-slate-100/50 transition cursor-pointer">
                    <input type="checkbox" name="pppoe" id="pppoe" class="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500">
                    <label for="pppoe" class="cursor-pointer select-none text-slate-700 text-sm font-semibold">Activer le serveur PPPoE</label>
                </div>
                <div class="flex items-center gap-3 p-3 bg-slate-50 rounded-xl hover:bg-slate-100/50 transition cursor-pointer">
                    <input type="checkbox" name="voucher" id="voucher" checked class="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500">
                    <label for="voucher" class="cursor-pointer select-none text-slate-700 text-sm font-semibold">Générer 10 vouchers d'accès</label>
                </div>
            </div>
        </div>"""

    body = f"""
    <div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-md">
        <div class="text-center pb-6 border-b border-slate-100 mb-8">
            <h2 class="text-xl font-bold" style="color:{plan['color']}">⚙️ Configuration : {plan['name']}</h2>
            <p class="text-xs text-slate-400 mt-1">Tarif : <strong class="text-slate-800">{plan['price']:,} {plan['currency']}</strong></p>
        </div>
        <form method="POST" class="space-y-6">
            <div>
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">👤 Vos Coordonnées</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Nom complet *</label>
                        <input name="client_name" required placeholder="Rakoto Andry" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Email *</label>
                        <input name="client_email" type="email" required placeholder="rakoto@gmail.com" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Téléphone</label>
                        <input name="client_phone" placeholder="034 00 000 00" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                </div>
            </div>
            <div class="pt-6 border-t border-slate-100">
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">🖥️ Modèle MikroTik</h3>
                <div class="grid grid-cols-1 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Sélectionnez votre matériel *</label>
                        <select name="mikrotik_model" id="ms" required class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="">-- Sélectionner le modèle --</option>{mo}
                        </select>
                    </div>
                </div>
                <div id="pp" class="bg-emerald-50 border border-emerald-100 p-4 rounded-xl mt-4 flex items-center gap-3" style="display:none">
                    <strong class="text-xs font-bold text-emerald-800 shrink-0">📍 Détection auto :</strong>
                    <div id="pv" class="flex gap-2 flex-wrap"></div>
                </div>
            </div>
            <div class="pt-6 border-t border-slate-100">
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">🌐 Paramètres Réseau</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Port WAN</label>
                        <select name="wan_interface" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="ether1">ether1 (Standard)</option><option value="sfp1">sfp1 (Fibre)</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Réseau LAN</label>
                        <input name="lan_network" value="192.168.88.0/24" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">IP Passerelle</label>
                        <input name="lan_gateway" value="192.168.88.1" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Pool DHCP</label>
                        <input name="dhcp_pool" value="192.168.88.10-192.168.88.250" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Nom WiFi (SSID)</label>
                        <input name="ssid" value="WiFiZone-Ketrika" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Mot de passe WiFi</label>
                        <input name="wifi_password" value="Ketrika2024" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                    </div>
                </div>
            </div>
            <div class="pt-6 border-t border-slate-100">
                <h3 class="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">⚙️ Optimisation Réseau Avancée</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Normalisation TTL</label>
                        <select name="ttl_value" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="65" selected>65 (Recommandé)</option><option value="64">64</option><option value="128">128</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Gestion Bande Passante</label>
                        <select name="limit_mode" id="lm" onchange="tl()" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="preset">📊 Profil équilibré</option>
                            <option value="nolimit">🚀 Débit illimité (Recommandé Cloudflare)</option>
                            <option value="custom">⚙️ Vitesse manuelle</option>
                        </select>
                    </div>
                </div>
                <div id="pl" class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Download / client</label>
                        <select name="dl_preset" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="5M">5 Mbps</option><option value="10M" selected>10 Mbps</option><option value="20M">20 Mbps</option><option value="50M">50 Mbps</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Upload / client</label>
                        <select name="ul_preset" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all">
                            <option value="2M">2 Mbps</option><option value="5M" selected>5 Mbps</option><option value="10M">10 Mbps</option>
                        </select>
                    </div>
                </div>
                <div id="cl" class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6" style="display:none">
                    <div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Download (ex: 25M)</label><input name="dl_custom" value="25M" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all"></div>
                    <div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Upload (ex: 10M)</label><input name="ul_custom" value="10M" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm focus:border-emerald-500 focus:bg-white focus:ring-2 focus:ring-emerald-500/10 outline-none transition-all"></div>
                </div>
                <div id="nl" class="p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800 text-xs font-semibold mt-6" style="display:none">
                    🚀 <strong>Débit illimité activé.</strong> Les clients bénéficient de l'intégralité de la bande passante via le tunnel Cloudflare stable.
                </div>
            </div>
            {hs}
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold py-4 rounded-xl shadow-lg transition">💳 Passer au Paiement — {plan['price']:,} {plan['currency']}</button>
        </form>
    </div>"""
    js = """<script>
    document.getElementById('ms').addEventListener('change',function(){var m=this.value;if(!m){document.getElementById('pp').style.display='none';return}fetch('/api/model/'+encodeURIComponent(m)).then(r=>r.json()).then(d=>{document.getElementById('pp').style.display='flex';var v=document.getElementById('pv');v.innerHTML='<span class="bg-rose-100 text-rose-700 px-2.5 py-1 rounded text-[10px] font-bold">ether1 WAN</span>';for(var i=2;i<=d.ports;i++)v.innerHTML+='<span class="bg-sky-100 text-sky-700 px-2.5 py-1 rounded text-[10px] font-bold">ether'+i+'</span>';if(d.wifi)v.innerHTML+='<span class="bg-emerald-100 text-emerald-700 px-2.5 py-1 rounded text-[10px] font-bold">WiFi</span>'})});
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
        try:
            f = request.files.get('proof')
            if not f or f.filename == '':
                flash('Veuillez sélectionner une image ou capture d\'écran.', 'error')
                return redirect(request.url)
            
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.pdf', '.webp']:
                ext = '.jpg'
                
            fn = f"{o.order_id}_{secrets.token_hex(4)}{ext}"
            fp = os.path.join(UPLOAD_FOLDER, fn)
            f.save(fp)
            
            o.payment_proof = f"static/uploads/{fn}"
            o.payment_method = request.form.get('pm', 'mvola')
            db.session.commit()
            
            flash('Preuve de transfert enregistrée. Validation en cours.', 'success')
            return redirect(url_for('order_status', oid=o.order_id))
        except Exception as e:
            db.session.rollback()
            print(f"Erreur upload paiement: {e}")
            flash('Erreur lors de l\'enregistrement de la preuve. Veuillez réessayer.', 'error')
            return redirect(request.url)

    body = f"""
    <div class="max-w-xl mx-auto bg-white rounded-3xl p-8 border border-slate-100 shadow-md">
        <h2 class="text-xl font-bold text-slate-900 text-center">💳 Confirmation du Paiement</h2>
        <p class="text-xs text-slate-400 text-center mt-1">Code de commande : <strong class="text-slate-700">{o.order_id}</strong></p>
        
        <div class="bg-slate-50 p-6 rounded-2xl text-center my-6">
            <div class="text-3xl font-extrabold text-slate-900">{p['price']:,} {p['currency']}</div>
            <p class="text-xs font-semibold text-slate-400 mt-1">{p['name']}</p>
        </div>
        
        <form method="POST" enctype="multipart/form-data" class="space-y-6">
            <div>
                <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">1. Numéro de paiement mobile</h3>
                <div class="bg-amber-50 border border-amber-100 p-4 rounded-xl">
                    <p class="text-xs font-semibold text-amber-900">📱 MVola, Orange Money, Airtel Money :</p>
                    <p class="text-xl font-black text-amber-800 mt-2">034 00 000 00</p>
                    <p class="text-[11px] text-amber-700/80 mt-1 font-semibold">Référence à inclure : {o.order_id}</p>
                </div>
            </div>
            <div>
                <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">2. Capture d'écran du transfert</h3>
                <div class="border-2 border-dashed border-slate-200 bg-slate-50 rounded-xl p-8 text-center cursor-pointer hover:bg-slate-100/50 transition" onclick="document.getElementById('fi').click()">
                    <p id="fn" class="text-xs font-bold text-slate-600">📸 Cliquez pour choisir la photo</p>
                    <p class="text-[10px] text-slate-400 mt-1">JPG, PNG ou PDF</p>
                    <input type="file" id="fi" name="proof" accept="image/*,.pdf" required class="hidden" onchange="document.getElementById('fn').textContent='✅ '+this.files[0].name; document.getElementById('fn').className='text-xs font-bold text-emerald-600'">
                </div>
            </div>
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 rounded-xl text-xs shadow-md transition">✅ Valider mon paiement</button>
        </form>
    </div>"""
    return render_template_string(wrap("Paiement", body))

@app.route('/status/<oid>')
def order_status(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    btn = f'<a href="/result/{o.order_id}" class="w-full text-center py-3.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow block transition">📥 Accéder à mon script</a>' if o.status in ('validated','delivered') else ''
    body = f"""
    <div class="max-w-md mx-auto bg-white rounded-3xl p-8 border border-slate-100 shadow-md text-center">
        <h2 class="text-xl font-bold text-slate-900">📦 Suivi Commande</h2>
        <p class="text-xs text-slate-400 mt-1">Référence : <strong>{o.order_id}</strong></p>
        <div class="text-5xl my-6">{'🟡' if o.status=='pending' else '✅'}</div>
        <h3 class="text-lg font-bold text-slate-800">{o.status_badge}</h3>
        <p class="text-xs text-slate-500 mt-2 mb-6">{'Un administrateur valide actuellement votre paiement.' if o.status=='pending' else 'Votre script MikroTik est prêt à l\'emploi !'}</p>
        {btn}
    </div>"""
    return render_template_string(wrap("Statut", body))

@app.route('/result/<oid>')
def result(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    if o.status not in ('validated', 'delivered'):
        flash('Commande en attente de validation.', 'warning')
        return redirect(url_for('order_status', oid=o.order_id))
    if not o.script_content:
        o.script_content = generate_full_script(o)
        db.session.commit()
    lim = "🚀 Débit Illimité (Cloudflare)" if o.dl_limit == 'nolimit' else f"⬇️ {o.dl_limit} / ⬆️ {o.ul_limit}"
    body = f"""
    <div class="bg-emerald-50 border border-emerald-100 rounded-3xl p-6 text-center mb-6">
        <h2 class="text-lg font-bold text-emerald-800">🎉 Votre configuration est prête !</h2>
        <p class="text-xs text-emerald-600 mt-1">ID Commande : <strong>{o.order_id}</strong> | Licence : <strong class="text-slate-800 font-bold">{o.license_key}</strong></p>
        <p class="text-xs text-slate-500 mt-3">Matériel : <strong class="font-bold text-slate-700">{o.mikrotik_model}</strong> | Gestion : <strong class="font-bold text-slate-700">{lim}</strong></p>
    </div>
    <div class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm mb-6">
        <h3 class="text-sm font-bold text-slate-800 mb-2">📋 Méthode 1 : Copier-Coller Terminal WinBox</h3>
        <p class="text-xs text-slate-400 mb-4">Ouvrez WinBox → New Terminal → Collez le script.</p>
        <button class="bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold py-2.5 px-4 rounded-lg shadow-sm transition" onclick="navigator.clipboard.writeText(document.getElementById('sc').innerText);this.textContent='✅ Script copié !';setTimeout(()=>this.textContent='📋 Copier le script',2000)">📋 Copier le script</button>
        <pre id="sc" class="bg-slate-900 text-emerald-400 p-4 rounded-xl max-h-80 overflow-y-auto text-[10px] font-mono leading-relaxed mt-4">{o.script_content}</pre>
    </div>
    <div class="bg-white rounded-3xl p-6 border-2 border-emerald-500 shadow-md">
        <h3 class="text-sm font-bold text-slate-800 mb-1">📁 Méthode 2 : Téléchargement du fichier .rsc (⭐ Recommandé)</h3>
        <p class="text-xs text-slate-400 mb-4">WinBox → Files → Glisser-déposer → Terminal : <code class="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">/import file-name=ketrika_{o.order_id}.rsc</code></p>
        <a href="/download/{o.order_id}" class="inline-flex bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold py-3 px-6 rounded-xl shadow transition">📥 Télécharger ketrika_{o.order_id}.rsc</a>
    </div>"""
    return render_template_string(wrap("Résultat", body))

@app.route('/download/<oid>')
def download(oid):
    o = Order.query.filter_by(order_id=oid).first_or_404()
    if o.status not in ('validated', 'delivered'):
        flash('Non autorisé.', 'error')
        return redirect(url_for('index'))
    if not o.script_content:
        o.script_content = generate_full_script(o)
        db.session.commit()
    return send_file(io.BytesIO(o.script_content.encode()), mimetype='text/plain', as_attachment=True, download_name=f'ketrika_{o.order_id}.rsc')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        a = Admin.query.filter_by(username=request.form['username']).first()
        if a and check_password_hash(a.password_hash, request.form['password']):
            login_user(a)
            return redirect(url_for('admin_dash'))
        flash('Identifiants incorrects.', 'error')
    body = """
    <div class="max-w-sm mx-auto bg-white rounded-3xl p-8 border border-slate-100 shadow-md">
        <h2 class="text-xl font-bold text-slate-900 text-center mb-6">🔐 Accès Admin</h2>
        <form method="POST" class="space-y-4">
            <div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Utilisateur</label><input name="username" required class="w-full px-4 py-2 rounded-xl border border-slate-200"></div>
            <div><label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Mot de passe</label><input name="password" type="password" required class="w-full px-4 py-2 rounded-xl border border-slate-200"></div>
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-lg text-xs transition mt-4">Connexion</button>
        </form>
    </div>"""
    return render_template_string(wrap("Admin", body))

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
            ac = f'<form method="POST" action="/admin/val/{o.id}" style="display:inline"><button name="a" value="v" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded-md text-[10px] font-bold">✅ Valider</button></form> '
            ac += f'<form method="POST" action="/admin/val/{o.id}" style="display:inline"><button name="a" value="r" class="bg-rose-600 hover:bg-rose-700 text-white px-2.5 py-1 rounded-md text-[10px] font-bold">❌</button></form>'
        if o.payment_proof:
            ac += f' <a href="/admin/proof/{o.id}" target="_blank" class="text-xs text-sky-600 hover:underline ml-1">📸 Preuve</a>'
        if o.license_key:
            ac += f'<br><span class="text-[9px] font-bold text-emerald-600">🔑 {o.license_key}</span>'
        rows += f'<tr class="border-b border-slate-100 hover:bg-slate-50"><td class="p-3"><strong>{o.order_id}</strong></td><td class="p-3">{o.client_name}<br><small class="text-slate-400">{o.client_email}</small></td><td class="p-3 text-xs font-bold">{o.plan_type.upper()}</td><td class="p-3 text-xs">{o.mikrotik_model}</td><td class="p-3 font-semibold">{o.plan_price:,}</td><td class="p-3"><span class="text-xs font-semibold">{o.status_badge}</span></td><td class="p-3 flex gap-1">{ac}</td></tr>'
    body = f"""
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-xl font-bold text-slate-900">Console KETRIKA</h1>
        <a href="/admin/logout" class="bg-rose-600 hover:bg-rose-700 text-white px-4 py-2 rounded-lg text-xs font-bold">Déconnexion</a>
    </div>
    <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm text-center"><div class="text-xl font-extrabold text-amber-500">{pend}</div><p class="text-[10px] text-slate-400 font-semibold mt-0.5">En attente</p></div>
        <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm text-center"><div class="text-xl font-extrabold text-emerald-600">{deli}</div><p class="text-[10px] text-slate-400 font-semibold mt-0.5">Livrées</p></div>
        <div class="bg-white p-4 rounded-xl border border-slate-100 shadow-sm text-center"><div class="text-lg font-extrabold text-sky-600">{rev:,} Ar</div><p class="text-[10px] text-slate-400 font-semibold mt-0.5">Revenus</p></div>
    </div>
    <div class="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <table class="w-full text-left border-collapse">
            <thead><tr class="bg-slate-50 text-[11px] font-bold text-slate-400 uppercase"><th class="p-3">ID</th><th class="p-3">Client</th><th class="p-3">Pack</th><th class="p-3">Matériel</th><th class="p-3">Montant</th><th class="p-3">Statut</th><th class="p-3">Actions</th></tr></thead>
            <tbody class="text-xs">{rows if rows else '<tr><td colspan="7" class="p-8 text-center text-slate-400 font-semibold">Aucune commande en cours</td></tr>'}</tbody>
        </table>
    </div>"""
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
                msg.body = f"Bonjour {o.client_name},\nVotre commande {o.order_id} est validée !\nClé : {o.license_key}\nScript : {request.host_url}result/{o.order_id}"
                mail.send(msg)
        except Exception:
            pass
        flash(f'Commande {o.order_id} validée.', 'success')
    else:
        o.status = 'rejected'
        db.session.commit()
        flash(f'Commande {o.order_id} rejetée.', 'error')
    return redirect(url_for('admin_dash'))

@app.route('/admin/proof/<int:oid>')
@login_required
def admin_proof(oid):
    o = Order.query.get_or_404(oid)
    if o.payment_proof:
        path = os.path.join(app.root_path, o.payment_proof)
        if os.path.exists(path):
            return send_file(path)
    flash('Fichier introuvable', 'error')
    return redirect(url_for('admin_dash'))

@app.route('/faq')
def faq():
    body = """
    <div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-md">
        <h2 class="text-xl font-bold text-slate-900 mb-6">❓ Questions Fréquentes</h2>
        <div class="space-y-6 text-sm">
            <div><h4 class="font-bold text-slate-800">Qu'est-ce que le Cloudflare Secure Tunnel ?</h4><p class="text-slate-500 mt-1">Une technologie WireGuard chiffrée AES-256 fournie par Cloudflare qui offre un débit illimité, une latence minimale et une stabilité garantie pour vos clients.</p></div>
            <div><h4 class="font-bold text-slate-800">Le débit reste-t-il stable avec plusieurs clients ?</h4><p class="text-slate-500 mt-1">Oui, notre solution utilise le réseau Anycast mondial de Cloudflare qui gère les gros volumes de trafic sans dégradation de vitesse.</p></div>
            <div><h4 class="font-bold text-slate-800">Faut-il redémarrer le routeur ?</h4><p class="text-slate-500 mt-1">Non, l'assignation asynchrone des ports permet une installation sans coupure de session WinBox.</p></div>
            <div><h4 class="font-bold text-slate-800">La configuration est-elle garantie sans erreur ?</h4><p class="text-slate-500 mt-1">Oui, chaque commande passe par un système de gestion d'erreurs (on-error) qui protège votre routeur contre toute mauvaise configuration.</p></div>
        </div>
    </div>"""
    return render_template_string(wrap("FAQ", body))

@app.route('/conditions')
def conditions():
    body = """<div class="bg-white rounded-3xl p-8 border border-slate-100 shadow-md"><h2 class="text-xl font-bold text-slate-900 mb-4">📜 Conditions Générales</h2><p class="text-slate-500 text-sm leading-relaxed">Une licence est strictement réservée à un unique routeur. Aucun remboursement après livraison du produit numérique.</p></div>"""
    return render_template_string(wrap("Conditions", body))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
