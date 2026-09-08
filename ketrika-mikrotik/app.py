#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Serveur Flask Principal
Plateforme de vente de configurations MikroTik RouterOS v7
"""

import os
import uuid
import secrets
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for, flash,
    send_file, session, abort, jsonify
)
from flask import render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'payments')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ketrika2024admin')

from database import db, Order, MIKROTIK_MODELS, get_next_lan_subnet
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ketrika.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(
        'postgres://', 'postgresql://', 1
    )
db.init_app(app)

with app.app_context():
    db.create_all()

def safe_get(obj, key, default=''):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default

# ===================== TEMPLATES HTML =====================

BASE_HEAD = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} - KETRIKA MIKROTIK</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
<style>
:root{--primary:#0d6efd;--success:#28a745;--dark:#212529;--light:#f8f9fa;--gray:#6c757d;--white:#fff}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--light);color:var(--dark)}
.navbar-brand{font-weight:800;font-size:1.4rem;letter-spacing:1px}
.navbar-brand .text-success{color:var(--success)!important}
.hero-section{background:linear-gradient(135deg,#f8f9fa 0%,#e8f5e9 50%,#f8f9fa 100%);padding:100px 0 80px;position:relative;overflow:hidden}
.hero-section::before{content:'';position:absolute;top:-50%;right:-20%;width:600px;height:600px;background:radial-gradient(circle,rgba(40,167,69,0.08) 0%,transparent 70%);border-radius:50%}
.hero-title{font-size:3.2rem;font-weight:800;line-height:1.15;color:var(--dark)}
.hero-title span{color:var(--success)}
.hero-subtitle{font-size:1.2rem;color:var(--gray);margin:20px 0 35px;line-height:1.7}
.btn-cta{background:var(--success);border:none;padding:16px 42px;font-size:1.15rem;font-weight:700;border-radius:50px;color:var(--white);box-shadow:0 8px 25px rgba(40,167,69,0.35);transition:all .3s}
.btn-cta:hover{background:#218838;transform:translateY(-2px);box-shadow:0 12px 35px rgba(40,167,69,0.45);color:var(--white)}
.badge-compat{display:inline-block;background:var(--white);border:2px solid var(--success);color:var(--success);padding:8px 20px;border-radius:50px;font-weight:600;font-size:.9rem;margin-top:15px}
.hero-image{font-size:15rem;color:var(--success);opacity:.15;text-align:center;line-height:1}
.hero-image-inner{font-size:8rem;color:var(--success);opacity:.7;animation:float 3s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-15px)}}
.section-title{font-size:2.2rem;font-weight:800;color:var(--dark);text-align:center;margin-bottom:15px}
.section-subtitle{text-align:center;color:var(--gray);font-size:1.05rem;margin-bottom:50px}
.feature-card{background:var(--white);border-radius:16px;padding:40px 30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.06);transition:all .3s;border:1px solid #e9ecef;height:100%}
.feature-card:hover{transform:translateY(-8px);box-shadow:0 12px 40px rgba(0,0,0,0.1)}
.feature-icon{width:70px;height:70px;background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;font-size:1.8rem;color:var(--success)}
.feature-card h5{font-weight:700;margin-bottom:12px;color:var(--dark)}
.feature-card p{color:var(--gray);font-size:.95rem;line-height:1.6}
.pricing-card{background:var(--white);border-radius:20px;padding:40px 30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.06);border:2px solid #e9ecef;transition:all .3s;position:relative;height:100%;display:flex;flex-direction:column}
.pricing-card:hover{transform:translateY(-5px);box-shadow:0 12px 40px rgba(0,0,0,0.12)}
.pricing-card.popular{border-color:var(--success);box-shadow:0 8px 30px rgba(40,167,69,0.2)}
.pricing-badge{position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:var(--success);color:var(--white);padding:5px 25px;border-radius:50px;font-weight:700;font-size:.85rem}
.pricing-badge.pro{background:var(--primary)}
.pricing-name{font-size:1.3rem;font-weight:700;color:var(--dark);margin-bottom:5px}
.pricing-price{font-size:2.8rem;font-weight:800;color:var(--success);margin:15px 0 5px}
.pricing-price small{font-size:1rem;color:var(--gray);font-weight:400}
.pricing-currency{font-size:1rem;color:var(--gray)}
.pricing-features{list-style:none;padding:0;margin:25px 0;text-align:left;flex-grow:1}
.pricing-features li{padding:8px 0;border-bottom:1px solid #f0f0f0;color:#555;font-size:.93rem}
.pricing-features li i{color:var(--success);margin-right:8px;width:18px;text-align:center}
.pricing-features li:last-child{border:none}
.btn-pricing{padding:14px 35px;border-radius:50px;font-weight:700;font-size:1rem;width:100%}
.steps-section{background:var(--white)}
.step-number{width:60px;height:60px;background:var(--success);border-radius:50%;display:flex;align-items:center;justify-content:center;color:var(--white);font-size:1.5rem;font-weight:800;margin:0 auto 20px;box-shadow:0 6px 20px rgba(40,167,69,0.3)}
.step-card{text-align:center;padding:30px 20px}
.step-card h5{font-weight:700;margin-bottom:10px}
.step-card p{color:var(--gray);font-size:.95rem}
.faq-section{background:var(--light)}
.accordion-button{font-weight:600;font-size:1.05rem;color:var(--dark);background:var(--white)}
.accordion-button:not(.collapsed){background:#e8f5e9;color:var(--success)}
.accordion-body{color:#555;line-height:1.7;font-size:.95rem}
.terms-section{background:var(--white)}
.terms-list li{padding:6px 0;color:#555;font-size:.95rem}
footer{background:var(--dark);color:var(--white);padding:40px 0}
footer a{color:var(--success);text-decoration:none}
footer a:hover{color:#34d058}
.order-form{background:var(--white);border-radius:20px;padding:50px 40px;box-shadow:0 4px 20px rgba(0,0,0,0.06)}
.form-label{font-weight:600;color:var(--dark);font-size:.95rem}
.form-control,.form-select{border-radius:10px;padding:12px 16px;border:1px solid #dee2e6;font-size:.95rem}
.form-control:focus,.form-select:focus{border-color:var(--success);box-shadow:0 0 0 .2rem rgba(40,167,69,0.15)}
.pack-radio{display:none}
.pack-label{display:block;border:2px solid #dee2e6;border-radius:14px;padding:20px;cursor:pointer;transition:all .3s;text-align:center}
.pack-radio:checked+.pack-label{border-color:var(--success);background:#e8f5e9;box-shadow:0 4px 15px rgba(40,167,69,0.15)}
.pack-label h6{font-weight:700;margin-bottom:5px}
.pack-label .price{font-size:1.3rem;font-weight:800;color:var(--success)}
.summary-box{background:linear-gradient(135deg,#f8f9fa,#e8f5e9);border-radius:16px;padding:30px;border:1px solid #c8e6c9}
.admin-nav{background:var(--dark)}
.status-badge{padding:5px 14px;border-radius:50px;font-size:.8rem;font-weight:600}
.status-pending{background:#fff3cd;color:#856404}
.status-active{background:#d4edda;color:#155724}
.status-rejected{background:#f8d7da;color:#721c24}
.stat-card{background:var(--white);border-radius:16px;padding:25px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.06)}
.stat-card .number{font-size:2.5rem;font-weight:800;color:var(--success)}
.stat-card .label{color:var(--gray);font-weight:600}
.license-box{background:var(--white);border-radius:20px;padding:40px;box-shadow:0 4px 20px rgba(0,0,0,0.06)}
.script-area{background:#1e1e1e;color:#d4d4d4;border-radius:12px;padding:20px;font-family:'Fira Code','Courier New',monospace;font-size:.85rem;max-height:500px;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
.guide-section{background:#f0f7ff;border:1px solid #b8d4f0;border-radius:14px;padding:30px;margin-top:30px}
.guide-section h5{color:var(--primary);font-weight:700}
.copy-btn{position:relative}
.copy-btn.copied::after{content:'Copié !';position:absolute;top:-30px;left:50%;transform:translateX(-50%);background:var(--success);color:#fff;padding:3px 12px;border-radius:5px;font-size:.8rem}
@media(max-width:768px){.hero-title{font-size:2.2rem}.pricing-price{font-size:2.2rem}.hero-image-inner{font-size:5rem}.order-form{padding:30px 20px}}
</style>
</head>
<body>
"""

