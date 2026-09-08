#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Serveur d'Application Flask Principal (Version Finale Corrigée 2026)
"""

import os
import uuid
import secrets
import traceback
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for,
    send_file, session, abort
)
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'payments')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ketrika2024admin')

# Coordonnées de paiement
MVOLA_NUMBER = "038 28 171 00"
ORANGE_NUMBER = "037 39 755 72"
WHATSAPP_NUMBER = "0382817100"  # sans indicatif pour lien wa.me
WHATSAPP_DISPLAY = "+261 38 28 171 00"
PAYMENT_NAME = "JEAN ERIC"

from database import db, Order, MIKROTIK_MODELS, get_next_lan_subnet, get_model_info

db_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'ketrika.db'))
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

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


# ===================== STYLE =====================

CSS_STYLES = """
:root { --primary: #0d6efd; --success: #28a745; --dark: #212529; --light: #f8f9fa; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #fafafa; color: #333; }
.navbar-brand { font-weight: 800; font-size: 1.4rem; }
.hero-section { background: linear-gradient(135deg, #ffffff 0%, #e8f5e9 100%); padding: 90px 0; }
.hero-title { font-size: 3rem; font-weight: 800; }
.hero-title span { color: var(--success); }
.hero-subtitle { font-size: 1.15rem; color: #6c757d; margin: 20px 0 35px; line-height: 1.7; }
.btn-cta { background: var(--success); border: none; padding: 15px 40px; font-size: 1.1rem; font-weight: 700; border-radius: 50px; color: #fff; box-shadow: 0 8px 20px rgba(40,167,69,0.3); transition: 0.3s; }
.btn-cta:hover { background: #218838; transform: translateY(-2px); color:#fff; }
.badge-compat { display: inline-block; background: #fff; border: 2px solid var(--success); color: var(--success); padding: 8px 20px; border-radius: 50px; font-weight: 600; margin-top: 15px; }
.feature-card { background: #fff; border-radius: 16px; padding: 35px 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #eee; height: 100%; transition: 0.3s; }
.feature-card:hover { transform: translateY(-5px); }
.feature-icon { width: 60px; height: 60px; background: #e8f5e9; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 1.6rem; color: var(--success); }
.pricing-card { background: #fff; border-radius: 20px; padding: 40px 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 2px solid #eee; height: 100%; display: flex; flex-direction: column; position: relative; }
.pricing-card.popular { border-color: var(--success); box-shadow: 0 8px 25px rgba(40,167,69,0.15); }
.pricing-badge { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); background: var(--success); color: #fff; padding: 5px 25px; border-radius: 50px; font-weight: 700; font-size: 0.8rem; }
.pricing-badge.pro { background: var(--primary); }
.pricing-price { font-size: 2.6rem; font-weight: 800; color: var(--success); margin: 15px 0; }
.pricing-features { list-style: none; padding: 0; margin: 20px 0; text-align: left; flex-grow: 1; }
.pricing-features li { padding: 8px 0; border-bottom: 1px solid #f9f9f9; font-size: 0.93rem; }
.pricing-features li i { color: var(--success); margin-right: 8px; }
.btn-pricing { padding: 12px; border-radius: 50px; font-weight: 700; width: 100%; }
.step-number { width: 50px; height: 50px; background: var(--success); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 1.3rem; font-weight: 800; margin: 0 auto 15px; }
.order-form { background: #fff; border-radius: 20px; padding: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #eee; }
.form-control, .form-select { border-radius: 10px; padding: 12px 15px; }
.pack-radio { display: none; }
.pack-label { display: block; border: 2px solid #dee2e6; border-radius: 14px; padding: 20px; cursor: pointer; transition: 0.3s; text-align: center; }
.pack-radio:checked+.pack-label { border-color: var(--success); background: #e8f5e9; }
.summary-box { background: #e8f5e9; border-radius: 16px; padding: 25px; border: 1px solid #c8e6c9; }
.script-area { background: #1e1e1e; color: #d4d4d4; border-radius: 12px; padding: 20px; font-family: monospace; font-size: 0.85rem; max-height: 400px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
.guide-section { background: #f0f7ff; border: 1px solid #b8d4f0; border-radius: 14px; padding: 25px; margin-top: 25px; }
.stat-card { background: #fff; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #eee; }
.stat-card .number { font-size: 2.2rem; font-weight: 800; color: var(--success); }
.status-badge { padding: 5px 12px; border-radius: 50px; font-size: 0.75rem; font-weight: 600; }
.status-pending { background: #fff3cd; color: #856404; }
.status-active { background: #d4edda; color: #155724; }
.status-rejected { background: #f8d7da; color: #721c24; }

/* Footer */
footer.main-footer {
    background: linear-gradient(180deg, #1a2332 0%, #0f1620 100%);
    color: #fff;
    padding: 60px 0 25px;
    margin-top: 60px;
}
footer.main-footer h5 {
    font-weight: 700;
    color: #fff;
    margin-bottom: 20px;
    font-size: 1.1rem;
    border-bottom: 2px solid #28a745;
    padding-bottom: 10px;
    display: inline-block;
}
footer.main-footer a {
    color: #adb5bd;
    text-decoration: none;
    transition: 0.3s;
    display: inline-block;
    padding: 3px 0;
}
footer.main-footer a:hover {
    color: #28a745;
    transform: translateX(3px);
}
footer.main-footer .footer-payment-box {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 18px;
    margin-top: 10px;
    border-left: 4px solid #28a745;
}
footer.main-footer .payment-line {
    display: flex;
    align-items: center;
    padding: 8px 0;
    color: #dee2e6;
}
footer.main-footer .payment-line i {
    color: #28a745;
    margin-right: 10px;
    font-size: 1.2rem;
    width: 24px;
}
footer.main-footer .payment-number {
    font-weight: 700;
    color: #fff;
    font-size: 1.05rem;
    letter-spacing: 1px;
}
footer.main-footer .whatsapp-btn {
    background: #25D366;
    color: white !important;
    padding: 10px 20px;
    border-radius: 50px;
    font-weight: 600;
    margin-top: 15px;
    display: inline-block !important;
}
footer.main-footer .whatsapp-btn:hover {
    background: #128C7E;
    color: white !important;
    transform: translateY(-2px);
}
.footer-bottom-bar {
    border-top: 1px solid rgba(255,255,255,0.1);
    margin-top: 40px;
    padding-top: 20px;
    text-align: center;
    color: #6c757d;
    font-size: 0.85rem;
}
.footer-bottom-bar .brand-badge {
    color: #28a745;
    font-weight: 700;
}

/* Boutons flottants */
.floating-cart {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 65px;
    height: 65px;
    background: linear-gradient(135deg, #28a745, #20c997);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.6rem;
    box-shadow: 0 8px 25px rgba(40, 167, 69, 0.45);
    z-index: 9999;
    text-decoration: none;
    transition: all 0.3s;
    animation: pulse 2s infinite;
}
.floating-cart:hover {
    transform: scale(1.1);
    color: white;
    box-shadow: 0 12px 35px rgba(40, 167, 69, 0.6);
}
.floating-cart .cart-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: red;
    color: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    border: 2px solid white;
}
@keyframes pulse {
    0% { box-shadow: 0 8px 25px rgba(40, 167, 69, 0.45), 0 0 0 0 rgba(40, 167, 69, 0.7); }
    70% { box-shadow: 0 8px 25px rgba(40, 167, 69, 0.45), 0 0 0 15px rgba(40, 167, 69, 0); }
    100% { box-shadow: 0 8px 25px rgba(40, 167, 69, 0.45), 0 0 0 0 rgba(40, 167, 69, 0); }
}

.floating-whatsapp {
    position: fixed;
    bottom: 110px;
    right: 30px;
    width: 60px;
    height: 60px;
    background: #25D366;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.7rem;
    box-shadow: 0 8px 25px rgba(37, 211, 102, 0.45);
    z-index: 9999;
    text-decoration: none;
    transition: all 0.3s;
}
.floating-whatsapp:hover {
    transform: scale(1.1);
    color: white;
}

/* ===== Page Ma Licence - Thème Réseau Pro ===== */
.license-hero {
    background: linear-gradient(135deg, #ffffff 0%, #e8f5e9 50%, #e3f2fd 100%);
    border-radius: 24px;
    padding: 50px 40px;
    text-align: center;
    border: 1px solid #d0e8d5;
    box-shadow: 0 8px 30px rgba(40, 167, 69, 0.08);
    position: relative;
    overflow: hidden;
}
.license-hero::before {
    content: '';
    position: absolute;
    top: -50px;
    right: -50px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(40,167,69,0.1) 0%, transparent 70%);
    border-radius: 50%;
}
.license-hero::after {
    content: '';
    position: absolute;
    bottom: -50px;
    left: -50px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(13,110,253,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.license-icon-wrap {
    width: 100px;
    height: 100px;
    background: white;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 25px rgba(40, 167, 69, 0.2);
    margin-bottom: 20px;
    position: relative;
    z-index: 2;
}
.license-icon-wrap i {
    font-size: 2.8rem;
    background: linear-gradient(135deg, #28a745, #0d6efd);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.license-hero h2 {
    color: #212529;
    font-weight: 800;
    position: relative;
    z-index: 2;
}
.license-hero p {
    color: #6c757d;
    position: relative;
    z-index: 2;
}
.license-form-wrap {
    position: relative;
    z-index: 2;
    max-width: 500px;
    margin: 25px auto 0;
}
.license-input {
    border-radius: 50px !important;
    padding: 16px 25px !important;
    font-size: 1.05rem !important;
    text-align: center !important;
    border: 2px solid #d0e8d5 !important;
    background: white !important;
    color: #212529 !important;
    font-weight: 600;
    letter-spacing: 1px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    transition: all 0.3s;
}
.license-input:focus {
    border-color: #28a745 !important;
    box-shadow: 0 0 0 0.25rem rgba(40, 167, 69, 0.15) !important;
    outline: none;
}
.license-input::placeholder {
    color: #adb5bd;
    font-weight: 400;
    letter-spacing: 0;
}
.btn-license-unlock {
    background: linear-gradient(135deg, #28a745, #20c997);
    border: none;
    color: white;
    border-radius: 50px;
    padding: 15px 45px;
    font-weight: 700;
    font-size: 1.05rem;
    margin-top: 18px;
    box-shadow: 0 6px 20px rgba(40, 167, 69, 0.35);
    transition: all 0.3s;
}
.btn-license-unlock:hover {
    background: linear-gradient(135deg, #218838, #17a2b8);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 10px 30px rgba(40, 167, 69, 0.5);
}
.info-network-card {
    background: white;
    border-radius: 20px;
    padding: 35px;
    margin-top: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    border: 1px solid #e9ecef;
    border-left: 5px solid #28a745;
}
.step-list-network {
    list-style: none;
    padding: 0;
    margin: 20px 0;
    counter-reset: step-counter;
}
.step-list-network li {
    padding: 12px 0 12px 45px;
    position: relative;
    color: #495057;
    line-height: 1.6;
    border-bottom: 1px dashed #e9ecef;
}
.step-list-network li:last-child {
    border-bottom: none;
}
.step-list-network li::before {
    content: counter(step-counter);
    counter-increment: step-counter;
    position: absolute;
    left: 0;
    top: 12px;
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #28a745, #0d6efd);
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
}
"""

def render_page(body_html, title="KETRIKA MIKROTIK", extra_script=""):
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - KETRIKA MIKROTIK</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <style>{CSS_STYLES}</style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm sticky-top">
        <div class="container">
            <a class="navbar-brand" href="/"><i class="fas fa-network-wired text-success me-2"></i>KETRIKA <span class="text-success">MIKROTIK</span></a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain"><span class="navbar-toggler-icon"></span></button>
            <div class="collapse navbar-collapse" id="navMain">
                <ul class="navbar-nav ms-auto align-items-lg-center">
                    <li class="nav-item"><a class="nav-link fw-semibold" href="/#pricing">Tarifs</a></li>
                    <li class="nav-item"><a class="nav-link fw-semibold" href="/#how">Comment ça marche</a></li>
                    <li class="nav-item"><a class="nav-link fw-semibold" href="/#faq">FAQ</a></li>
                    <li class="nav-item"><a class="nav-link fw-semibold text-primary" href="/my-license"><i class="fas fa-key me-1"></i>Ma Licence</a></li>
                    <li class="nav-item ms-lg-3"><a class="btn btn-success btn-sm px-4 rounded-pill fw-bold text-white" href="/order"><i class="fas fa-shopping-cart me-1"></i> Commander</a></li>
                </ul>
            </div>
        </div>
    </nav>
    {body_html}
    
    <!-- FOOTER RICHE -->
    <footer class="main-footer">
        <div class="container">
            <div class="row g-4">
                <div class="col-lg-4 col-md-6">
                    <h5><i class="fas fa-network-wired me-2"></i>KETRIKA MIKROTIK</h5>
                    <p style="color:#adb5bd;line-height:1.7;margin-top:15px">
                        Plateforme professionnelle de vente de configurations automatiques pour routeurs MikroTik RouterOS v7. 
                        Scripts prêts à l'emploi, VPN Cloudflare WARP illimité et Hotspot WiFi Zone.
                    </p>
                    <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="whatsapp-btn">
                        <i class="fab fa-whatsapp me-2"></i>Contactez-nous
                    </a>
                </div>
                
                <div class="col-lg-3 col-md-6">
                    <h5><i class="fas fa-link me-2"></i>Liens rapides</h5>
                    <div class="d-flex flex-column">
                        <a href="/"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Accueil</a>
                        <a href="/#pricing"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Tarifs</a>
                        <a href="/#how"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Comment ça marche</a>
                        <a href="/#faq"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>FAQ</a>
                        <a href="/order"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Commander</a>
                        <a href="/my-license"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Ma Licence</a>
                    </div>
                </div>
                
                <div class="col-lg-5 col-md-12">
                    <h5><i class="fas fa-credit-card me-2"></i>Modes de paiement</h5>
                    <div class="footer-payment-box">
                        <div class="payment-line">
                            <i class="fas fa-mobile-alt"></i>
                            <div>
                                <div style="font-size:0.85rem;color:#adb5bd">MVola</div>
                                <div class="payment-number">{MVOLA_NUMBER}</div>
                            </div>
                        </div>
                        <div class="payment-line">
                            <i class="fas fa-mobile-alt" style="color:#ff6b1a"></i>
                            <div>
                                <div style="font-size:0.85rem;color:#adb5bd">Orange Money</div>
                                <div class="payment-number">{ORANGE_NUMBER}</div>
                            </div>
                        </div>
                        <div class="payment-line">
                            <i class="fab fa-whatsapp" style="color:#25D366"></i>
                            <div>
                                <div style="font-size:0.85rem;color:#adb5bd">WhatsApp Support</div>
                                <div class="payment-number">{WHATSAPP_DISPLAY}</div>
                            </div>
                        </div>
                        <hr style="border-color:rgba(255,255,255,0.1);margin:12px 0">
                        <div class="text-center" style="color:#dee2e6">
                            <i class="fas fa-user-check text-success me-1"></i>
                            <span>Au nom de <strong style="color:#fff">{PAYMENT_NAME}</strong></span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer-bottom-bar">
                <p class="mb-1">
                    &copy; 2026 <span class="brand-badge">KETRIKA MIKROTIK</span> — Tous droits réservés
                </p>
                <p class="mb-0" style="font-size:0.8rem;color:#6c757d">
                    <i class="fas fa-shield-alt me-1"></i>Plateforme sécurisée
                    &nbsp;•&nbsp;
                    <i class="fas fa-lock me-1"></i>Paiement mobile money
                    &nbsp;•&nbsp;
                    <i class="fas fa-map-marker-alt me-1"></i>Madagascar
                </p>
            </div>
        </div>
    </footer>
    
    <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="floating-whatsapp" title="Contactez-nous sur WhatsApp">
        <i class="fab fa-whatsapp"></i>
    </a>
    
    <a href="/order" class="floating-cart" title="Commander maintenant">
        <i class="fas fa-shopping-cart"></i>
        <span class="cart-badge">3</span>
    </a>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {extra_script}
</body>
</html>"""


# ===================== ACCUEIL =====================
HOME_BODY = """
<section class="hero-section">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-7">
                <h1 class="hero-title">Configurez votre <span>MikroTik</span> en 1 clic</h1>
                <p class="hero-subtitle">Scripts professionnels RouterOS v7 prêts à l'emploi. VPN illimité, Hotspot WiFi Zone, protection réseau avancée.</p>
                <a href="/order" class="btn btn-cta"><i class="fas fa-bolt me-2"></i>Commander maintenant</a>
                <a href="/my-license" class="btn btn-outline-primary ms-2 rounded-pill px-4 py-3"><i class="fas fa-key me-2"></i>J'ai déjà une clé/référence</a>
                <br><span class="badge-compat"><i class="fas fa-check-circle me-1"></i> 100% Compatible RouterOS v7</span>
            </div>
            <div class="col-lg-5 d-none d-lg-block text-center">
                <div style="font-size: 10rem; color: #28a745;"><i class="fas fa-server"></i></div>
            </div>
        </div>
    </div>
</section>

<section class="py-5 bg-white">
    <div class="container">
        <h2 class="section-title text-center mb-5">Pourquoi nous choisir ?</h2>
        <div class="row g-4">
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-bolt"></i></div><h5 class="text-center">Configuration Rapide</h5><p class="text-muted text-center mb-0">Copiez-collez le script généré, configuration automatique en 30 secondes.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-shield-halved"></i></div><h5 class="text-center">VPN Cloudflare WARP</h5><p class="text-muted text-center mb-0">Naviguez anonymement et sans baisse de débit via les tunnels sécurisés.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-router"></i></div><h5 class="text-center">Tous modèles compatibles</h5><p class="text-muted text-center mb-0">Détection intelligente pour configurations WiFi 5 et WiFi 6.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fab fa-whatsapp"></i></div><h5 class="text-center">Assistance 24/7</h5><p class="text-muted text-center mb-0">Assistance et livraison de licence directement par WhatsApp.</p></div></div>
        </div>
    </div>
</section>

<section class="py-5" id="pricing">
    <div class="container">
        <h2 class="section-title text-center">Nos Tarifs</h2>
        <p class="text-center text-muted mb-5">Sélectionnez le pack dont vous avez besoin pour votre routeur</p>
        <div class="row g-4 justify-content-center">
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card">
                    <div class="pricing-name fw-bold">PACK ESSENTIEL</div>
                    <div class="pricing-price">30 000 <small style="font-size:1.2rem">Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Configuration complète du Bridge</li>
                        <li><i class="fas fa-check"></i> Wi-Fi Sécurisé (WPA2-PSK)</li>
                        <li><i class="fas fa-check"></i> DNS Chiffré Cloudflare DoH</li>
                        <li><i class="fas fa-check"></i> Masquage TTL (Anti-partage)</li>
                        <li><i class="fas fa-check"></i> Limitation QoS Simple</li>
                    </ul>
                    <a href="/order?pack=standard" class="btn btn-outline-success btn-pricing">Commander</a>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card popular">
                    <div class="pricing-badge">POPULAIRE</div>
                    <div class="pricing-name fw-bold mt-2">PACK SÉCURITÉ VPN</div>
                    <div class="pricing-price">50 000 <small style="font-size:1.2rem">Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Tout le Pack Essentiel +</li>
                        <li><i class="fas fa-check"></i> VPN Cloudflare WARP illimité</li>
                        <li><i class="fas fa-check"></i> Contournement DPI et FAI</li>
                        <li><i class="fas fa-check"></i> MSS Clamping automatique</li>
                        <li><i class="fas fa-check"></i> Guide Réseau Avancé (PDF)</li>
                    </ul>
                    <a href="/order?pack=warp" class="btn btn-success text-white btn-pricing">Commander</a>
                </div>
            </div>
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card">
                    <div class="pricing-badge pro">PRO</div>
                    <div class="pricing-name fw-bold mt-2">PACK BUSINESS HOTSPOT</div>
                    <div class="pricing-price">80 000 <small style="font-size:1.2rem">Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Tout le Pack Sécurité VPN +</li>
                        <li><i class="fas fa-check"></i> Portail Captif WiFi Zone</li>
                        <li><i class="fas fa-check"></i> Serveur PPPoE intégré</li>
                        <li><i class="fas fa-check"></i> 10 Vouchers de test inclus</li>
                        <li><i class="fas fa-check"></i> Pare-feu Anti-Torrent</li>
                    </ul>
                    <a href="/order?pack=hotspot" class="btn btn-primary btn-pricing">Commander</a>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="py-5 bg-white" id="how">
    <div class="container">
        <h2 class="section-title text-center mb-5">Comment ça marche ?</h2>
        <div class="row g-4">
            <div class="col-md-3 text-center">
                <div class="step-number">1</div>
                <h5>Commandez</h5>
                <p class="text-muted">Choisissez un pack et personnalisez votre configuration.</p>
            </div>
            <div class="col-md-3 text-center">
                <div class="step-number">2</div>
                <h5>Payez</h5>
                <p class="text-muted">MVola ou Orange Money, envoyez la preuve.</p>
            </div>
            <div class="col-md-3 text-center">
                <div class="step-number">3</div>
                <h5>Recevez la clé</h5>
                <p class="text-muted">Votre clé de licence ou ID de commande est validé en moins de 10 min.</p>
            </div>
            <div class="col-md-3 text-center">
                <div class="step-number">4</div>
                <h5>Récupérez le script</h5>
                <p class="text-muted">Allez sur <strong>"Ma Licence"</strong>, entrez votre référence et copiez le script.</p>
            </div>
        </div>
        <div class="text-center mt-5">
            <a href="/my-license" class="btn btn-outline-success btn-lg rounded-pill px-5"><i class="fas fa-key me-2"></i>Récupérer mon script de configuration</a>
        </div>
    </div>
</section>

<section class="py-5" id="faq">
    <div class="container" style="max-width: 800px;">
        <h2 class="section-title text-center mb-5">Foire Aux Questions (FAQ)</h2>
        <div class="accordion" id="faqAcc">
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f1">Est-ce que le VPN ralentit le débit internet ?</button></h2>
                <div id="f1" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Non. Cloudflare utilise un protocole très optimisé (WireGuard) qui préserve l'intégralité de votre bande passante.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f2">Comment je reçois ma clé de licence ?</button></h2>
                <div id="f2" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Après validation de votre paiement (max 10 minutes), vous recevez votre clé sur WhatsApp. De plus, votre numéro de commande <strong>KTR-...</strong> fonctionne également pour récupérer votre configuration sur la page <strong>Ma Licence</strong>.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f3">Est-ce compatible avec mon modèle de routeur ?</button></h2>
                <div id="f3" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Oui ! Notre système détecte automatiquement votre modèle : hAP lite, hAP ac2, hAP ac3, hAP ax2, hAP ax3, hEX, RB5009, CCR, L009, etc. Le script généré est parfaitement adapté à votre WiFi 5 ou WiFi 6.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f4">Puis-je utiliser une licence sur plusieurs routeurs ?</button></h2>
                <div id="f4" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Non. Chaque licence est valable pour un seul routeur MikroTik. Pour équiper plusieurs routeurs, vous devrez commander une licence par routeur.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f5">Quels sont les modes de paiement acceptés ?</button></h2>
                <div id="f5" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Nous acceptons <strong>MVola</strong> et <strong>Orange Money</strong>. Envoyez le montant au nom de JEAN ERIC et joignez la capture d'écran comme preuve de paiement.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded">
                <h2 class="accordion-header"><button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#f6">Que faire si le script ne fonctionne pas ?</button></h2>
                <div id="f6" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Contactez immédiatement notre support WhatsApp en cliquant sur le bouton vert en bas de la page. Notre équipe technique vous assistera pour vérifier votre RouterOS (v7 requis) et vous aider à finaliser l'installation.</div></div>
            </div>
        </div>
    </div>
</section>
"""

@app.route('/')
def home():
    try:
        return render_page(HOME_BODY, title="Accueil")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur Serveur</h1><pre>{e}</pre>", 500


# ===================== MA LICENCE =====================
@app.route('/my-license', methods=['GET', 'POST'])
def my_license():
    try:
        error = ""
        saved_key = ""
        if request.method == 'POST':
            raw_key = request.form.get('license_key') or ''
            key = raw_key.strip().upper().replace(' ', '').replace('\t', '').replace('\n', '')
            saved_key = key
            
            if not key:
                error = '<div class="alert alert-warning mt-3"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez entrer une référence de commande ou clé de licence.</div>'
            else:
                # Recherche intelligente : Fonctionne avec la clé de licence (LIC-) OU le numéro de commande (KTR-)
                order_obj = Order.query.filter(
                    (db.func.upper(Order.license_key) == key) | 
                    (db.func.upper(Order.order_id) == key)
                ).first()
                
                if order_obj:
                    return redirect(url_for('license_page', key=order_obj.license_key))
                else:
                    error = f'''<div class="alert alert-danger mt-3">
                        <i class="fas fa-times-circle me-2"></i><strong>Référence ou Clé introuvable.</strong><br>
                        <small>Vérifiez que vous avez bien copié votre clé (ex: <code>LIC-XXXX</code>) ou votre numéro de commande (ex: <code>KTR-3231065F</code>).</small>
                    </div>'''

        body = f"""
<section class="py-5">
    <div class="container" style="max-width: 750px">
        <div class="license-hero">
            <div class="license-icon-wrap">
                <i class="fas fa-key"></i>
            </div>
            <h2>Accédez à votre configuration</h2>
            <p class="fs-6 mb-0">Entrez votre Clé de Licence (<code>LIC-...</code>) ou votre Référence Commande (<code>KTR-...</code>)</p>
            
            <div class="license-form-wrap">
                <form method="POST">
                    <input type="text" 
                           name="license_key" 
                           class="form-control license-input" 
                           placeholder="KTR-XXXXXXXX ou LIC-XXXXXXXX" 
                           value="{saved_key}"
                           required 
                           autocomplete="off">
                    <button type="submit" class="btn btn-license-unlock">
                        <i class="fas fa-unlock me-2"></i>Accéder à mon script
                    </button>
                </form>
                {error}
            </div>
        </div>
        
        <div class="info-network-card">
            <h5 class="fw-bold mb-3" style="color:#0d6efd">
                <i class="fas fa-network-wired me-2"></i>Comment récupérer ma configuration ?
            </h5>
            <ol class="step-list-network">
                <li><strong>Commandez</strong> votre pack et payez via MVola ou Orange Money</li>
                <li><strong>Téléversez</strong> la capture d'écran de votre paiement mobile</li>
                <li>Notre équipe <strong>valide</strong> l'activation de votre script en moins de 10 min</li>
                <li>Saisissez ci-dessus votre numéro de commande <strong>KTR-...</strong> ou votre clé <strong>LIC-...</strong> reçue sur WhatsApp</li>
                <li><strong>Copiez</strong> le script généré et collez-le directement dans Winbox</li>
            </ol>
            
            <hr class="my-4">
            
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="d-flex align-items-center p-3 rounded-3" style="background:#e8f5e9">
                        <i class="fas fa-shopping-cart text-success fs-3 me-3"></i>
                        <div>
                            <div class="fw-bold">Pas encore de commande ?</div>
                            <a href="/order" class="text-success fw-semibold" style="text-decoration:none">Faire une commande →</a>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="d-flex align-items-center p-3 rounded-3" style="background:#e3f2fd">
                        <i class="fab fa-whatsapp text-success fs-3 me-3"></i>
                        <div>
                            <div class="fw-bold">Besoin d'aide ?</div>
                            <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="text-primary fw-semibold" style="text-decoration:none">Support WhatsApp →</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>
"""
        return render_page(body, title="Ma Licence")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ===================== COMMANDES =====================
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

        preselect = request.args.get('pack', 'standard')
        options_html = '<option value="">-- Sélectionnez votre modèle --</option>'
        for key, info in MIKROTIK_MODELS.items():
            options_html += f'<option value="{key}">{info["name"]}</option>'
        options_html += '<option value="other">Autre / Modèle non listé</option>'

        c1 = 'checked' if preselect == 'standard' else ''
        c2 = 'checked' if preselect == 'warp' else ''
        c3 = 'checked' if preselect == 'hotspot' else ''

        body = f"""
<section class="py-5">
    <div class="container" style="max-width:850px">
        <h2 class="section-title text-center mb-4"><i class="fas fa-shopping-cart text-success me-2"></i>Commande</h2>
        <form class="order-form" method="POST" action="/order">
            <div class="mb-3"><label class="form-label">Nom complet du client</label><input type="text" name="client_name" class="form-control" required placeholder="Ex: Jean Luc"></div>
            <div class="mb-3"><label class="form-label"><i class="fab fa-whatsapp text-success"></i> Numéro WhatsApp</label><input type="text" name="whatsapp" class="form-control" placeholder="+261 34 XX XXX XX" required></div>
            <div class="mb-4">
                <label class="form-label">Type de Pack</label>
                <div class="row g-3">
                    <div class="col-md-4"><input type="radio" name="plan_type" value="standard" id="p1" class="pack-radio" {c1}><label class="pack-label" for="p1"><h6>Pack Essentiel</h6><div class="price">30 000 Ar</div></label></div>
                    <div class="col-md-4"><input type="radio" name="plan_type" value="warp" id="p2" class="pack-radio" {c2}><label class="pack-label" for="p2"><h6>Pack Sécurité VPN</h6><div class="price">50 000 Ar</div></label></div>
                    <div class="col-md-4"><input type="radio" name="plan_type" value="hotspot" id="p3" class="pack-radio" {c3}><label class="pack-label" for="p3"><h6>Pack Business</h6><div class="price">80 000 Ar</div></label></div>
                </div>
            </div>
            <div class="mb-3"><label class="form-label">Modèle de routeur MikroTik</label><select name="mikrotik_model" class="form-select" id="modelSelect" required>{options_html}</select></div>
            <div class="mb-3" id="otherModelDiv" style="display:none"><label class="form-label">Indiquez la référence exacte</label><input type="text" name="other_model" class="form-control" placeholder="Ex: RB1100AHx4"></div>
            <div class="row g-3 mb-3">
                <div class="col-md-6"><label class="form-label">SSID (Nom Wi-Fi)</label><input type="text" name="ssid" class="form-control" value="KETRIKA-WiFi"></div>
                <div class="col-md-6"><label class="form-label">Clé de sécurité Wi-Fi (min 8 car.)</label><input type="text" name="wifi_password" class="form-control" minlength="8" value="ketrika2024"></div>
            </div>
            <div class="row g-3 mb-3">
                <div class="col-md-6"><label class="form-label">Interface WAN</label><input type="text" name="wan_interface" class="form-control" value="ether1"></div>
                <div class="col-md-6"><label class="form-label">IP LAN &amp; DHCP</label><input type="text" class="form-control" value="Génération d'IP unique active" disabled></div>
            </div>
            <div class="row g-3 mb-3">
                <div class="col-md-4">
                    <label class="form-label">Valeur du TTL</label>
                    <select name="ttl_value" class="form-select">
                        <option value="64" selected>64 (Masquage)</option>
                        <option value="65">65</option>
                        <option value="128">128</option>
                        <option value="0">Désactivé</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Limite Download</label>
                    <select name="dl_limit" class="form-select">
                        <option value="0">Illimité</option><option value="5M">5 Mbps</option><option value="10M">10 Mbps</option><option value="20M">20 Mbps</option><option value="50M">50 Mbps</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Limite Upload</label>
                    <select name="ul_limit" class="form-select">
                        <option value="0">Illimité</option><option value="2M">2 Mbps</option><option value="5M">5 Mbps</option><option value="10M">10 Mbps</option><option value="20M">20 Mbps</option>
                    </select>
                </div>
            </div>
            <div id="hotspotOptions" style="display:none;background:#f0f7ff;padding:20px;border-radius:12px" class="mb-3">
                <h6 class="fw-bold text-primary"><i class="fas fa-wifi me-1"></i> Options Business Hotspot</h6>
                <div class="form-check mb-2"><input type="checkbox" name="pppoe_enabled" class="form-check-input" id="pppoeCheck" value="1"><label class="form-check-label" for="pppoeCheck">Activer serveur PPPoE</label></div>
                <div class="form-check"><input type="checkbox" name="voucher_enabled" class="form-check-input" id="voucherCheck" value="1" checked><label class="form-check-label" for="voucherCheck">Générer 10 codes d'accès Wi-Fi</label></div>
            </div>
            <button type="submit" class="btn btn-cta w-100"><i class="fas fa-check me-2"></i>Valider la configuration</button>
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
(function(){
    var s=document.querySelector('input[name=plan_type]:checked');
    if(s&&s.value==='hotspot')document.getElementById('hotspotOptions').style.display='block';
})();
</script>
"""
        return render_page(body, title="Commander", extra_script=js)
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur formulaire</h1><pre>{e}</pre>", 500


# ===================== PAIEMENTS =====================
@app.route('/pay/<order_id>', methods=['GET', 'POST'])
def pay(order_id):
    try:
        if len(order_id) < 5 or '.' in order_id:
            abort(404)

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
    <div class="container text-center" style="max-width:650px">
        <div class="order-form">
            <div class="text-success mb-3" style="font-size: 5rem;"><i class="fas fa-check-circle"></i></div>
            <h3 class="fw-bold">Preuve reçue !</h3>
            <p class="text-muted fs-5">Votre paiement est en cours de vérification.</p>
            <hr>
            <div class="alert alert-info text-start">
                <h6 class="fw-bold"><i class="fas fa-clock me-2"></i>Prochaines étapes :</h6>
                <ol class="mb-0">
                    <li>Notre équipe vérifie votre paiement (max 10 minutes)</li>
                    <li>Saisissez votre ID de commande <strong>{order_id}</strong> pour voir le script dès validation.</li>
                </ol>
            </div>
            <p class="mt-3"><strong>Référence de commande :</strong> <code>{order_id}</code></p>
            <div class="d-grid gap-2 mt-4">
                <a href="/my-license" class="btn btn-success text-white rounded-pill py-3"><i class="fas fa-key me-2"></i>Accéder à "Ma Licence"</a>
                <a href="/" class="btn btn-outline-secondary rounded-pill">Retour à l'accueil</a>
            </div>
        </div>
    </div>
</section>
"""
            return render_page(body, title="Preuve reçue")

        plan = safe_get(order_obj, 'plan_type', 'standard')
        price_map = {'standard': ('30 000 Ar', 'Pack Essentiel'), 'warp': ('50 000 Ar', 'Pack Sécurité VPN'), 'hotspot': ('80 000 Ar', 'Pack Business')}
        price, name = price_map.get(plan, ('30 000 Ar', 'Pack Essentiel'))

        body = f"""
<section class="py-5">
    <div class="container" style="max-width:700px">
        <div class="order-form">
            <h3 class="text-center fw-bold mb-4"><i class="fas fa-mobile text-success me-2"></i>Instructions de Paiement</h3>
            <div class="summary-box mb-4">
                <p class="mb-1"><strong>Référence :</strong> {safe_get(order_obj, 'order_id')}</p>
                <p class="mb-1"><strong>Formule :</strong> {name}</p>
                <p class="mb-0"><strong>Montant :</strong> <span class="fw-bold text-success fs-4">{price}</span></p>
            </div>
            <div class="alert alert-warning">
                <h6 class="fw-bold mb-3"><i class="fas fa-mobile-alt me-2"></i>Envoyez <strong>{price}</strong> sur un de ces numéros :</h6>
                <div class="p-3 mb-2 rounded" style="background:white;border-left:4px solid #28a745">
                    <strong>MVola / WhatsApp :</strong><br>
                    <span style="font-size:1.3rem;letter-spacing:2px;font-weight:700;color:#28a745">{MVOLA_NUMBER}</span>
                </div>
                <div class="p-3 mb-2 rounded" style="background:white;border-left:4px solid #ff6b1a">
                    <strong>Orange Money :</strong><br>
                    <span style="font-size:1.3rem;letter-spacing:2px;font-weight:700;color:#ff6b1a">{ORANGE_NUMBER}</span>
                </div>
                <div class="text-center mt-3">
                    <i class="fas fa-user-check me-1"></i>Au nom de <strong>{PAYMENT_NAME}</strong>
                </div>
            </div>
            <form method="POST" action="/pay/{order_id}" enctype="multipart/form-data">
                <div class="mb-3"><label class="form-label fw-bold">Capture d'écran de la preuve</label><input type="file" name="payment_proof" class="form-control" accept="image/*" required></div>
                <div class="mb-3"><label class="form-label fw-bold">Rappel de votre numéro WhatsApp</label><input type="text" name="whatsapp_confirm" class="form-control" value="{safe_get(order_obj, 'whatsapp_number')}" required></div>
                <button type="submit" class="btn btn-cta w-100">Transmettre la preuve</button>
            </form>
        </div>
    </div>
</section>
"""
        return render_page(body, title="Paiement")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur paiement</h1><pre>{e}</pre>", 500


# ===================== SCRIPT & LICENCE =====================
@app.route('/license/<key>')
def license_page(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            # Tente de chercher par ID de commande au cas où
            order_obj = Order.query.filter_by(order_id=key).first()
            if not order_obj:
                abort(404)

        if safe_get(order_obj, 'status') != 'active':
            ref = safe_get(order_obj, 'order_id')
            body = f"""
<section class="py-5 text-center">
    <div class="container" style="max-width: 650px">
        <div class="order-form">
            <div style="font-size: 4rem; color: #ffc107;" class="mb-3"><i class="fas fa-clock"></i></div>
            <h4 class="fw-bold">Configuration en attente</h4>
            <p class="text-muted">La commande <code>{ref}</code> n'est pas encore activée.</p>
            <div class="alert alert-info mt-4 text-start">
                <strong>Que faire ?</strong>
                <ul class="mb-0">
                    <li>Veuillez patienter pendant la validation de votre preuve (max 10 minutes).</li>
                    <li>Dès que l'administrateur valide, votre script apparaîtra ici instantanément.</li>
                </ul>
            </div>
            <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="btn btn-success text-white rounded-pill px-4 mt-3">
                <i class="fab fa-whatsapp me-2"></i>Contacter JEAN ERIC
            </a>
        </div>
    </div>
</section>
"""
            return render_page(body, title="Licence en attente")

        from warp_api import generate_script
        script = generate_script(order_obj)
        esc_script = script.replace('<', '&lt;').replace('>', '&gt;')

        body = f"""
<section class="py-5">
    <div class="container" style="max-width: 900px">
        <div class="order-form">
            <div class="text-center mb-4">
                <div style="font-size: 3rem; color: #28a745;"><i class="fas fa-check-circle"></i></div>
                <h4 class="fw-bold">Configuration Activée !</h4>
                <span class="badge bg-success py-2 px-3">{safe_get(order_obj, 'license_key')}</span>
            </div>
            <div class="summary-box mb-4">
                <p class="mb-1"><strong>Client :</strong> {safe_get(order_obj, 'client_name')}</p>
                <p class="mb-1"><strong>Modèle :</strong> {safe_get(order_obj, 'mikrotik_model')}</p>
                <p class="mb-1"><strong>SSID WiFi :</strong> {safe_get(order_obj, 'ssid')}</p>
                <p class="mb-0"><strong>IP LAN :</strong> {safe_get(order_obj, 'lan_gateway')}</p>
            </div>
            <h6 class="fw-bold">Votre Script de Configuration RouterOS v7 :</h6>
            <div class="script-area" id="scrText">{esc_script}</div>
            <div class="row g-3 mt-3">
                <div class="col-6"><button class="btn btn-success w-100 text-white" id="cpBtn" onclick="cp()"><i class="fas fa-copy me-2"></i>Copier le script</button></div>
                <div class="col-6"><a href="/download/{safe_get(order_obj, 'license_key')}" class="btn btn-outline-primary w-100"><i class="fas fa-download me-2"></i>Télécharger (.rsc)</a></div>
            </div>
            <div class="alert alert-info mt-4">
                <h6 class="fw-bold"><i class="fas fa-book me-1"></i>Procédure d'installation :</h6>
                <ol class="mb-0">
                    <li>Ouvrez <strong>Winbox</strong> et connectez-vous à votre routeur</li>
                    <li>Ouvrez le menu <strong>New Terminal</strong></li>
                    <li>Cliquez sur <strong>"Copier le script"</strong> ci-dessus</li>
                    <li>Collez (Ctrl+V ou clic droit → Paste) dans le terminal</li>
                    <li>Le routeur applique la configuration puis redémarre tout seul</li>
                </ol>
            </div>
        </div>
    </div>
</section>
"""
        js = """
<script>
function cp(){
    var t=document.getElementById('scrText').innerText;
    navigator.clipboard.writeText(t).then(function(){
        var b=document.getElementById('cpBtn');
        b.innerHTML='<i class="fas fa-check me-2"></i>Script copié !';
        setTimeout(function(){ b.innerHTML='<i class="fas fa-copy me-2"></i>Copier le script'; }, 2000);
    });
}
</script>
"""
        return render_page(body, title="Ma Licence Active", extra_script=js)
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur licence</h1><pre>{e}</pre>", 500


@app.route('/download/<key>')
def download_script(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            order_obj = Order.query.filter_by(order_id=key).first()
            if not order_obj:
                abort(404)
                
        if safe_get(order_obj, 'status') != 'active':
            abort(403)

        from warp_api import generate_script
        script = generate_script(order_obj)
        fname = f"ketrika_{key[:10]}.rsc"
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(script)
        return send_file(fpath, as_attachment=True, download_name=fname)
    except HTTPException as e:
        raise e
    except Exception as e:
        return str(e), 500


# ===================== SÉCURITÉ ADMIN =====================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    try:
        if session.get('admin_logged'):
            return redirect(url_for('admin_dashboard'))
        err = ""
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['admin_logged'] = True
                return redirect(url_for('admin_dashboard'))
            err = '<div class="alert alert-danger">Mot de passe invalide</div>'

        body = f"""
<div class="d-flex align-items-center justify-content-center" style="min-height:75vh">
    <div class="order-form text-center" style="max-width:400px; width:100%;">
        <h3>Administration</h3>
        {err}
        <form method="POST">
            <input type="password" name="password" class="form-control mb-3 text-center" placeholder="Clé Secrète" required>
            <button class="btn btn-success w-100 text-white">Se connecter</button>
        </form>
    </div>
</div>
"""
        return render_page(body, title="Login Admin")
    except HTTPException as e:
        raise e
    except Exception as e:
        return str(e), 500


@app.route('/admin/dashboard')
def admin_dashboard():
    try:
        if not session.get('admin_logged'):
            return redirect(url_for('admin_login'))

        orders = Order.query.order_by(Order.created_at.desc()).all()
        total = len(orders)
        pending = sum(1 for o in orders if safe_get(o, 'status') == 'pending')
        active = sum(1 for o in orders if safe_get(o, 'status') == 'active')

        rows = ""
        for o in orders:
            stat = safe_get(o, 'status')
            p_type = safe_get(o, 'plan_type')

            if stat == 'pending':
                badg = '<span class="status-badge status-pending">En attente</span>'
                act = f"""
                <form method="POST" action="/admin/validate/{o.order_id}" style="display:inline"><button class="btn btn-sm btn-success text-white"><i class="fas fa-check"></i></button></form>
                <form method="POST" action="/admin/reject/{o.order_id}" style="display:inline"><button class="btn btn-sm btn-danger"><i class="fas fa-times"></i></button></form>
                """
            elif stat == 'active':
                badg = '<span class="status-badge status-active">Validé</span>'
                act = f'<a href="/license/{o.license_key}" target="_blank" class="btn btn-sm btn-outline-success"><i class="fas fa-eye"></i></a>'
            else:
                badg = '<span class="status-badge status-rejected">Refusé</span>'
                act = ""

            proof_btn = "-"
            if safe_get(o, 'payment_proof'):
                proof_btn = f'<a href="/admin/proof/{o.order_id}" target="_blank" class="btn btn-sm btn-light"><i class="fas fa-image"></i></a>'

            rows += f"""
<tr>
    <td><small><strong>{safe_get(o, 'order_id')}</strong></small></td>
    <td>{safe_get(o, 'client_name')}</td>
    <td><a href="https://wa.me/{safe_get(o, 'whatsapp_number').replace(' ','')}" target="_blank">{safe_get(o, 'whatsapp_number')}</a></td>
    <td>{p_type.upper()}</td>
    <td><small class="text-muted">{safe_get(o, 'license_key', '')[:20]}...</small></td>
    <td>{proof_btn}</td>
    <td>{badg}</td>
    <td>{act}</td>
</tr>
"""
        if not rows:
            rows = '<tr><td colspan="8" class="text-center text-muted py-4">Aucune commande</td></tr>'

        body = f"""
<div class="bg-dark py-3 mb-4">
    <div class="container d-flex justify-content-between align-items-center">
        <h5 class="text-white mb-0">CONSOLE KETRIKA ADMIN</h5>
        <a href="/admin/logout" class="btn btn-sm btn-outline-light">Déconnexion</a>
    </div>
</div>
<section class="container pb-5">
    <div class="row g-3 mb-4 text-center">
        <div class="col-4"><div class="stat-card"><h5>Total</h5><div class="number">{total}</div></div></div>
        <div class="col-4"><div class="stat-card"><h5>En attente</h5><div class="number text-warning">{pending}</div></div></div>
        <div class="col-4"><div class="stat-card"><h5>Actifs</h5><div class="number text-success">{active}</div></div></div>
    </div>
    <div class="card shadow-sm border-0 rounded-4">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table mb-0 align-middle">
                    <thead class="table-light">
                        <tr><th>Réf (KTR-)</th><th>Client</th><th>WhatsApp</th><th>Pack</th><th>Clé Licence</th><th>Preuve</th><th>Statut</th><th>Action</th></tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>
    </div>
</section>
"""
        return render_page(body, title="Console Admin")
    except HTTPException as e:
        raise e
    except Exception as e:
        return str(e), 500


@app.route('/admin/validate/<order_id>', methods=['POST'])
def admin_validate(order_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    o = Order.query.filter_by(order_id=order_id).first()
    if o:
        o.status = 'active'
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject/<order_id>', methods=['POST'])
def admin_reject(order_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    o = Order.query.filter_by(order_id=order_id).first()
    if o:
        o.status = 'rejected'
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/proof/<order_id>')
def admin_proof(order_id):
    if not session.get('admin_logged'):
        return redirect(url_for('admin_login'))
    o = Order.query.filter_by(order_id=order_id).first()
    if not o or not o.payment_proof:
        abort(404)
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], o.payment_proof))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('admin_login'))


@app.route('/health')
def health():
    return {"status": "healthy"}, 200


def secure_filename(filename):
    for c in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>', ' ']:
        filename = filename.replace(c, '_')
    return filename


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
