#!/usr/bin/env python3
"""KETRIKA MIKROTIK - Serveur Flask"""

import os
import uuid
import secrets
import traceback
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for,
    send_file, session, abort, render_template_string
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'payments')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ketrika2024admin')

# Database URL - Render fournit DATABASE_URL pour Postgres
db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'ketrika.db'))
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

from database import db, Order, MIKROTIK_MODELS, get_next_lan_subnet
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")


def safe_get(obj, key, default=''):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default


# ============ TEMPLATES (CSS séparé pour éviter conflit Jinja) ============

CSS_STYLES = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#f8f9fa;color:#212529}
.navbar-brand{font-weight:800;font-size:1.4rem;letter-spacing:1px}
.hero-section{background:linear-gradient(135deg,#f8f9fa 0%,#e8f5e9 50%,#f8f9fa 100%);padding:100px 0 80px}
.hero-title{font-size:3rem;font-weight:800;line-height:1.15;color:#212529}
.hero-title span{color:#28a745}
.hero-subtitle{font-size:1.15rem;color:#6c757d;margin:20px 0 35px;line-height:1.7}
.btn-cta{background:#28a745;border:none;padding:16px 42px;font-size:1.1rem;font-weight:700;border-radius:50px;color:#fff;box-shadow:0 8px 25px rgba(40,167,69,.35);transition:all .3s}
.btn-cta:hover{background:#218838;transform:translateY(-2px);color:#fff}
.badge-compat{display:inline-block;background:#fff;border:2px solid #28a745;color:#28a745;padding:8px 20px;border-radius:50px;font-weight:600;font-size:.9rem;margin-top:15px}
.hero-image-inner{font-size:8rem;color:#28a745;opacity:.7}
.section-title{font-size:2.2rem;font-weight:800;color:#212529;text-align:center;margin-bottom:15px}
.section-subtitle{text-align:center;color:#6c757d;font-size:1.05rem;margin-bottom:50px}
.feature-card{background:#fff;border-radius:16px;padding:40px 30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.06);transition:all .3s;height:100%}
.feature-card:hover{transform:translateY(-8px)}
.feature-icon{width:70px;height:70px;background:#e8f5e9;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:1.8rem;color:#28a745}
.pricing-card{background:#fff;border-radius:20px;padding:40px 30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.06);border:2px solid #e9ecef;height:100%;display:flex;flex-direction:column;position:relative}
.pricing-card.popular{border-color:#28a745;box-shadow:0 8px 30px rgba(40,167,69,.2)}
.pricing-badge{position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:#28a745;color:#fff;padding:5px 25px;border-radius:50px;font-weight:700;font-size:.85rem}
.pricing-badge.pro{background:#0d6efd}
.pricing-name{font-size:1.3rem;font-weight:700;color:#212529;margin-bottom:5px}
.pricing-price{font-size:2.8rem;font-weight:800;color:#28a745;margin:15px 0 5px}
.pricing-features{list-style:none;padding:0;margin:25px 0;text-align:left;flex-grow:1}
.pricing-features li{padding:8px 0;border-bottom:1px solid #f0f0f0;color:#555;font-size:.93rem}
.pricing-features li i{color:#28a745;margin-right:8px}
.pricing-features li:last-child{border:none}
.btn-pricing{padding:14px 35px;border-radius:50px;font-weight:700;width:100%}
.step-number{width:60px;height:60px;background:#28a745;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.5rem;font-weight:800;margin:0 auto 20px}
.step-card{text-align:center;padding:30px 20px}
.accordion-button:not(.collapsed){background:#e8f5e9;color:#28a745}
footer{background:#212529;color:#fff;padding:40px 0}
footer a{color:#28a745;text-decoration:none}
.order-form{background:#fff;border-radius:20px;padding:40px 30px;box-shadow:0 4px 20px rgba(0,0,0,.06)}
.form-label{font-weight:600;color:#212529}
.form-control,.form-select{border-radius:10px;padding:12px 16px}
.form-control:focus,.form-select:focus{border-color:#28a745;box-shadow:0 0 0 .2rem rgba(40,167,69,.15)}
.pack-radio{display:none}
.pack-label{display:block;border:2px solid #dee2e6;border-radius:14px;padding:20px;cursor:pointer;transition:all .3s;text-align:center}
.pack-radio:checked+.pack-label{border-color:#28a745;background:#e8f5e9}
.pack-label h6{font-weight:700;margin-bottom:5px}
.pack-label .price{font-size:1.3rem;font-weight:800;color:#28a745}
.summary-box{background:#e8f5e9;border-radius:16px;padding:30px;border:1px solid #c8e6c9}
.stat-card{background:#fff;border-radius:16px;padding:25px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,.06)}
.stat-card .number{font-size:2.5rem;font-weight:800;color:#28a745}
.stat-card .label{color:#6c757d;font-weight:600}
.status-badge{padding:5px 14px;border-radius:50px;font-size:.8rem;font-weight:600}
.status-pending{background:#fff3cd;color:#856404}
.status-active{background:#d4edda;color:#155724}
.status-rejected{background:#f8d7da;color:#721c24}
.script-area{background:#1e1e1e;color:#d4d4d4;border-radius:12px;padding:20px;font-family:monospace;font-size:.85rem;max-height:500px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.guide-section{background:#f0f7ff;border:1px solid #b8d4f0;border-radius:14px;padding:30px;margin-top:30px}
@media(max-width:768px){.hero-title{font-size:2rem}.pricing-price{font-size:2.2rem}}
"""


def render_page(body_html, title="KETRIKA MIKROTIK", extra_script=""):
    """Rendu générique d'une page avec header + body + footer"""
    full_html = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + title + """ - KETRIKA MIKROTIK</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
<style>""" + CSS_STYLES + """</style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm sticky-top">
<div class="container">
<a class="navbar-brand" href="/"><i class="fas fa-network-wired text-success me-2"></i>KETRIKA <span class="text-success">MIKROTIK</span></a>
<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain"><span class="navbar-toggler-icon"></span></button>
<div class="collapse navbar-collapse" id="navMain">
<ul class="navbar-nav ms-auto">
<li class="nav-item"><a class="nav-link fw-semibold" href="/#pricing">Tarifs</a></li>
<li class="nav-item"><a class="nav-link fw-semibold" href="/#how">Comment ça marche</a></li>
<li class="nav-item"><a class="nav-link fw-semibold" href="/#faq">FAQ</a></li>
<li class="nav-item ms-lg-3"><a class="btn btn-success btn-sm px-4 rounded-pill fw-bold" href="/order"><i class="fas fa-shopping-cart me-1"></i> Commander</a></li>
</ul>
</div>
</div>
</nav>
""" + body_html + """
<footer>
<div class="container text-center">
<p class="mb-2"><i class="fas fa-network-wired me-2"></i><strong>KETRIKA MIKROTIK</strong></p>
<p class="mb-2"><a href="https://wa.me/261340000000"><i class="fab fa-whatsapp me-1"></i> WhatsApp Support</a></p>
<p class="mb-2"><i class="fas fa-lock me-1"></i> Paiement sécurisé MVola &amp; Orange Money</p>
<p class="mt-3 mb-0" style="color:#adb5bd;font-size:.85rem">&copy; 2024 KETRIKA MIKROTIK - Tous droits réservés</p>
</div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
""" + extra_script + """
</body>
</html>"""
    return full_html


# ============ PAGE ACCUEIL ============
HOME_BODY = """
<section class="hero-section">
<div class="container">
<div class="row align-items-center">
<div class="col-lg-7">
<h1 class="hero-title">Configurez votre <span>MikroTik</span> en 1 clic</h1>
<p class="hero-subtitle">Scripts professionnels RouterOS v7 prêts à l'emploi. VPN illimité, Hotspot WiFi Zone, protection réseau avancée.</p>
<a href="/order" class="btn btn-cta"><i class="fas fa-bolt me-2"></i>Commander maintenant</a>
<br><span class="badge-compat"><i class="fas fa-check-circle me-1"></i> 100% Compatible RouterOS v7</span>
</div>
<div class="col-lg-5 d-none d-lg-block text-center">
<div class="hero-image-inner"><i class="fas fa-router"></i></div>
</div>
</div>
</div>
</section>

<section class="py-5">
<div class="container">
<h2 class="section-title">Pourquoi nous choisir ?</h2>
<p class="section-subtitle">Une solution clé en main pour votre réseau MikroTik</p>
<div class="row g-4">
<div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-bolt"></i></div><h5>Configuration en 1 clic</h5><p>Copiez-collez le script, votre routeur se configure tout seul en 30 secondes.</p></div></div>
<div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-shield-halved"></i></div><h5>VPN Illimité</h5><p>Naviguez sous protection permanente avec Cloudflare WARP, sans ralentissement.</p></div></div>
<div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-server"></i></div><h5>Compatible Tous Modèles</h5><p>hAP ac2, hAP ax2, hEX, RB5009... Détection auto WiFi 5 et WiFi 6.</p></div></div>
<div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fab fa-whatsapp"></i></div><h5>Support WhatsApp</h5><p>Recevez votre clé sur WhatsApp en moins de 10 minutes.</p></div></div>
</div>
</div>
</section>

<section class="py-5" style="background:#f8f9fa" id="pricing">
<div class="container">
<h2 class="section-title">Nos Tarifs</h2>
<p class="section-subtitle">Choisissez le pack adapté à vos besoins</p>
<div class="row g-4 justify-content-center">
<div class="col-md-6 col-lg-4">
<div class="pricing-card">
<div class="pricing-name">PACK ESSENTIEL</div>
<div class="pricing-price">30 000 <small>Ar</small></div>
<ul class="pricing-features">
<li><i class="fas fa-check"></i> Configuration automatique complète</li>
<li><i class="fas fa-check"></i> Wi-Fi sécurisé (WPA2-PSK)</li>
<li><i class="fas fa-check"></i> DNS chiffré (DoH Cloudflare)</li>
<li><i class="fas fa-check"></i> Masquage TTL (Anti-coupure partage)</li>
<li><i class="fas fa-check"></i> QoS / Limitation bande passante</li>
</ul>
<a href="/order?pack=standard" class="btn btn-outline-success btn-pricing">Commander</a>
</div>
</div>
<div class="col-md-6 col-lg-4">
<div class="pricing-card popular">
<div class="pricing-badge">POPULAIRE</div>
<div class="pricing-name mt-2">PACK SECURITE VPN</div>
<div class="pricing-price">50 000 <small>Ar</small></div>
<ul class="pricing-features">
<li><i class="fas fa-check"></i> Tout le Pack Essentiel +</li>
<li><i class="fas fa-check"></i> VPN Cloudflare WARP illimité</li>
<li><i class="fas fa-check"></i> Protection réseau avancée</li>
<li><i class="fas fa-check"></i> Connexion chiffrée bout en bout</li>
<li><i class="fas fa-check"></i> Aucune perte de débit</li>
<li><i class="fas fa-gift"></i> Guide exclusif Optimisation Réseau</li>
</ul>
<a href="/order?pack=warp" class="btn btn-success btn-pricing">Commander</a>
</div>
</div>
<div class="col-md-6 col-lg-4">
<div class="pricing-card">
<div class="pricing-badge pro">PRO</div>
<div class="pricing-name mt-2">PACK BUSINESS HOTSPOT</div>
<div class="pricing-price">80 000 <small>Ar</small></div>
<ul class="pricing-features">
<li><i class="fas fa-check"></i> Tout le Pack Securite VPN +</li>
<li><i class="fas fa-check"></i> Portail Captif WiFi Zone</li>
<li><i class="fas fa-check"></i> Serveur PPPoE intégré</li>
<li><i class="fas fa-check"></i> 10 Vouchers générés</li>
<li><i class="fas fa-check"></i> Multi-profils (1h, 1j, 1sem, 1mois)</li>
<li><i class="fas fa-check"></i> Protection anti-torrent</li>
<li><i class="fas fa-gift"></i> Guide exclusif inclus</li>
</ul>
<a href="/order?pack=hotspot" class="btn btn-primary btn-pricing">Commander</a>
</div>
</div>
</div>
</div>
</section>

<section class="py-5" id="how" style="background:#fff">
<div class="container">
<h2 class="section-title">Comment ça marche ?</h2>
<p class="section-subtitle">3 étapes simples</p>
<div class="row g-4">
<div class="col-md-4"><div class="step-card"><div class="step-number">1</div><h5><i class="fas fa-shopping-cart text-success me-2"></i>Choisissez et personnalisez</h5><p>Sélectionnez votre Pack et personnalisez vos paramètres.</p></div></div>
<div class="col-md-4"><div class="step-card"><div class="step-number">2</div><h5><i class="fas fa-mobile-alt text-success me-2"></i>Payez par MVola ou Orange Money</h5><p>Envoyez le montant et uploadez la preuve.</p></div></div>
<div class="col-md-4"><div class="step-card"><div class="step-number">3</div><h5><i class="fas fa-check-circle text-success me-2"></i>Recevez votre script</h5><p>Recevez votre clé sur WhatsApp et collez le script dans Winbox.</p></div></div>
</div>
</div>
</section>

<section class="py-5" id="faq">
<div class="container">
<h2 class="section-title">Questions fréquentes</h2>
<div class="accordion" id="faqAcc" style="max-width:800px;margin:0 auto">
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f1">Est-ce que le VPN ralentit ma connexion ?</button></h2>
<div id="f1" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">Non. Cloudflare WARP est l'un des réseaux les plus rapides au monde. Votre débit reste identique.</div></div>
</div>
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f2">Comment Starlink détecte le partage ?</button></h2>
<div id="f2" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">Les FAI analysent la valeur TTL des paquets. Nos scripts appliquent un masquage TTL uniforme, rendant le partage invisible.</div></div>
</div>
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f3">Est-ce compatible avec mon routeur ?</button></h2>
<div id="f3" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">Oui ! Détection automatique du modèle avec configuration WiFi 5 ou WiFi 6 adaptée.</div></div>
</div>
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f4">Comment je reçois ma licence ?</button></h2>
<div id="f4" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">Après validation, vous recevez votre clé sur WhatsApp en moins de 10 minutes.</div></div>
</div>
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f5">Quels sont les modes de paiement ?</button></h2>
<div id="f5" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">MVola et Orange Money au nom de JEAN ERIC.</div></div>
</div>
<div class="accordion-item border-0 mb-3 rounded-3 shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f6">Une licence pour plusieurs routeurs ?</button></h2>
<div id="f6" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body">Non. Chaque licence est verrouillée sur un seul routeur.</div></div>
</div>
</div>
</div>
</section>
"""


@app.route('/')
def home():
    try:
        return render_page(HOME_BODY, title="Accueil")
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ============ PAGE COMMANDE ============
@app.route('/order', methods=['GET', 'POST'])
def order():
    try:
        if request.method == 'POST':
            client_name = (request.form.get('client_name') or '').strip()
            whatsapp = (request.form.get('whatsapp') or '').strip()
            plan_type = request.form.get('plan_type') or 'standard'
            mikrotik_model = request.form.get('mikrotik_model') or 'hap_ac2'
            if mikrotik_model == 'other':
                mikrotik_model = (request.form.get('other_model') or 'Unknown').strip()

            ssid = (request.form.get('ssid') or 'KETRIKA-WiFi').strip()
            wifi_password = (request.form.get('wifi_password') or 'ketrika2024').strip()
            wan_interface = (request.form.get('wan_interface') or 'ether1').strip()
            ttl_value = request.form.get('ttl_value') or '64'
            dl_limit = request.form.get('dl_limit') or '0'
            ul_limit = request.form.get('ul_limit') or '0'
            pppoe_enabled = request.form.get('pppoe_enabled') == '1'
            voucher_enabled = request.form.get('voucher_enabled') == '1'

            subnet_info = get_next_lan_subnet()
            order_id = 'KTR-' + uuid.uuid4().hex[:8].upper()
            license_key = 'LIC-' + secrets.token_hex(16).upper()

            new_order = Order(
                order_id=order_id,
                license_key=license_key,
                client_name=client_name,
                whatsapp_number=whatsapp,
                plan_type=plan_type,
                mikrotik_model=mikrotik_model,
                ssid=ssid,
                wifi_password=wifi_password,
                wan_interface=wan_interface,
                lan_gateway=subnet_info['gateway'],
                lan_network=subnet_info['network'],
                dhcp_pool=subnet_info['pool'],
                ttl_value=ttl_value,
                dl_limit=dl_limit,
                ul_limit=ul_limit,
                pppoe_enabled=pppoe_enabled,
                voucher_enabled=voucher_enabled,
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(new_order)
            db.session.commit()
            return redirect(url_for('pay', order_id=order_id))

        # GET
        preselect = request.args.get('pack', 'standard')

        # Options du select modèle
        options_html = '<option value="">-- Sélectionnez votre modèle --</option>'
        for key, info in MIKROTIK_MODELS.items():
            options_html += f'<option value="{key}">{info["name"]}</option>'
        options_html += '<option value="other">Autre (préciser)</option>'

        # Radios pack
        c1 = 'checked' if preselect == 'standard' else ''
        c2 = 'checked' if preselect == 'warp' else ''
        c3 = 'checked' if preselect == 'hotspot' else ''

        body = f"""
<section class="py-5">
<div class="container" style="max-width:850px">
<h2 class="section-title mb-2"><i class="fas fa-shopping-cart text-success me-2"></i>Commander</h2>
<p class="section-subtitle">Personnalisez votre configuration MikroTik</p>
<form class="order-form" method="POST" action="/order">
<div class="mb-3"><label class="form-label">Nom complet</label>
<input type="text" name="client_name" class="form-control" required></div>
<div class="mb-3"><label class="form-label"><i class="fab fa-whatsapp text-success me-1"></i> Numéro WhatsApp</label>
<input type="text" name="whatsapp" class="form-control" placeholder="+261 34 XX XXX XX" required></div>
<div class="mb-4"><label class="form-label">Choisissez votre Pack</label>
<div class="row g-3">
<div class="col-md-4"><input type="radio" name="plan_type" value="standard" id="p1" class="pack-radio" {c1}>
<label class="pack-label" for="p1"><h6>Pack Essentiel</h6><div class="price">30 000 Ar</div></label></div>
<div class="col-md-4"><input type="radio" name="plan_type" value="warp" id="p2" class="pack-radio" {c2}>
<label class="pack-label" for="p2"><h6>Pack Sécurité VPN</h6><div class="price">50 000 Ar</div></label></div>
<div class="col-md-4"><input type="radio" name="plan_type" value="hotspot" id="p3" class="pack-radio" {c3}>
<label class="pack-label" for="p3"><h6>Pack Business Hotspot</h6><div class="price">80 000 Ar</div></label></div>
</div></div>
<div class="mb-3"><label class="form-label">Modèle MikroTik</label>
<select name="mikrotik_model" class="form-select" id="modelSelect" required>{options_html}</select></div>
<div class="mb-3" id="otherModelDiv" style="display:none">
<label class="form-label">Précisez votre modèle</label>
<input type="text" name="other_model" class="form-control"></div>
<div class="row g-3 mb-3">
<div class="col-md-6"><label class="form-label">Nom du réseau Wi-Fi (SSID)</label>
<input type="text" name="ssid" class="form-control" value="KETRIKA-WiFi"></div>
<div class="col-md-6"><label class="form-label">Mot de passe Wi-Fi</label>
<input type="text" name="wifi_password" class="form-control" minlength="8" value="ketrika2024"></div>
</div>
<h5 class="mt-4 mb-3 fw-bold"><i class="fas fa-network-wired text-primary me-2"></i>Paramètres réseau</h5>
<div class="row g-3 mb-3">
<div class="col-md-6"><label class="form-label">Interface WAN</label>
<input type="text" name="wan_interface" class="form-control" value="ether1"></div>
<div class="col-md-6"><label class="form-label">IP LAN (auto)</label>
<input type="text" class="form-control" value="Générée automatiquement" readonly></div>
</div>
<h5 class="mt-4 mb-3 fw-bold"><i class="fas fa-sliders-h text-primary me-2"></i>Options</h5>
<div class="row g-3 mb-3">
<div class="col-md-4"><label class="form-label">Valeur TTL</label>
<select name="ttl_value" class="form-select">
<option value="64" selected>64 (Recommandé)</option>
<option value="65">65</option>
<option value="128">128</option>
<option value="0">Désactivé</option>
</select></div>
<div class="col-md-4"><label class="form-label">Limite Download</label>
<select name="dl_limit" class="form-select">
<option value="0">Illimité</option><option value="2M">2M</option><option value="5M">5M</option>
<option value="10M">10M</option><option value="20M">20M</option><option value="50M">50M</option><option value="100M">100M</option>
</select></div>
<div class="col-md-4"><label class="form-label">Limite Upload</label>
<select name="ul_limit" class="form-select">
<option value="0">Illimité</option><option value="1M">1M</option><option value="2M">2M</option>
<option value="5M">5M</option><option value="10M">10M</option><option value="20M">20M</option><option value="50M">50M</option>
</select></div>
</div>
<div id="hotspotOptions" style="display:none;background:#f0f7ff;padding:20px;border-radius:12px" class="mb-3">
<h6 class="fw-bold text-primary"><i class="fas fa-wifi me-1"></i> Options Hotspot</h6>
<div class="form-check mb-2"><input type="checkbox" name="pppoe_enabled" class="form-check-input" id="pppoeCheck" value="1">
<label class="form-check-label" for="pppoeCheck">Activer le serveur PPPoE</label></div>
<div class="form-check"><input type="checkbox" name="voucher_enabled" class="form-check-input" id="voucherCheck" value="1" checked>
<label class="form-check-label" for="voucherCheck">Générer 10 Vouchers</label></div>
</div>
<button type="submit" class="btn btn-cta w-100 mt-3"><i class="fas fa-paper-plane me-2"></i>Valider ma commande</button>
</form>
</div>
</section>
"""

        js = """
<script>
document.querySelectorAll('input[name=plan_type]').forEach(function(r){
    r.addEventListener('change',function(){
        document.getElementById('hotspotOptions').style.display=this.value==='hotspot'?'block':'none';
    });
});
document.getElementById('modelSelect').addEventListener('change',function(){
    document.getElementById('otherModelDiv').style.display=this.value==='other'?'block':'none';
});
(function(){var s=document.querySelector('input[name=plan_type]:checked');
if(s&&s.value==='hotspot')document.getElementById('hotspotOptions').style.display='block';})();
</script>
"""
        return render_page(body, title="Commander", extra_script=js)

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return f"<h1>Erreur commande</h1><pre>{e}</pre>", 500


# ============ PAGE PAIEMENT ============
@app.route('/pay/<order_id>', methods=['GET', 'POST'])
def pay(order_id):
    try:
        order_obj = Order.query.filter_by(order_id=order_id).first()
        if not order_obj:
            abort(404)

        if request.method == 'POST':
            file = request.files.get('payment_proof')
            if file and file.filename:
                fname = secure_filename(f"{order_id}_{file.filename}")
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                file.save(fpath)
                order_obj.payment_proof = fname

            wa_confirm = (request.form.get('whatsapp_confirm') or '').strip()
            if wa_confirm:
                order_obj.whatsapp_number = wa_confirm
            db.session.commit()

            body = f"""
<section class="py-5">
<div class="container text-center" style="max-width:600px">
<div class="order-form">
<div style="font-size:5rem;color:#28a745"><i class="fas fa-check-circle"></i></div>
<h3 class="fw-bold mt-3">Merci !</h3>
<p class="text-muted fs-5">Votre paiement est en cours de vérification.</p>
<p class="mt-3">Vous recevrez votre clé sur <strong>WhatsApp</strong> dans <strong>10 minutes</strong> max.</p>
<p class="mt-2"><small class="text-muted">Référence : {order_id}</small></p>
<a href="/" class="btn btn-outline-success mt-3 rounded-pill px-4">Retour à l'accueil</a>
</div></div></section>
"""
            return render_page(body, title="Paiement confirmé")

        # GET - Affichage
        plan = safe_get(order_obj, 'plan_type', 'standard')
        if plan == 'standard':
            plan_name = 'Pack Essentiel'
            prix = '30 000 Ar'
        elif plan == 'warp':
            plan_name = 'Pack Sécurité VPN'
            prix = '50 000 Ar'
        else:
            plan_name = 'Pack Business Hotspot'
            prix = '80 000 Ar'

        body = f"""
<section class="py-5">
<div class="container" style="max-width:700px">
<div class="order-form">
<h3 class="text-center fw-bold mb-4"><i class="fas fa-credit-card text-success me-2"></i>Paiement</h3>
<div class="summary-box mb-4">
<h5 class="fw-bold mb-3">Résumé de votre commande</h5>
<p class="mb-1"><strong>Référence :</strong> {safe_get(order_obj,'order_id')}</p>
<p class="mb-1"><strong>Client :</strong> {safe_get(order_obj,'client_name')}</p>
<p class="mb-1"><strong>WhatsApp :</strong> {safe_get(order_obj,'whatsapp_number')}</p>
<p class="mb-1"><strong>Pack :</strong> {plan_name}</p>
<p class="mb-1"><strong>Modèle :</strong> {safe_get(order_obj,'mikrotik_model')}</p>
<p class="mb-0"><strong>Prix :</strong> <span class="fw-bold text-success fs-5">{prix}</span></p>
</div>
<div class="alert alert-success">
<h6 class="fw-bold"><i class="fas fa-info-circle me-1"></i> Instructions de paiement</h6>
<p class="mb-1">Envoyez <strong>{prix}</strong> par MVola ou Orange Money au nom de <strong>JEAN ERIC</strong></p>
<p class="mb-1"><i class="fas fa-phone me-1"></i> <strong>MVola :</strong> 034 XX XXX XX</p>
<p class="mb-1"><i class="fas fa-phone me-1"></i> <strong>Orange :</strong> 032 XX XXX XX</p>
<p class="mb-0 mt-2"><em>IMPORTANT : Mentionnez votre numéro WhatsApp dans le motif.</em></p>
</div>
<form method="POST" action="/pay/{order_id}" enctype="multipart/form-data">
<div class="mb-3"><label class="form-label fw-bold">Capture d'écran de la preuve</label>
<input type="file" name="payment_proof" class="form-control" accept="image/*" required></div>
<div class="mb-3"><label class="form-label fw-bold">Confirmez votre WhatsApp</label>
<input type="text" name="whatsapp_confirm" class="form-control" value="{safe_get(order_obj,'whatsapp_number')}" required></div>
<button type="submit" class="btn btn-cta w-100"><i class="fas fa-upload me-2"></i>Envoyer la preuve</button>
</form>
</div></div></section>
"""
        return render_page(body, title="Paiement")

    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ============ PAGE LICENCE ============
@app.route('/license/<key>')
def license_page(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            abort(404)

        if safe_get(order_obj, 'status') != 'active':
            body = f"""
<section class="py-5"><div class="container text-center" style="max-width:600px">
<div class="order-form">
<div style="font-size:4rem;color:#ffc107"><i class="fas fa-clock"></i></div>
<h3 class="fw-bold mt-3">Licence en attente</h3>
<p class="text-muted">Votre licence n'est pas encore activée. Patientez pendant la vérification.</p>
<p><small>Clé : {key}</small></p>
</div></div></section>
"""
            return render_page(body, title="Licence en attente")

        from warp_api import generate_script
        script = generate_script(order_obj)
        # Échapper pour éviter injection HTML
        script_safe = script.replace('<', '&lt;').replace('>', '&gt;')

        plan = safe_get(order_obj, 'plan_type', 'standard')
        if plan == 'standard':
            plan_name = 'Pack Essentiel'
        elif plan == 'warp':
            plan_name = 'Pack Sécurité VPN'
        else:
            plan_name = 'Pack Business Hotspot'

        guide_html = ""
        if plan in ['warp', 'hotspot']:
            guide_html = """
<div class="guide-section">
<h5 style="color:#0d6efd;font-weight:700"><i class="fas fa-graduation-cap me-2"></i>Guide Exclusif : Optimisation Réseau</h5>
<hr>
<h6 class="fw-bold mt-3">Comment Starlink et les opérateurs 4G/5G détectent le partage Wi-Fi</h6>
<ul>
<li><strong>Analyse TTL :</strong> Chaque paquet perd 1 TTL par routeur. Les FAI comparent le TTL pour détecter les appareils derrière un routeur.</li>
<li><strong>User-Agent :</strong> Analyse des en-têtes HTTP pour identifier la diversité des appareils.</li>
<li><strong>DPI :</strong> Inspection profonde pour identifier les patterns multi-appareils.</li>
</ul>
<h6 class="fw-bold mt-3">Comment notre script résout ça</h6>
<ul>
<li><strong>Masquage TTL uniforme :</strong> Tous les paquets sortants ont le même TTL.</li>
<li><strong>MSS Clamping :</strong> Taille TCP à 1280 pour éviter la fragmentation.</li>
<li><strong>Tunnel WireGuard :</strong> Trafic chiffré via Cloudflare WARP.</li>
</ul>
<h6 class="fw-bold mt-3">Conseils</h6>
<ul>
<li><i class="fas fa-exclamation-triangle text-warning me-1"></i> Ne modifiez pas les règles Firewall Mangle après installation</li>
<li><i class="fas fa-satellite-dish text-primary me-1"></i> Starlink : Branchez le câble sur le Port 1 (ether1)</li>
</ul>
</div>
"""

        body = f"""
<section class="py-5">
<div class="container" style="max-width:900px">
<div class="order-form">
<div class="text-center mb-4">
<div style="font-size:4rem;color:#28a745"><i class="fas fa-key"></i></div>
<h3 class="fw-bold">Votre Licence KETRIKA MIKROTIK</h3>
<span class="badge bg-success fs-6 px-3 py-2 mt-2">{safe_get(order_obj,'license_key')}</span>
</div>
<div class="summary-box mb-4">
<p class="mb-1"><strong>Client :</strong> {safe_get(order_obj,'client_name')}</p>
<p class="mb-1"><strong>Pack :</strong> {plan_name}</p>
<p class="mb-1"><strong>Modèle :</strong> {safe_get(order_obj,'mikrotik_model')}</p>
<p class="mb-0"><strong>SSID :</strong> {safe_get(order_obj,'ssid')}</p>
</div>
<h5 class="fw-bold mb-3"><i class="fas fa-code text-success me-2"></i>Votre Script MikroTik</h5>
<div class="script-area" id="scriptContent">{script_safe}</div>
<div class="row g-3 mt-3">
<div class="col-md-6"><button class="btn btn-success w-100 rounded-pill" id="copyBtn" onclick="copyScript()"><i class="fas fa-copy me-2"></i>Copier le script</button></div>
<div class="col-md-6"><a href="/download/{key}" class="btn btn-outline-primary w-100 rounded-pill"><i class="fas fa-download me-2"></i>Télécharger (.rsc)</a></div>
</div>
<div class="alert alert-info mt-4">
<h6 class="fw-bold"><i class="fas fa-book me-1"></i> Instructions</h6>
<ol class="mb-0">
<li>Ouvrez <strong>Winbox</strong> et connectez-vous</li>
<li>Allez dans <strong>System → Terminal</strong></li>
<li>Cliquez sur <strong>Copier le script</strong></li>
<li>Collez dans le terminal (Ctrl+V)</li>
<li>Le routeur se configure et redémarre en 3 secondes</li>
<li>Connectez-vous au WiFi "<strong>{safe_get(order_obj,'ssid')}</strong>"</li>
</ol>
</div>
{guide_html}
</div></div></section>
"""
        js = """
<script>
function copyScript(){
  var t=document.getElementById('scriptContent').innerText;
  navigator.clipboard.writeText(t).then(function(){
    var b=document.getElementById('copyBtn');
    b.innerHTML='<i class="fas fa-check me-2"></i>Copié !';
    setTimeout(function(){b.innerHTML='<i class="fas fa-copy me-2"></i>Copier le script';},2000);
  });
}
</script>
"""
        return render_page(body, title="Licence", extra_script=js)

    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur licence</h1><pre>{e}</pre>", 500


# ============ DOWNLOAD ============
@app.route('/download/<key>')
def download_script(key):
    try:
        order_obj = Order.query.filter_by(license_key=key, status='active').first()
        if not order_obj:
            abort(404)
        from warp_api import generate_script
        script = generate_script(order_obj)
        fname = f"ketrika_{safe_get(order_obj,'plan_type','config')}_{key[:12]}.rsc"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(script)
        return send_file(fpath, as_attachment=True, download_name=fname)
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ============ ADMIN ============
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    try:
        if session.get('admin_logged'):
            return redirect(url_for('admin_dashboard'))
        error = ''
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['admin_logged'] = True
                return redirect(url_for('admin_dashboard'))
            error = '<div class="alert alert-danger">Mot de passe incorrect</div>'
        body = f"""
<div class="d-flex align-items-center justify-content-center" style="min-height:80vh">
<div class="order-form text-center" style="max-width:400px;width:100%">
<h3 class="fw-bold mb-4"><i class="fas fa-lock text-success me-2"></i>Admin</h3>
{error}
<form method="POST">
<div class="mb-3"><input type="password" name="password" class="form-control text-center" placeholder="Mot de passe" required></div>
<button class="btn btn-success w-100 rounded-pill">Connexion</button>
</form>
</div></div>
"""
        return render_page(body, title="Admin")
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


@app.route('/admin/dashboard')
def admin_dashboard():
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))

        orders = Order.query.order_by(Order.created_at.desc()).all()
        total = len(orders)
        pending = sum(1 for o in orders if safe_get(o, 'status') == 'pending')
        active = sum(1 for o in orders if safe_get(o, 'status') == 'active')
        revenue = 0
        for o in orders:
            if safe_get(o, 'status') == 'active':
                pt = safe_get(o, 'plan_type', '')
                if pt == 'standard':
                    revenue += 30000
                elif pt == 'warp':
                    revenue += 50000
                elif pt == 'hotspot':
                    revenue += 80000
        revenue_str = f"{revenue:,}".replace(',', ' ')

        rows = ""
        for o in orders:
            plan = safe_get(o, 'plan_type', '')
            if plan == 'standard':
                pack_badge = '<span class="badge bg-secondary">Essentiel</span>'
                prix = '30 000'
            elif plan == 'warp':
                pack_badge = '<span class="badge bg-success">VPN</span>'
                prix = '50 000'
            else:
                pack_badge = '<span class="badge bg-primary">Hotspot</span>'
                prix = '80 000'

            status = safe_get(o, 'status', 'pending')
            if status == 'pending':
                status_badge = '<span class="status-badge status-pending">En attente</span>'
                actions = f'''
<form method="POST" action="/admin/validate/{o.order_id}" style="display:inline">
<button class="btn btn-sm btn-success rounded-pill"><i class="fas fa-check"></i></button></form>
<form method="POST" action="/admin/reject/{o.order_id}" style="display:inline">
<button class="btn btn-sm btn-danger rounded-pill"><i class="fas fa-times"></i></button></form>
'''
            elif status == 'active':
                status_badge = '<span class="status-badge status-active">Validée</span>'
                actions = f'<a href="/license/{o.license_key}" target="_blank" class="btn btn-sm btn-outline-success rounded-pill"><i class="fas fa-eye"></i></a>'
            else:
                status_badge = '<span class="status-badge status-rejected">Refusée</span>'
                actions = ''

            proof = '<span class="text-muted">-</span>'
            if safe_get(o, 'payment_proof'):
                proof = f'<a href="/admin/proof/{o.order_id}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill"><i class="fas fa-image"></i></a>'

            date_str = o.created_at.strftime('%d/%m/%Y %H:%M') if o.created_at else '-'
            wa = safe_get(o, 'whatsapp_number', '').replace(' ', '').replace('+', '')

            rows += f"""
<tr>
<td><small>{date_str}</small></td>
<td class="fw-semibold">{safe_get(o,'client_name')}</td>
<td><a href="https://wa.me/{wa}" target="_blank" class="text-success">{safe_get(o,'whatsapp_number')}</a></td>
<td>{pack_badge}</td>
<td><small>{safe_get(o,'mikrotik_model')}</small></td>
<td class="fw-bold">{prix}</td>
<td>{proof}</td>
<td><small>{safe_get(o,'license_key','')[:12]}...</small></td>
<td>{status_badge}</td>
<td>{actions}</td>
</tr>
"""

        if not rows:
            rows = '<tr><td colspan="10" class="text-center py-4 text-muted">Aucune commande</td></tr>'

        body = f"""
<div style="background:#212529;padding:15px 0;margin-bottom:20px">
<div class="container d-flex justify-content-between align-items-center">
<span style="color:#fff;font-weight:700"><i class="fas fa-shield-halved me-2"></i>KETRIKA ADMIN</span>
<a href="/admin/logout" class="btn btn-outline-light btn-sm rounded-pill"><i class="fas fa-sign-out-alt me-1"></i>Déconnexion</a>
</div>
</div>
<section class="py-4">
<div class="container">
<div class="row g-3 mb-4">
<div class="col-md-3"><div class="stat-card"><div class="number">{total}</div><div class="label">Total commandes</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="number" style="color:#0d6efd">{pending}</div><div class="label">En attente</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="number">{active}</div><div class="label">Licences actives</div></div></div>
<div class="col-md-3"><div class="stat-card"><div class="number">{revenue_str}</div><div class="label">Revenus (Ar)</div></div></div>
</div>
<div class="card shadow-sm border-0 rounded-4">
<div class="card-header bg-white border-0 pt-4 px-4">
<h5 class="fw-bold"><i class="fas fa-list me-2 text-success"></i>Toutes les commandes</h5>
</div>
<div class="card-body p-0">
<div class="table-responsive">
<table class="table table-hover mb-0">
<thead class="table-light">
<tr><th>Date</th><th>Client</th><th>WhatsApp</th><th>Pack</th><th>Modèle</th><th>Prix</th><th>Preuve</th><th>Licence</th><th>Statut</th><th>Actions</th></tr>
</thead>
<tbody>{rows}</tbody>
</table>
</div></div></div>
</div></section>
"""
        return render_page(body, title="Dashboard Admin")
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur admin</h1><pre>{e}</pre>", 500


@app.route('/admin/validate/<order_id>', methods=['POST'])
def admin_validate(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        o = Order.query.filter_by(order_id=order_id).first()
        if o:
            o.status = 'active'
            db.session.commit()
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return f"Erreur: {e}", 500


@app.route('/admin/reject/<order_id>', methods=['POST'])
def admin_reject(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        o = Order.query.filter_by(order_id=order_id).first()
        if o:
            o.status = 'rejected'
            db.session.commit()
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return f"Erreur: {e}", 500


@app.route('/admin/proof/<order_id>')
def admin_proof(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))
        o = Order.query.filter_by(order_id=order_id).first()
        if not o or not o.payment_proof:
            abort(404)
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], o.payment_proof)
        if not os.path.exists(fpath):
            abort(404)
        return send_file(fpath)
    except Exception as e:
        traceback.print_exc()
        return f"Erreur: {e}", 500


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))


@app.route('/health')
def health():
    return {'status': 'ok'}, 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