NAVBAR = """
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
"""

BASE_FOOT = """
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ===================== PAGE ACCUEIL =====================
HOME_TEMPLATE = (
    BASE_HEAD
    + NAVBAR
    + """
<!-- HERO -->
<section class="hero-section">
<div class="container">
<div class="row align-items-center">
<div class="col-lg-7">
<h1 class="hero-title">Configurez votre <span>MikroTik</span> en 1 clic</h1>
<p class="hero-subtitle">Scripts professionnels RouterOS v7 prêts à l'emploi.<br>VPN illimité, Hotspot WiFi Zone, protection réseau avancée.</p>
<a href="/order" class="btn btn-cta"><i class="fas fa-bolt me-2"></i>Commander maintenant</a>
<br><span class="badge-compat"><i class="fas fa-check-circle me-1"></i> 100% Compatible RouterOS v7</span>
</div>
<div class="col-lg-5 d-none d-lg-block text-center">
<div class="hero-image-inner"><i class="fas fa-router"></i><br><i class="fas fa-shield-halved" style="font-size:4rem;color:#0d6efd;opacity:.5"></i></div>
</div>
</div>
</div>
</section>

<!-- POURQUOI NOUS -->
<section class="py-5" id="features">
<div class="container">
<h2 class="section-title">Pourquoi nous choisir ?</h2>
<p class="section-subtitle">Une solution clé en main pour votre réseau MikroTik</p>
<div class="row g-4">
<div class="col-md-6 col-lg-3">
<div class="feature-card">
<div class="feature-icon"><i class="fas fa-bolt"></i></div>
<h5>Configuration en 1 clic</h5>
<p>Copiez-collez le script, votre routeur se configure tout seul en 30 secondes.</p>
</div>
</div>
<div class="col-md-6 col-lg-3">
<div class="feature-card">
<div class="feature-icon"><i class="fas fa-shield-halved"></i></div>
<h5>VPN Illimité Sans Perte de Débit</h5>
<p>Naviguez sous protection permanente avec Cloudflare WARP, sans ralentissement.</p>
</div>
</div>
<div class="col-md-6 col-lg-3">
<div class="feature-card">
<div class="feature-icon"><i class="fas fa-server"></i></div>
<h5>Compatible Tous Modèles</h5>
<p>hAP ac2, hAP ax2, hEX, RB5009... Détection automatique WiFi 5 et WiFi 6.</p>
</div>
</div>
<div class="col-md-6 col-lg-3">
<div class="feature-card">
<div class="feature-icon"><i class="fab fa-whatsapp"></i></div>
<h5>Support WhatsApp</h5>
<p>Recevez votre clé de licence directement sur WhatsApp en moins de 10 minutes.</p>
</div>
</div>
</div>
</div>
</section>

<!-- TARIFS -->
<section class="py-5" style="background:var(--light)" id="pricing">
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
<li><i class="fas fa-check"></i> QoS / Limitation de bande passante</li>
</ul>
<a href="/order?pack=standard" class="btn btn-outline-success btn-pricing">Commander</a>
</div>
</div>

<div class="col-md-6 col-lg-4">
<div class="pricing-card popular">
<div class="pricing-badge">POPULAIRE</div>
<div class="pricing-name mt-2">PACK SÉCURITÉ VPN</div>
<div class="pricing-price">50 000 <small>Ar</small></div>
<ul class="pricing-features">
<li><i class="fas fa-check"></i> Tout le Pack Essentiel +</li>
<li><i class="fas fa-check"></i> VPN Cloudflare WARP illimité</li>
<li><i class="fas fa-check"></i> Protection réseau avancée</li>
<li><i class="fas fa-check"></i> Connexion chiffrée de bout en bout</li>
<li><i class="fas fa-check"></i> Aucune perte de débit</li>
<li><i class="fas fa-gift"></i> Guide exclusif "Optimisation Réseau"</li>
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
<li><i class="fas fa-check"></i> Tout le Pack Sécurité VPN +</li>
<li><i class="fas fa-check"></i> Portail Captif WiFi Zone</li>
<li><i class="fas fa-check"></i> Serveur PPPoE intégré</li>
<li><i class="fas fa-check"></i> 10 Vouchers générés automatiquement</li>
<li><i class="fas fa-check"></i> Gestion multi-profils (1h, 1j, 1sem, 1mois)</li>
<li><i class="fas fa-check"></i> Protection anti-torrent</li>
<li><i class="fas fa-gift"></i> Guide exclusif inclus</li>
</ul>
<a href="/order?pack=hotspot" class="btn btn-primary btn-pricing">Commander</a>
</div>
</div>

</div>
</div>
</section>

<!-- COMMENT CA MARCHE -->
<section class="steps-section py-5" id="how">
<div class="container">
<h2 class="section-title">Comment ça marche ?</h2>
<p class="section-subtitle">3 étapes simples pour configurer votre routeur</p>
<div class="row g-4">
<div class="col-md-4">
<div class="step-card">
<div class="step-number">1</div>
<h5><i class="fas fa-shopping-cart text-success me-2"></i>Choisissez & personnalisez</h5>
<p>Sélectionnez votre Pack, indiquez votre modèle de routeur et personnalisez vos paramètres réseau.</p>
</div>
</div>
<div class="col-md-4">
<div class="step-card">
<div class="step-number">2</div>
<h5><i class="fas fa-mobile-alt text-success me-2"></i>Payez par MVola ou Orange Money</h5>
<p>Envoyez le montant correspondant et uploadez la capture d'écran comme preuve de paiement.</p>
</div>
</div>
<div class="col-md-4">
<div class="step-card">
<div class="step-number">3</div>
<h5><i class="fas fa-check-circle text-success me-2"></i>Recevez & collez le script</h5>
<p>Recevez votre clé de licence sur WhatsApp et collez le script dans le Terminal de Winbox.</p>
</div>
</div>
</div>
</div>
</section>

<!-- FAQ -->
<section class="faq-section py-5" id="faq">
<div class="container">
<h2 class="section-title">Questions fréquentes</h2>
<p class="section-subtitle">Tout ce que vous devez savoir</p>
<div class="accordion" id="faqAccordion" style="max-width:800px;margin:0 auto">

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">Est-ce que le VPN ralentit ma connexion ?</button></h2>
<div id="faq1" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Non. Notre solution utilise Cloudflare WARP, l'un des réseaux les plus rapides au monde. Vous ne remarquerez aucune différence de vitesse, votre débit reste identique.</div></div>
</div>

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">Comment Starlink et les opérateurs 4G détectent le partage de connexion ?</button></h2>
<div id="faq2" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Les fournisseurs d'accès analysent la valeur TTL (Time To Live) de vos paquets réseau. Quand plusieurs appareils sont connectés derrière un routeur, le TTL diminue et l'opérateur le détecte. Nos scripts appliquent automatiquement un masquage TTL uniforme sur tous les appareils, rendant le partage totalement invisible.</div></div>
</div>

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">Est-ce compatible avec mon routeur MikroTik ?</button></h2>
<div id="faq3" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Oui ! Notre système détecte automatiquement votre modèle de routeur (hAP lite, hAP ac2, hAP ac3, hAP ax2, hAP ax3, hEX, RB5009, CCR...) et génère le script adapté avec la bonne configuration WiFi 5 ou WiFi 6.</div></div>
</div>

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq4">Comment je reçois ma licence ?</button></h2>
<div id="faq4" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Après validation de votre paiement, vous recevez votre clé de licence directement sur WhatsApp dans un délai de 10 minutes maximum.</div></div>
</div>

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq5">Quels sont les modes de paiement acceptés ?</button></h2>
<div id="faq5" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Nous acceptons MVola et Orange Money. Envoyez le montant au nom de JEAN ERIC et joignez la capture d'écran comme preuve de paiement avec votre numéro WhatsApp.</div></div>
</div>

<div class="accordion-item border-0 mb-3 rounded-3 overflow-hidden shadow-sm">
<h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq6">Est-ce que je peux utiliser la licence sur plusieurs routeurs ?</button></h2>
<div id="faq6" class="accordion-collapse collapse" data-bs-parent="#faqAccordion"><div class="accordion-body">Non. Chaque licence est verrouillée sur un seul routeur MikroTik pour garantir la sécurité et la qualité du service.</div></div>
</div>

</div>
</div>
</section>

<!-- CONDITIONS -->
<section class="terms-section py-5">
<div class="container" style="max-width:800px">
<h2 class="section-title">Conditions d'utilisation</h2>
<p class="section-subtitle">En achetant nos services, vous acceptez les conditions suivantes</p>
<ul class="terms-list list-unstyled">
<li><i class="fas fa-gavel text-success me-2"></i> La licence est valable pour 1 seul routeur MikroTik</li>
<li><i class="fas fa-gavel text-success me-2"></i> Le script est à usage personnel ou professionnel</li>
<li><i class="fas fa-gavel text-success me-2"></i> Aucun remboursement après activation de la licence</li>
<li><i class="fas fa-gavel text-success me-2"></i> Le service est fourni tel quel, sans garantie de compatibilité avec les mises à jour futures de RouterOS</li>
<li><i class="fas fa-gavel text-success me-2"></i> L'utilisateur est responsable de l'utilisation légale du service dans son pays</li>
</ul>
</div>
</section>

<!-- FOOTER -->
<footer>
<div class="container text-center">
<p class="mb-2"><i class="fas fa-network-wired me-2"></i><strong>KETRIKA MIKROTIK</strong></p>
<p class="mb-2"><a href="https://wa.me/261XXXXXXXXX"><i class="fab fa-whatsapp me-1"></i> WhatsApp : +261 XX XXX XX XX</a></p>
<p class="mb-2"><i class="fas fa-lock me-1"></i> Paiement sécurisé MVola &amp; Orange Money</p>
<p class="mt-3 mb-0" style="color:#adb5bd;font-size:.85rem">&copy; 2024 KETRIKA MIKROTIK - Tous droits réservés</p>
</div>
</footer>
"""
    + BASE_FOOT
)


# ===================== PAGE COMMANDE =====================
ORDER_TEMPLATE = (
    BASE_HEAD
    + NAVBAR
    + """
<section class="py-5">
<div class="container" style="max-width:850px">
<h2 class="section-title mb-2"><i class="fas fa-shopping-cart text-success me-2"></i>Commander</h2>
<p class="section-subtitle">Personnalisez votre configuration MikroTik</p>

<form class="order-form" method="POST" action="/order" id="orderForm">

<!-- Nom -->
<div class="mb-3">
<label class="form-label">Nom complet</label>
<input type="text" name="client_name" class="form-control" placeholder="Votre nom complet" required>
</div>

<!-- WhatsApp -->
<div class="mb-3">
<label class="form-label"><i class="fab fa-whatsapp text-success me-1"></i> Numéro WhatsApp</label>
<input type="text" name="whatsapp" class="form-control" placeholder="+261 34 XX XXX XX" required>
</div>

<!-- Pack -->
<div class="mb-4">
<label class="form-label">Choisissez votre Pack</label>
<div class="row g-3">
<div class="col-md-4">
<input type="radio" name="plan_type" value="standard" id="p1" class="pack-radio" {{ 'checked' if preselect=='standard' else '' }}>
<label class="pack-label" for="p1">
<h6>Pack Essentiel</h6>
<div class="price">30 000 Ar</div>
</label>
</div>
<div class="col-md-4">
<input type="radio" name="plan_type" value="warp" id="p2" class="pack-radio" {{ 'checked' if preselect=='warp' else '' }}>
<label class="pack-label" for="p2">
<h6>Pack Sécurité VPN</h6>
<div class="price">50 000 Ar</div>
</label>
</div>
<div class="col-md-4">
<input type="radio" name="plan_type" value="hotspot" id="p3" class="pack-radio" {{ 'checked' if preselect=='hotspot' else '' }}>
<label class="pack-label" for="p3">
<h6>Pack Business Hotspot</h6>
<div class="price">80 000 Ar</div>
</label>
</div>
</div>
</div>

<!-- Modèle MikroTik -->
<div class="mb-3">
<label class="form-label">Modèle MikroTik</label>
<select name="mikrotik_model" class="form-select" required>
<option value="">-- Sélectionnez votre modèle --</option>
{% for key, info in models.items() %}
<option value="{{ key }}">{{ info.name }}</option>
{% endfor %}
<option value="other">Autre (préciser ci-dessous)</option>
</select>
</div>
<div class="mb-3" id="otherModelDiv" style="display:none">
<label class="form-label">Précisez votre modèle</label>
<input type="text" name="other_model" class="form-control" placeholder="Ex: RB1100AHx4">
</div>

<!-- WiFi -->
<div class="row g-3 mb-3" id="wifiSection">
<div class="col-md-6">
<label class="form-label">Nom du réseau Wi-Fi (SSID)</label>
<input type="text" name="ssid" class="form-control" placeholder="MonReseau_WiFi" value="KETRIKA-WiFi">
</div>
<div class="col-md-6">
<label class="form-label">Mot de passe Wi-Fi (min. 8 car.)</label>
<input type="text" name="wifi_password" class="form-control" placeholder="MotDePasse123" minlength="8">
</div>
</div>

<!-- Réseau -->
<h5 class="mt-4 mb-3 fw-bold"><i class="fas fa-network-wired text-primary me-2"></i>Paramètres réseau</h5>
<div class="row g-3 mb-3">
<div class="col-md-6">
<label class="form-label">Interface WAN</label>
<input type="text" name="wan_interface" class="form-control" value="ether1">
</div>
<div class="col-md-6">
<label class="form-label">IP Gateway LAN</label>
<input type="text" name="lan_gateway" class="form-control" value="auto" readonly>
<small class="text-muted">Attribué automatiquement pour éviter les conflits</small>
</div>
</div>
<div class="row g-3 mb-3">
<div class="col-md-6">
<label class="form-label">Sous-réseau LAN</label>
<input type="text" name="lan_network" class="form-control" value="auto" readonly>
</div>
<div class="col-md-6">
<label class="form-label">Plage DHCP</label>
<input type="text" name="dhcp_pool" class="form-control" value="auto" readonly>
</div>
</div>

<!-- Options -->
<h5 class="mt-4 mb-3 fw-bold"><i class="fas fa-sliders-h text-primary me-2"></i>Options</h5>
<div class="row g-3 mb-3">
<div class="col-md-4">
<label class="form-label">Valeur TTL</label>
<select name="ttl_value" class="form-select">
<option value="64" selected>64 (Recommandé)</option>
<option value="65">65</option>
<option value="128">128</option>
<option value="0">Désactivé</option>
</select>
</div>
<div class="col-md-4">
<label class="form-label">Limite Download</label>
<select name="dl_limit" class="form-select">
<option value="0">Illimité</option>
<option value="2M">2 Mbps</option>
<option value="5M">5 Mbps</option>
<option value="10M">10 Mbps</option>
<option value="20M">20 Mbps</option>
<option value="50M">50 Mbps</option>
<option value="100M">100 Mbps</option>
</select>
</div>
<div class="col-md-4">
<label class="form-label">Limite Upload</label>
<select name="ul_limit" class="form-select">
<option value="0">Illimité</option>
<option value="1M">1 Mbps</option>
<option value="2M">2 Mbps</option>
<option value="5M">5 Mbps</option>
<option value="10M">10 Mbps</option>
<option value="20M">20 Mbps</option>
<option value="50M">50 Mbps</option>
</select>
</div>
</div>

<!-- Options Pack 3 -->
<div id="hotspotOptions" style="display:none" class="p-3 mb-3 rounded-3" style="background:#f0f7ff">
<h6 class="fw-bold text-primary"><i class="fas fa-wifi me-1"></i> Options Hotspot (Pack Business)</h6>
<div class="form-check mb-2">
<input type="checkbox" name="pppoe_enabled" class="form-check-input" id="pppoeCheck" value="1">
<label class="form-check-label" for="pppoeCheck">Activer le serveur PPPoE</label>
</div>
<div class="form-check">
<input type="checkbox" name="voucher_enabled" class="form-check-input" id="voucherCheck" value="1" checked>
<label class="form-check-label" for="voucherCheck">Générer 10 Vouchers automatiquement</label>
</div>
</div>

<button type="submit" class="btn btn-cta w-100 mt-3"><i class="fas fa-paper-plane me-2"></i>Valider ma commande</button>
</form>
</div>
</section>

<footer>
<div class="container text-center">
<p class="mb-0" style="color:#adb5bd;font-size:.85rem">&copy; 2024 KETRIKA MIKROTIK</p>
</div>
</footer>

<script>
document.querySelectorAll('input[name=plan_type]').forEach(r=>{
    r.addEventListener('change',function(){
        document.getElementById('hotspotOptions').style.display=this.value==='hotspot'?'block':'none';
    });
});
document.querySelector('select[name=mikrotik_model]').addEventListener('change',function(){
    document.getElementById('otherModelDiv').style.display=this.value==='other'?'block':'none';
});
// Init
(function(){
    var sel=document.querySelector('input[name=plan_type]:checked');
    if(sel && sel.value==='hotspot') document.getElementById('hotspotOptions').style.display='block';
})();
</script>
"""
    + BASE_FOOT
)


# ===================== PAGE PAIEMENT =====================
PAY_TEMPLATE = (
    BASE_HEAD
    + NAVBAR
    + """
<section class="py-5">
<div class="container" style="max-width:700px">
<div class="order-form">
<h3 class="text-center fw-bold mb-4"><i class="fas fa-credit-card text-success me-2"></i>Paiement</h3>

<div class="summary-box mb-4">
<h5 class="fw-bold mb-3">Résumé de votre commande</h5>
<table class="table table-borderless mb-0">
<tr><td class="fw-semibold">Référence</td><td>{{ order.order_id }}</td></tr>
<tr><td class="fw-semibold">Client</td><td>{{ order.client_name }}</td></tr>
<tr><td class="fw-semibold">WhatsApp</td><td>{{ order.whatsapp_number }}</td></tr>
<tr><td class="fw-semibold">Pack</td><td>
{% if order.plan_type == 'standard' %}Pack Essentiel
{% elif order.plan_type == 'warp' %}Pack Sécurité VPN
{% else %}Pack Business Hotspot{% endif %}
</td></tr>
<tr><td class="fw-semibold">Modèle</td><td>{{ order.mikrotik_model }}</td></tr>
<tr><td class="fw-semibold">Prix</td><td class="fw-bold text-success fs-5">
{% if order.plan_type == 'standard' %}30 000 Ar
{% elif order.plan_type == 'warp' %}50 000 Ar
{% else %}80 000 Ar{% endif %}
</td></tr>
</table>
</div>

<div class="alert alert-success">
<h6 class="fw-bold"><i class="fas fa-info-circle me-1"></i> Instructions de paiement</h6>
<p class="mb-1">Envoyez <strong>
{% if order.plan_type == 'standard' %}30 000 Ar
{% elif order.plan_type == 'warp' %}50 000 Ar
{% else %}80 000 Ar{% endif %}
</strong> par MVola ou Orange Money au nom de <strong>JEAN ERIC</strong></p>
<p class="mb-1"><i class="fas fa-phone me-1"></i> <strong>MVola :</strong> 034 XX XXX XX</p>
<p class="mb-1"><i class="fas fa-phone me-1"></i> <strong>Orange Money :</strong> 032 XX XXX XX</p>
<p class="mb-0 mt-2"><em>IMPORTANT : Mentionnez votre numéro WhatsApp dans le motif du transfert.</em></p>
</div>

<form method="POST" action="/pay/{{ order.order_id }}" enctype="multipart/form-data">
<div class="mb-3">
<label class="form-label fw-bold">Capture d'écran de la preuve de paiement</label>
<input type="file" name="payment_proof" class="form-control" accept="image/*" required>
</div>
<div class="mb-3">
<label class="form-label fw-bold">Confirmez votre numéro WhatsApp</label>
<input type="text" name="whatsapp_confirm" class="form-control" value="{{ order.whatsapp_number }}" required>
</div>
<button type="submit" class="btn btn-cta w-100"><i class="fas fa-upload me-2"></i>Envoyer la preuve de paiement</button>
</form>
</div>
</div>
</section>

<footer>
<div class="container text-center">
<p class="mb-0" style="color:#adb5bd;font-size:.85rem">&copy; 2024 KETRIKA MIKROTIK</p>
</div>
</footer>
"""
    + BASE_FOOT
)


# ===================== PAGE CONFIRMATION PAIEMENT =====================
PAY_CONFIRM_TEMPLATE = (
    BASE_HEAD
    + NAVBAR
    + """
<section class="py-5">
<div class="container text-center" style="max-width:600px">
<div class="order-form">
<div style="font-size:5rem;color:var(--success)"><i class="fas fa-check-circle"></i></div>
<h3 class="fw-bold mt-3">Merci !</h3>
<p class="text-muted fs-5">Votre paiement est en cours de vérification.</p>
<p class="mt-3">Vous recevrez votre clé de licence sur <strong>WhatsApp</strong> dans un délai de <strong>10 minutes</strong> maximum.</p>
<p class="mt-2"><small class="text-muted">Référence : {{ order_id }}</small></p>
<a href="/" class="btn btn-outline-success mt-3 rounded-pill px-4">Retour à l'accueil</a>
</div>
</div>
</section>
"""
    + BASE_FOOT
)


# ===================== PAGE LICENCE =====================
LICENSE_TEMPLATE = (
    BASE_HEAD
    + NAVBAR
    + """
<section class="py-5">
<div class="container" style="max-width:900px">
<div class="license-box">

<div class="text-center mb-4">
<div style="font-size:4rem;color:var(--success)"><i class="fas fa-key"></i></div>
<h3 class="fw-bold">Votre Licence KETRIKA MIKROTIK</h3>
<span class="badge bg-success fs-6 px-3 py-2 mt-2">{{ order.license_key }}</span>
</div>

<div class="summary-box mb-4">
<div class="row">
<div class="col-md-6">
<p class="mb-1"><strong>Client :</strong> {{ order.client_name }}</p>
<p class="mb-1"><strong>Pack :</strong>
{% if order.plan_type == 'standard' %}Pack Essentiel
{% elif order.plan_type == 'warp' %}Pack Sécurité VPN
{% else %}Pack Business Hotspot{% endif %}
</p>
</div>
<div class="col-md-6">
<p class="mb-1"><strong>Modèle :</strong> {{ order.mikrotik_model }}</p>
<p class="mb-1"><strong>SSID :</strong> {{ order.ssid }}</p>
</div>
</div>
</div>

<h5 class="fw-bold mb-3"><i class="fas fa-code text-success me-2"></i>Votre Script MikroTik</h5>
<div class="script-area" id="scriptContent">{{ script }}</div>

<div class="row g-3 mt-3">
<div class="col-md-6">
<button class="btn btn-success w-100 rounded-pill copy-btn" id="copyBtn" onclick="copyScript()"><i class="fas fa-copy me-2"></i>Copier le script</button>
</div>
<div class="col-md-6">
<a href="/download/{{ order.license_key }}" class="btn btn-outline-primary w-100 rounded-pill"><i class="fas fa-download me-2"></i>Télécharger (.rsc)</a>
</div>
</div>

<div class="alert alert-info mt-4">
<h6 class="fw-bold"><i class="fas fa-book me-1"></i> Instructions d'installation</h6>
<ol class="mb-0">
<li>Ouvrez <strong>Winbox</strong> et connectez-vous à votre routeur MikroTik</li>
<li>Allez dans <strong>System → Terminal</strong> (ou New Terminal)</li>
<li>Cliquez sur le bouton <strong>"Copier le script"</strong> ci-dessus</li>
<li><strong>Collez</strong> le script dans le terminal Winbox (Ctrl+V)</li>
<li>Le routeur va se configurer automatiquement et <strong>redémarrer</strong> dans 3 secondes</li>
<li>Après le redémarrage, connectez-vous au réseau WiFi "<strong>{{ order.ssid }}</strong>"</li>
</ol>
</div>

{% if order.plan_type in ['warp', 'hotspot'] %}
<div class="guide-section">
<h5><i class="fas fa-graduation-cap me-2"></i>Guide Exclusif : Optimisation Réseau Avancée</h5>
<hr>
<h6 class="fw-bold mt-3">Comment Starlink et les opérateurs 4G/5G détectent le partage Wi-Fi</h6>
<ul>
<li><strong>Analyse TTL :</strong> Chaque paquet réseau possède une valeur TTL qui diminue à chaque passage par un routeur. Les opérateurs comparent le TTL reçu : si la valeur varie (64, 63, 128, 127...), ils détectent que plusieurs appareils sont connectés derrière un routeur.</li>
<li><strong>Signature User-Agent :</strong> Certains opérateurs analysent les en-têtes HTTP pour détecter la diversité des appareils (Windows, Android, iPhone...).</li>
<li><strong>DPI (Deep Packet Inspection) :</strong> Inspection profonde des paquets pour identifier les patterns de trafic multi-appareils.</li>
</ul>
<h6 class="fw-bold mt-3">Comment notre script résout ce problème automatiquement</h6>
<ul>
<li><strong>Masquage TTL uniforme :</strong> Tous les paquets sortants reçoivent la même valeur TTL (64), rendant impossible la détection du nombre d'appareils.</li>
<li><strong>MSS Clamping :</strong> Ajustement automatique de la taille maximale des segments TCP à 1280 octets pour éviter la fragmentation dans le tunnel WireGuard.</li>
<li><strong>Tunnel chiffré WireGuard :</strong> Tout le trafic passe par Cloudflare WARP, empêchant le DPI de voir le contenu des paquets.</li>
</ul>
<h6 class="fw-bold mt-3">Conseils d'utilisation</h6>
<ul>
<li><i class="fas fa-exclamation-triangle text-warning me-1"></i> <strong>Ne modifiez pas</strong> les règles Firewall Mangle après installation</li>
<li><i class="fas fa-satellite-dish text-primary me-1"></i> <strong>Starlink :</strong> Branchez le câble Starlink directement sur le Port 1 (ether1) du MikroTik</li>
<li><i class="fas fa-sync text-success me-1"></i> Si le VPN se déconnecte, redémarrez simplement le routeur</li>
</ul>
</div>
{% endif %}

</div>
</div>
</section>

<footer>
<div class="container text-center">
<p class="mb-0" style="color:#adb5bd;font-size:.85rem">&copy; 2024 KETRIKA MIKROTIK</p>
</div>
</footer>

<script>
function copyScript(){
    var t=document.getElementById('scriptContent').innerText;
    navigator.clipboard.writeText(t).then(function(){
        var b=document.getElementById('copyBtn');
        b.classList.add('copied');
        b.innerHTML='<i class="fas fa-check me-2"></i>Copié !';
        setTimeout(function(){b.classList.remove('copied');b.innerHTML='<i class="fas fa-copy me-2"></i>Copier le script';},2000);
    });
}
</script>
"""
    + BASE_FOOT
)


# ===================== PAGE ADMIN LOGIN =====================
ADMIN_LOGIN_TEMPLATE = (
    BASE_HEAD
    + """
<div class="d-flex align-items-center justify-content-center" style="min-height:100vh;background:var(--light)">
<div class="order-form text-center" style="max-width:400px;width:100%">
<h3 class="fw-bold mb-4"><i class="fas fa-lock text-success me-2"></i>Admin</h3>
{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
<form method="POST">
<div class="mb-3"><input type="password" name="password" class="form-control text-center" placeholder="Mot de passe admin" required></div>
<button class="btn btn-success w-100 rounded-pill">Connexion</button>
</form>
</div>
</div>
"""
    + BASE_FOOT
)


# ===================== PAGE ADMIN DASHBOARD =====================
ADMIN_DASHBOARD_TEMPLATE = (
    BASE_HEAD
    + """
<nav class="navbar admin-nav navbar-dark">
<div class="container">
<span class="navbar-brand"><i class="fas fa-shield-halved me-2"></i>KETRIKA ADMIN</span>
<a href="/admin/logout" class="btn btn-outline-light btn-sm rounded-pill"><i class="fas fa-sign-out-alt me-1"></i>Déconnexion</a>
</div>
</nav>

<section class="py-4">
<div class="container">

<!-- Stats -->
<div class="row g-3 mb-4">
<div class="col-md-3">
<div class="stat-card">
<div class="number">{{ stats.total }}</div>
<div class="label">Total commandes</div>
</div>
</div>
<div class="col-md-3">
<div class="stat-card">
<div class="number" style="color:var(--primary)">{{ stats.pending }}</div>
<div class="label">En attente</div>
</div>
</div>
<div class="col-md-3">
<div class="stat-card">
<div class="number">{{ stats.active }}</div>
<div class="label">Licences actives</div>
</div>
</div>
<div class="col-md-3">
<div class="stat-card">
<div class="number">{{ stats.revenue }}</div>
<div class="label">Revenus (Ar)</div>
</div>
</div>
</div>

<!-- Commandes -->
<div class="card shadow-sm border-0 rounded-4">
<div class="card-header bg-white border-0 pt-4 px-4">
<h5 class="fw-bold"><i class="fas fa-list me-2 text-success"></i>Toutes les commandes</h5>
</div>
<div class="card-body p-0">
<div class="table-responsive">
<table class="table table-hover mb-0">
<thead class="table-light">
<tr>
<th>Date</th><th>Client</th><th>WhatsApp</th><th>Pack</th><th>Modèle</th><th>Prix</th><th>Preuve</th><th>Licence</th><th>Statut</th><th>Actions</th>
</tr>
</thead>
<tbody>
{% for o in orders %}
<tr>
<td><small>{{ o.created_at.strftime('%d/%m/%Y %H:%M') if o.created_at else '-' }}</small></td>
<td class="fw-semibold">{{ o.client_name }}</td>
<td><a href="https://wa.me/{{ o.whatsapp_number|replace(' ','')|replace('+','') }}" target="_blank" class="text-success">{{ o.whatsapp_number }}</a></td>
<td>
{% if o.plan_type == 'standard' %}<span class="badge bg-secondary">Essentiel</span>
{% elif o.plan_type == 'warp' %}<span class="badge bg-success">VPN</span>
{% else %}<span class="badge bg-primary">Hotspot</span>{% endif %}
</td>
<td><small>{{ o.mikrotik_model }}</small></td>
<td class="fw-bold">
{% if o.plan_type == 'standard' %}30 000
{% elif o.plan_type == 'warp' %}50 000
{% else %}80 000{% endif %}
</td>
<td>
{% if o.payment_proof %}
<a href="/admin/proof/{{ o.order_id }}" target="_blank" class="btn btn-sm btn-outline-primary rounded-pill"><i class="fas fa-image"></i></a>
{% else %}<span class="text-muted">-</span>{% endif %}
</td>
<td><small class="text-monospace">{{ o.license_key[:12] }}...</small></td>
<td>
{% if o.status == 'pending' %}<span class="status-badge status-pending">En attente</span>
{% elif o.status == 'active' %}<span class="status-badge status-active">Validée</span>
{% else %}<span class="status-badge status-rejected">Refusée</span>{% endif %}
</td>
<td>
{% if o.status == 'pending' %}
<form method="POST" action="/admin/validate/{{ o.order_id }}" style="display:inline">
<button class="btn btn-sm btn-success rounded-pill" title="Valider"><i class="fas fa-check"></i></button>
</form>
<form method="POST" action="/admin/reject/{{ o.order_id }}" style="display:inline">
<button class="btn btn-sm btn-danger rounded-pill" title="Refuser"><i class="fas fa-times"></i></button>
</form>
{% elif o.status == 'active' %}
<a href="/license/{{ o.license_key }}" target="_blank" class="btn btn-sm btn-outline-success rounded-pill" title="Voir licence"><i class="fas fa-eye"></i></a>
{% endif %}
</td>
</tr>
{% endfor %}
{% if not orders %}
<tr><td colspan="10" class="text-center py-4 text-muted">Aucune commande pour le moment</td></tr>
{% endif %}
</tbody>
</table>
</div>
</div>
</div>

</div>
</section>
"""
    + BASE_FOOT
)


# ===================== ROUTES =====================

@app.route('/')
def home():
    try:
        return render_template_string(HOME_TEMPLATE, title="Accueil")
    except Exception as e:
        return f"Erreur: {e}", 500


@app.route('/order', methods=['GET', 'POST'])
def order():
    try:
        if request.method == 'GET':
            preselect = request.args.get('pack', 'standard')
            return render_template_string(
                ORDER_TEMPLATE,
                title="Commander",
                models=MIKROTIK_MODELS,
                preselect=preselect
            )

        # POST - Traitement commande
        client_name = request.form.get('client_name', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        plan_type = request.form.get('plan_type', 'standard')
        mikrotik_model = request.form.get('mikrotik_model', '')
        if mikrotik_model == 'other':
            mikrotik_model = request.form.get('other_model', 'Unknown').strip()

        ssid = request.form.get('ssid', 'KETRIKA-WiFi').strip()
        wifi_password = request.form.get('wifi_password', '12345678').strip()
        wan_interface = request.form.get('wan_interface', 'ether1').strip()
        ttl_value = request.form.get('ttl_value', '64')
        dl_limit = request.form.get('dl_limit', '0')
        ul_limit = request.form.get('ul_limit', '0')
        pppoe_enabled = request.form.get('pppoe_enabled') == '1'
        voucher_enabled = request.form.get('voucher_enabled') == '1'

        # Générer IP LAN unique
        subnet_info = get_next_lan_subnet()
        lan_gateway = subnet_info['gateway']
        lan_network = subnet_info['network']
        dhcp_pool = subnet_info['pool']

        # Générer IDs
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
            lan_gateway=lan_gateway,
            lan_network=lan_network,
            dhcp_pool=dhcp_pool,
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

    except Exception as e:
        db.session.rollback()
        return f"Erreur lors de la commande: {e}", 500


@app.route('/pay/<order_id>', methods=['GET', 'POST'])
def pay(order_id):
    try:
        order_obj = Order.query.filter_by(order_id=order_id).first()
        if not order_obj:
            abort(404)

        if request.method == 'GET':
            return render_template_string(PAY_TEMPLATE, title="Paiement", order=order_obj)

        # POST - Upload preuve
        file = request.files.get('payment_proof')
        if file and file.filename:
            filename = secure_filename(f"{order_id}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            order_obj.payment_proof = filename

        whatsapp_confirm = request.form.get('whatsapp_confirm', '')
        if whatsapp_confirm:
            order_obj.whatsapp_number = whatsapp_confirm

        db.session.commit()

        return render_template_string(PAY_CONFIRM_TEMPLATE, title="Confirmation", order_id=order_id)

    except Exception as e:
        db.session.rollback()
        return f"Erreur: {e}", 500


@app.route('/license/<key>')
def license_page(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            abort(404)
        if order_obj.status != 'active':
            return render_template_string(
                BASE_HEAD + NAVBAR + """
                <section class="py-5"><div class="container text-center" style="max-width:600px">
                <div class="order-form">
                <div style="font-size:4rem;color:#ffc107"><i class="fas fa-clock"></i></div>
                <h3 class="fw-bold mt-3">Licence en attente</h3>
                <p class="text-muted">Votre licence n'a pas encore été activée. Veuillez patienter pendant la vérification de votre paiement.</p>
                <p><small>Clé : {{ key }}</small></p>
                </div></div></section>
                """ + BASE_FOOT,
                title="Licence en attente",
                key=key
            )

        # Générer le script
        from warp_api import generate_script
        script = generate_script(order_obj)

        return render_template_string(LICENSE_TEMPLATE, title="Licence", order=order_obj, script=script)

    except Exception as e:
        return f"Erreur: {e}", 500


@app.route('/download/<key>')
def download_script(key):
    try:
        order_obj = Order.query.filter_by(license_key=key, status='active').first()
        if not order_obj:
            abort(404)

        from warp_api import generate_script
        script = generate_script(order_obj)

        filename = f"ketrika_{safe_get(order_obj, 'plan_type', 'config')}_{key[:12]}.rsc"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(script)

        return send_file(filepath, as_attachment=True, download_name=filename)

    except Exception as e:
        return f"Erreur: {e}", 500


# ===================== ADMIN ROUTES =====================

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    try:
        if session.get('admin_logged'):
            return redirect(url_for('admin_dashboard'))

        error = None
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['admin_logged'] = True
                return redirect(url_for('admin_dashboard'))
            error = "Mot de passe incorrect"

        return render_template_string(ADMIN_LOGIN_TEMPLATE, title="Admin Login", error=error)

    except Exception as e:
        return f"Erreur: {e}", 500


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

        stats = {
            'total': total,
            'pending': pending,
            'active': active,
            'revenue': f"{revenue:,}".replace(',', ' ')
        }

        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            title="Admin Dashboard",
            orders=orders,
            stats=stats
        )

    except Exception as e:
        return f"Erreur: {e}", 500


@app.route('/admin/validate/<order_id>', methods=['POST'])
def admin_validate(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))

        order_obj = Order.query.filter_by(order_id=order_id).first()
        if order_obj:
            order_obj.status = 'active'
            db.session.commit()

        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        db.session.rollback()
        return f"Erreur: {e}", 500


@app.route('/admin/reject/<order_id>', methods=['POST'])
def admin_reject(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))

        order_obj = Order.query.filter_by(order_id=order_id).first()
        if order_obj:
            order_obj.status = 'rejected'
            db.session.commit()

        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        db.session.rollback()
        return f"Erreur: {e}", 500


@app.route('/admin/proof/<order_id>')
def admin_proof(order_id):
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))

        order_obj = Order.query.filter_by(order_id=order_id).first()
        if not order_obj or not order_obj.payment_proof:
            abort(404)

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], order_obj.payment_proof)
        if not os.path.exists(filepath):
            abort(404)

        return send_file(filepath)

    except Exception as e:
        return f"Erreur: {e}", 500


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))


# ===================== DÉMARRAGE =====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
