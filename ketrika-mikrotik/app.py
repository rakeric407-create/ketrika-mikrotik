Voici le fichier **`app.py` COMPLET et NETTOYÉ**. 

Le mot **"Starlink"** a été **100% supprimé et éradiqué** de toutes les pages (Accueil, Tarifs, Formulaire de commande, Page de Licence, Guide, etc.) et remplacé par des termes professionnels et discrets comme **"FAI / Opérateurs Haut Débit"**, **"Modem Source"**, ou **"Réseau Satellite/4G"**.

---

### 📄 FICHIER COMPLET À COLLER DANS `app.py` :

```python
#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Serveur Flask Principal (Version Complète Cyber-Réseau 2026)
"""

import os
import io
import uuid
import secrets
import traceback
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for,
    send_file, session, abort, Response
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

# Coordonnées officielles de paiement
MVOLA_NUMBER = "038 28 171 00"
ORANGE_NUMBER = "037 39 755 72"
WHATSAPP_NUMBER = "0382817100"
WHATSAPP_DISPLAY = "+261 38 28 171 00"
PAYMENT_NAME = "JEAN ERIC"

from database import db, Order, MIKROTIK_MODELS, get_next_lan_subnet, get_model_info, generate_random_mac, generate_router_name
from warp_api import generate_script, generate_secret_guide

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


def secure_filename(filename):
    for c in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>', ' ']:
        filename = filename.replace(c, '_')
    return filename


# ===================== STYLE CSS CYBER-RÉSEAU PRO =====================

CSS_STYLES = """
:root {
    --dark-bg: #001e3c;
    --dark-card: #0a1929;
    --cyber-cyan: #00d4ff;
    --cyber-green: #00ff88;
    --neon-blue: #0066ff;
    --accent-orange: #ff6b1a;
    --border-glow: rgba(0, 212, 255, 0.25);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f5f7fb; color: #1a2332; line-height: 1.6; }

/* NAVBAR */
.navbar-pro { background: linear-gradient(135deg, #001e3c 0%, #0a1929 100%); padding: 15px 0; border-bottom: 1px solid var(--border-glow); box-shadow: 0 4px 20px rgba(0,30,60,0.15); }
.navbar-pro .navbar-brand { font-weight: 900; font-size: 1.4rem; color: white !important; letter-spacing: 1px; }
.navbar-pro .brand-glow { background: linear-gradient(135deg, var(--cyber-cyan), var(--cyber-green)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; }
.navbar-pro .nav-link { color: rgba(255,255,255,0.85) !important; font-weight: 600; padding: 8px 16px !important; transition: 0.3s; }
.navbar-pro .nav-link:hover { color: var(--cyber-cyan) !important; }
.navbar-pro .btn-cta-nav { background: linear-gradient(135deg, var(--cyber-green), #00cc6a); color: #001e3c !important; padding: 10px 24px; border-radius: 50px; font-weight: 800; border: none; text-decoration: none; box-shadow: 0 4px 15px rgba(0,255,136,0.3); transition: 0.3s; }
.navbar-pro .btn-cta-nav:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,255,136,0.5); }

/* HERO CYBER */
.hero-cyber { background: linear-gradient(135deg, #001e3c 0%, #0a1929 50%, #001428 100%); color: white; padding: 90px 0 80px; position: relative; overflow: hidden; }
.hero-cyber::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px); background-size: 40px 40px; }
.hero-title { font-size: 3.2rem; font-weight: 900; line-height: 1.15; margin-bottom: 20px; }
.hero-title .highlight { background: linear-gradient(135deg, var(--cyber-cyan), var(--cyber-green)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-subtitle { font-size: 1.15rem; color: rgba(255,255,255,0.85); margin-bottom: 30px; max-width: 580px; }
.hero-tag { background: rgba(0,212,255,0.12); border: 1px solid rgba(0,212,255,0.35); padding: 6px 16px; border-radius: 50px; font-size: 0.85rem; color: var(--cyber-cyan); font-weight: 700; display: inline-flex; align-items: center; gap: 8px; margin-bottom: 25px; }

.btn-hero-primary { background: linear-gradient(135deg, var(--cyber-green), #00cc6a); color: #001e3c; padding: 16px 38px; border-radius: 50px; font-weight: 800; font-size: 1.05rem; box-shadow: 0 8px 25px rgba(0,255,136,0.4); text-decoration: none; display: inline-block; transition: 0.3s; }
.btn-hero-primary:hover { transform: translateY(-2px); color: #001e3c; box-shadow: 0 12px 30px rgba(0,255,136,0.6); }
.btn-hero-secondary { background: transparent; color: white; padding: 15px 30px; border: 2px solid var(--cyber-cyan); border-radius: 50px; font-weight: 700; text-decoration: none; display: inline-block; margin-left: 12px; transition: 0.3s; }
.btn-hero-secondary:hover { background: var(--cyber-cyan); color: #001e3c; }

.router-box { background: linear-gradient(135deg, #0a1929, #001e3c); border: 2px solid var(--cyber-cyan); border-radius: 20px; padding: 35px 25px; text-align: center; box-shadow: 0 0 50px rgba(0,212,255,0.25); animation: float 3s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
.router-box i { font-size: 6.5rem; color: var(--cyber-cyan); }
.led-group { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }
.led { width: 12px; height: 12px; border-radius: 50%; box-shadow: 0 0 10px currentColor; animation: blink 1.2s infinite; }
.led.green { background: var(--cyber-green); color: var(--cyber-green); }
.led.blue { background: var(--cyber-cyan); color: var(--cyber-cyan); animation-delay: 0.3s; }
.led.orange { background: var(--accent-orange); color: var(--accent-orange); animation-delay: 0.6s; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

/* SECTION HEADERS */
.section-badge { display: inline-block; background: rgba(0,102,255,0.08); color: var(--neon-blue); padding: 6px 18px; border-radius: 50px; font-size: 0.8rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
.section-title { font-size: 2.4rem; font-weight: 900; color: #001e3c; margin-bottom: 12px; text-align: center; }
.section-subtitle { color: #607d8b; font-size: 1.05rem; text-align: center; margin-bottom: 45px; }

/* FEATURES */
.feature-card { background: white; border-radius: 20px; padding: 35px 25px; text-align: center; box-shadow: 0 4px 20px rgba(0,30,60,0.05); border: 1px solid #e2e8f0; height: 100%; transition: 0.3s; }
.feature-card:hover { transform: translateY(-8px); box-shadow: 0 15px 35px rgba(0,102,255,0.12); }
.feature-icon { width: 65px; height: 65px; background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(0,255,136,0.12)); border-radius: 18px; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; font-size: 1.8rem; color: var(--neon-blue); }

/* PRICING */
.pricing-card { background: white; border-radius: 22px; padding: 40px 30px; box-shadow: 0 4px 20px rgba(0,30,60,0.05); border: 2px solid transparent; height: 100%; display: flex; flex-direction: column; position: relative; transition: 0.3s; }
.pricing-card:hover { transform: translateY(-6px); box-shadow: 0 15px 40px rgba(0,30,60,0.1); }
.pricing-card.popular { border-color: var(--cyber-green); box-shadow: 0 8px 30px rgba(0,255,136,0.2); }
.pricing-card.pro { background: linear-gradient(135deg, #001e3c, #0a1929); color: white; }
.pricing-badge { position: absolute; top: -14px; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, var(--cyber-green), #00cc6a); color: #001e3c; padding: 5px 22px; border-radius: 50px; font-weight: 900; font-size: 0.75rem; letter-spacing: 1px; }
.pricing-badge.pro-badge { background: linear-gradient(135deg, var(--cyber-cyan), var(--neon-blue)); color: white; }
.pricing-name { font-size: 1.15rem; font-weight: 800; color: #001e3c; letter-spacing: 1px; margin-bottom: 8px; }
.pricing-card.pro .pricing-name { color: var(--cyber-cyan); }
.pricing-price { font-size: 2.7rem; font-weight: 900; color: #001e3c; margin: 12px 0; }
.pricing-price small { font-size: 1rem; color: #607d8b; font-weight: 600; }
.pricing-card.pro .pricing-price { color: white; }
.pricing-card.pro .pricing-price small { color: rgba(255,255,255,0.7); }
.pricing-features { list-style: none; padding: 0; margin: 20px 0; flex-grow: 1; }
.pricing-features li { padding: 9px 0; color: #37474f; display: flex; align-items: center; gap: 10px; font-size: 0.95rem; border-bottom: 1px solid #f1f5f9; }
.pricing-card.pro .pricing-features li { color: rgba(255,255,255,0.9); border-bottom-color: rgba(255,255,255,0.06); }
.pricing-features li i { color: #00cc6a; font-size: 0.95rem; }
.pricing-features li .secret-badge { background: rgba(255,107,26,0.15); color: var(--accent-orange); padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; }

.btn-pricing { padding: 14px 28px; border-radius: 50px; font-weight: 800; width: 100%; border: none; text-decoration: none; display: inline-block; text-align: center; transition: 0.3s; }
.btn-pricing-outline { background: transparent; color: var(--neon-blue); border: 2px solid var(--neon-blue); }
.btn-pricing-outline:hover { background: var(--neon-blue); color: white; }
.btn-pricing-primary { background: linear-gradient(135deg, var(--cyber-green), #00cc6a); color: #001e3c; }
.btn-pricing-primary:hover { box-shadow: 0 6px 20px rgba(0,255,136,0.4); color: #001e3c; }
.btn-pricing-dark { background: linear-gradient(135deg, var(--cyber-cyan), var(--neon-blue)); color: white; }
.btn-pricing-dark:hover { box-shadow: 0 6px 20px rgba(0,212,255,0.4); color: white; }

/* STEPS */
.step-card { text-align: center; padding: 20px; }
.step-number { width: 55px; height: 55px; background: linear-gradient(135deg, var(--cyber-cyan), var(--neon-blue)); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 18px; font-size: 1.4rem; font-weight: 900; box-shadow: 0 8px 20px rgba(0,212,255,0.3); }

/* FORMS */
.form-card { background: white; border-radius: 24px; padding: 40px 35px; box-shadow: 0 8px 30px rgba(0,30,60,0.06); border: 1px solid #e2e8f0; }
.form-label { font-weight: 700; color: #001e3c; margin-bottom: 7px; font-size: 0.9rem; }
.form-control, .form-select { border-radius: 12px; padding: 12px 16px; border: 1.5px solid #cbd5e1; font-size: 0.95rem; }
.form-control:focus, .form-select:focus { border-color: var(--cyber-cyan); box-shadow: 0 0 0 0.2rem rgba(0,212,255,0.15); }
.pack-radio { display: none; }
.pack-label { display: block; border: 2px solid #e2e8f0; border-radius: 16px; padding: 20px 12px; cursor: pointer; transition: 0.3s; text-align: center; background: white; height: 100%; }
.pack-radio:checked + .pack-label { border-color: #00cc6a; background: rgba(0,255,136,0.05); box-shadow: 0 6px 20px rgba(0,255,136,0.15); }
.pack-label h6 { font-weight: 800; color: #001e3c; margin-bottom: 6px; font-size: 0.95rem; }
.pack-label .price-tag { font-size: 1.35rem; font-weight: 900; color: #00cc6a; }

.advanced-box { background: linear-gradient(135deg, rgba(0,212,255,0.04), rgba(0,255,136,0.04)); border: 1px solid rgba(0,212,255,0.25); border-radius: 16px; padding: 25px; margin: 20px 0; }
.advanced-title { color: var(--neon-blue); font-weight: 800; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }

/* LICENCE & GUIDE */
.license-hero { background: linear-gradient(135deg, #001e3c 0%, #0a1929 100%); color: white; border-radius: 24px; padding: 50px 40px; text-align: center; }
.license-hero h2 { font-weight: 900; }
.license-input { border-radius: 50px !important; padding: 16px 25px !important; font-size: 1.05rem !important; text-align: center !important; border: 2px solid rgba(0,212,255,0.4) !important; background: rgba(255,255,255,0.1) !important; color: white !important; font-weight: 700; letter-spacing: 1px; }
.license-input:focus { border-color: var(--cyber-cyan) !important; background: rgba(255,255,255,0.18) !important; color: white !important; }
.script-area { background: #0d1117; color: #58a6ff; border-radius: 12px; padding: 22px; font-family: 'Courier New', monospace; font-size: 0.85rem; max-height: 480px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; border: 1px solid #30363d; }

.guide-secret-box { background: linear-gradient(135deg, #001e3c, #0a1929); color: white; border-radius: 20px; padding: 35px; margin: 25px 0; border: 2px solid var(--cyber-green); box-shadow: 0 0 30px rgba(0,255,136,0.2); }
.btn-download-secret { background: linear-gradient(135deg, var(--accent-orange), #cc5500); color: white !important; border: none; padding: 12px 28px; border-radius: 50px; font-weight: 800; text-decoration: none; display: inline-block; box-shadow: 0 6px 20px rgba(255,107,26,0.35); transition: 0.3s; }
.btn-download-secret:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(255,107,26,0.5); }

/* FOOTER */
footer.footer-pro { background: linear-gradient(180deg, #001e3c 0%, #000a15 100%); color: white; padding: 60px 0 25px; margin-top: 80px; border-top: 2px solid rgba(0,212,255,0.2); }
footer.footer-pro h5 { font-weight: 800; margin-bottom: 20px; font-size: 1rem; letter-spacing: 1px; text-transform: uppercase; color: var(--cyber-cyan); }
footer.footer-pro a { color: rgba(255,255,255,0.7); text-decoration: none; transition: 0.3s; display: inline-block; padding: 4px 0; }
footer.footer-pro a:hover { color: var(--cyber-green); transform: translateX(3px); }
.footer-payment-box { background: rgba(0,212,255,0.05); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,212,255,0.15); }
.footer-payment-number { color: white; font-weight: 800; font-size: 1.1rem; letter-spacing: 1px; }

/* BOUTONS FLOTTANTS */
.floating-cart { position: fixed; bottom: 30px; right: 30px; width: 65px; height: 65px; background: linear-gradient(135deg, var(--cyber-green), #00cc6a); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #001e3c; font-size: 1.6rem; box-shadow: 0 8px 25px rgba(0,255,136,0.5); z-index: 9999; text-decoration: none; animation: pulse 2s infinite; }
.floating-cart:hover { color: #001e3c; transform: scale(1.1); }
@keyframes pulse { 0%, 100% { box-shadow: 0 8px 25px rgba(0,255,136,0.5); } 50% { box-shadow: 0 8px 35px rgba(0,255,136,0.8); } }
.floating-cart .cart-badge { position: absolute; top: -5px; right: -5px; background: #ff3333; color: white; border-radius: 50%; width: 24px; height: 24px; font-size: 0.75rem; display: flex; align-items: center; justify-content: center; font-weight: 800; border: 2px solid white; }
.floating-whatsapp { position: fixed; bottom: 110px; right: 30px; width: 60px; height: 60px; background: #25D366; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.7rem; box-shadow: 0 8px 25px rgba(37,211,102,0.45); z-index: 9999; text-decoration: none; transition: 0.3s; }
.floating-whatsapp:hover { transform: scale(1.1); color: white; }

.status-badge { padding: 6px 14px; border-radius: 50px; font-size: 0.75rem; font-weight: 800; }
.status-pending { background: #fff3cd; color: #856404; }
.status-active { background: #d1e7dd; color: #0f5132; }
.status-rejected { background: #f8d7da; color: #842029; }
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
    <nav class="navbar navbar-expand-lg navbar-pro sticky-top">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-network-wired me-2" style="color:var(--cyber-cyan)"></i>
                KETRIKA <span class="brand-glow">MIKROTIK</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain" style="border-color: rgba(255,255,255,0.3)">
                <span class="navbar-toggler-icon" style="filter: invert(1)"></span>
            </button>
            <div class="collapse navbar-collapse" id="navMain">
                <ul class="navbar-nav ms-auto align-items-lg-center">
                    <li class="nav-item"><a class="nav-link" href="/#pricing"><i class="fas fa-tags me-1"></i>Tarifs</a></li>
                    <li class="nav-item"><a class="nav-link" href="/#how"><i class="fas fa-cogs me-1"></i>Fonctionnement</a></li>
                    <li class="nav-item"><a class="nav-link" href="/#faq"><i class="fas fa-question-circle me-1"></i>FAQ</a></li>
                    <li class="nav-item"><a class="nav-link" href="/my-license"><i class="fas fa-key me-1"></i>Ma Licence</a></li>
                    <li class="nav-item ms-lg-3"><a class="btn-cta-nav" href="/order"><i class="fas fa-shopping-cart me-1"></i>Commander</a></li>
                </ul>
            </div>
        </div>
    </nav>
    
    {body_html}
    
    <footer class="footer-pro">
        <div class="container">
            <div class="row g-4">
                <div class="col-lg-4 col-md-6">
                    <h5><i class="fas fa-network-wired me-2"></i>KETRIKA MIKROTIK</h5>
                    <p style="color:rgba(255,255,255,0.7);line-height:1.7">
                        Plateforme d'ingénierie réseau pour routeurs MikroTik RouterOS v7. 
                        Scripts d'automatisation, VPN Cloudflare WARP illimité, Hotspot WiFi Zone et contournement anti-détection de partage FAI.
                    </p>
                    <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" style="background:#25D366;color:white!important;padding:10px 22px;border-radius:50px;font-weight:700;margin-top:15px;display:inline-block;text-decoration:none">
                        <i class="fab fa-whatsapp me-2"></i>Assistance Technique
                    </a>
                </div>
                <div class="col-lg-3 col-md-6">
                    <h5><i class="fas fa-link me-2"></i>Navigation</h5>
                    <div class="d-flex flex-column">
                        <a href="/"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Accueil</a>
                        <a href="/#pricing"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Nos Packs</a>
                        <a href="/#how"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Comment ça marche</a>
                        <a href="/#faq"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>FAQ</a>
                        <a href="/order"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Commander</a>
                        <a href="/my-license"><i class="fas fa-chevron-right me-2" style="font-size:0.7rem"></i>Ma Licence</a>
                    </div>
                </div>
                <div class="col-lg-5 col-md-12">
                    <h5><i class="fas fa-credit-card me-2"></i>Paiement Sécurisé</h5>
                    <div class="footer-payment-box">
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-mobile-alt me-3" style="color:var(--cyber-green);font-size:1.4rem"></i>
                            <div>
                                <div style="color:rgba(255,255,255,0.6);font-size:0.85rem">MVola / WhatsApp</div>
                                <div class="footer-payment-number">{MVOLA_NUMBER}</div>
                            </div>
                        </div>
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-mobile-alt me-3" style="color:var(--accent-orange);font-size:1.4rem"></i>
                            <div>
                                <div style="color:rgba(255,255,255,0.6);font-size:0.85rem">Orange Money</div>
                                <div class="footer-payment-number">{ORANGE_NUMBER}</div>
                            </div>
                        </div>
                        <hr style="border-color:rgba(255,255,255,0.1);margin:12px 0">
                        <div class="text-center" style="color:rgba(255,255,255,0.85)">
                            <i class="fas fa-user-check me-1" style="color:var(--cyber-green)"></i>
                            Bénéficiaire : <strong style="color:white">{PAYMENT_NAME}</strong>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-center mt-5 pt-3" style="border-top:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);font-size:0.85rem">
                <p class="mb-1">&copy; 2026 <strong style="color:var(--cyber-cyan)">KETRIKA MIKROTIK</strong> — Tous droits réservés</p>
                <p class="mb-0"><i class="fas fa-shield-alt me-1"></i>Plateforme certifiée RouterOS v7 &bull; Madagascar</p>
            </div>
        </div>
    </footer>
    
    <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="floating-whatsapp" title="WhatsApp Support"><i class="fab fa-whatsapp"></i></a>
    <a href="/order" class="floating-cart" title="Commander"><i class="fas fa-shopping-cart"></i><span class="cart-badge">3</span></a>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    {extra_script}
</body>
</html>"""


# ===================== ACCUEIL =====================
HOME_BODY = """
<section class="hero-cyber">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-7">
                <div class="hero-tag"><i class="fas fa-microchip"></i> Ingénierie Réseau Avancée MikroTik</div>
                <h1 class="hero-title">Configurez votre <span class="highlight">MikroTik</span> en 1 clic</h1>
                <p class="hero-subtitle">Scripts automatisés de niveau ingénieur pour RouterOS v7. Tunnels VPN Cloudflare WARP, Hotspot Zone et masquage anti-coupure FAI / Haut Débit.</p>
                <div>
                    <a href="/order" class="btn-hero-primary"><i class="fas fa-bolt me-2"></i>Générer ma configuration</a>
                    <a href="/my-license" class="btn-hero-secondary"><i class="fas fa-key me-2"></i>J'ai déjà une référence</a>
                </div>
            </div>
            <div class="col-lg-5 d-none d-lg-block">
                <div class="router-box">
                    <i class="fas fa-server"></i>
                    <div class="led-group">
                        <div class="led green" title="Power OK"></div>
                        <div class="led blue" title="WAN Internet"></div>
                        <div class="led green" title="VPN WireGuard"></div>
                        <div class="led orange" title="WiFi Active"></div>
                    </div>
                    <div class="mt-3 text-muted small" style="color:var(--cyber-cyan)!important"><i class="fas fa-check-circle me-1"></i>100% Compatible RouterOS v7</div>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="py-5 bg-white">
    <div class="container">
        <div class="text-center mb-5">
            <div class="section-badge">Performances &amp; Sécurité</div>
            <h2 class="section-title">Pourquoi choisir notre moteur ?</h2>
        </div>
        <div class="row g-4">
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-bolt"></i></div><h5 class="fw-bold">Configuration Zéro Erreur</h5><p class="text-muted small">Aucune coupure Winbox lors du collage du script. Détection automatique du matériel.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-shield-alt"></i></div><h5 class="fw-bold">VPN Cloudflare WARP</h5><p class="text-muted small">Tunnels chiffrés WireGuard haute vitesse sans aucune perte de débit internet.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fas fa-satellite-dish"></i></div><h5 class="fw-bold">Anti-Détection &amp; Masquage FAI</h5><p class="text-muted small">Masquage TTL uniforme et MSS Clamping pour un partage réseau invisible.</p></div></div>
            <div class="col-md-6 col-lg-3"><div class="feature-card"><div class="feature-icon"><i class="fab fa-whatsapp"></i></div><h5 class="fw-bold">Assistance Directe</h5><p class="text-muted small">Support technique réactif et livraison de vos accès via WhatsApp sous 10 min.</p></div></div>
        </div>
    </div>
</section>

<section class="py-5" id="pricing" style="background:#f1f5f9">
    <div class="container">
        <div class="text-center mb-5">
            <div class="section-badge">Formules &amp; Tarifs</div>
            <h2 class="section-title">Choisissez votre Pack</h2>
            <p class="section-subtitle">Chaque licence est taillée sur mesure pour votre modèle exact de routeur</p>
        </div>
        <div class="row g-4 justify-content-center">
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card">
                    <div class="pricing-name">PACK ESSENTIEL</div>
                    <div class="pricing-price">30 000 <small>Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Configuration Bridge &amp; DHCP Auto</li>
                        <li><i class="fas fa-check"></i> Wi-Fi Sécurisé (WPA2/WPA3)</li>
                        <li><i class="fas fa-check"></i> DNS Chiffré Cloudflare DoH</li>
                        <li><i class="fas fa-check"></i> Masquage TTL (Anti-partage FAI)</li>
                        <li><i class="fas fa-check"></i> Limitation de bande passante QoS</li>
                    </ul>
                    <a href="/order?pack=standard" class="btn-pricing btn-pricing-outline">Commander Essentiel</a>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card popular">
                    <div class="pricing-badge">LE PLUS CHOISI</div>
                    <div class="pricing-name mt-2">PACK SÉCURITÉ VPN</div>
                    <div class="pricing-price">50 000 <small>Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Tout le Pack Essentiel +</li>
                        <li><i class="fas fa-check"></i> <strong>VPN Cloudflare WARP illimité</strong></li>
                        <li><i class="fas fa-check"></i> Contournement DPI &amp; Restrictions FAI</li>
                        <li><i class="fas fa-check"></i> MSS Clamping TCP automatique</li>
                        <li><i class="fas fa-gift" style="color:var(--accent-orange)"></i> <strong>Guide Secret Optimisation Réseau (PDF)</strong> <span class="secret-badge">INCLUS</span></li>
                    </ul>
                    <a href="/order?pack=warp" class="btn-pricing btn-pricing-primary">Commander Sécurité VPN</a>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="pricing-card pro">
                    <div class="pricing-badge pro-badge">BUSINESS PRO</div>
                    <div class="pricing-name mt-2">PACK BUSINESS HOTSPOT</div>
                    <div class="pricing-price">80 000 <small>Ar</small></div>
                    <ul class="pricing-features">
                        <li><i class="fas fa-check"></i> Tout le Pack Sécurité VPN +</li>
                        <li><i class="fas fa-check"></i> <strong>Portail Captif WiFi Zone</strong></li>
                        <li><i class="fas fa-check"></i> 10 Vouchers de test auto-générés</li>
                        <li><i class="fas fa-check"></i> Profils vitesse (1h, 1j, 1sem, 1mois)</li>
                        <li><i class="fas fa-check"></i> Pare-feu Anti-Torrent P2P</li>
                        <li><i class="fas fa-gift" style="color:var(--accent-orange)"></i> <strong>Guide Secret Avancé (PDF)</strong></li>
                    </ul>
                    <a href="/order?pack=hotspot" class="btn-pricing btn-pricing-dark">Commander Hotspot Pro</a>
                </div>
            </div>
        </div>
    </div>
</section>

<section class="py-5 bg-white" id="how">
    <div class="container">
        <div class="text-center mb-5">
            <div class="section-badge">Simple &amp; Efficace</div>
            <h2 class="section-title">Comment ça marche ?</h2>
        </div>
        <div class="row g-4">
            <div class="col-md-3"><div class="step-card"><div class="step-number">1</div><h5 class="fw-bold">Personnalisez</h5><p class="text-muted small">Remplissez le formulaire en sélectionnant votre modèle MikroTik et vos préférences.</p></div></div>
            <div class="col-md-3"><div class="step-card"><div class="step-number">2</div><h5 class="fw-bold">Payez</h5><p class="text-muted small">Transférez le montant par MVola ou Orange Money et envoyez la capture d'écran.</p></div></div>
            <div class="col-md-3"><div class="step-card"><div class="step-number">3</div><h5 class="fw-bold">Validation 10 min</h5><p class="text-muted small">Notre équipe approuve votre commande et active votre licence RouterOS.</p></div></div>
            <div class="col-md-3"><div class="step-card"><div class="step-number">4</div><h5 class="fw-bold">Injectez</h5><p class="text-muted small">Allez sur "Ma Licence", copiez le script et collez-le dans le Terminal Winbox.</p></div></div>
        </div>
    </div>
</section>

<section class="py-5" id="faq" style="background:#f8fafc">
    <div class="container" style="max-width:800px">
        <div class="text-center mb-5">
            <div class="section-badge">Support &amp; Réponses</div>
            <h2 class="section-title">Foire Aux Questions</h2>
        </div>
        <div class="accordion" id="faqAcc">
            <div class="accordion-item border-0 mb-3 shadow-sm rounded-4 overflow-hidden">
                <h2 class="accordion-header"><button class="accordion-button collapsed fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#f1">Est-ce que le VPN ralentit le débit internet ?</button></h2>
                <div id="f1" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Non. Cloudflare WARP s'appuie sur le protocole WireGuard nouvelle génération avec un réseau de serveurs ultra-rapides. Vous conservez 100% de votre bande passante.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded-4 overflow-hidden">
                <h2 class="accordion-header"><button class="accordion-button collapsed fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#f2">Comment récupérer mon script une fois la commande passée ?</button></h2>
                <div id="f2" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Dès validation de votre paiement, rendez-vous sur le menu <strong>"Ma Licence"</strong> et tapez simplement votre référence de commande <strong>KTR-...</strong> pour accéder immédiatement à votre script complet et à vos guides.</div></div>
            </div>
            <div class="accordion-item border-0 mb-3 shadow-sm rounded-4 overflow-hidden">
                <h2 class="accordion-header"><button class="accordion-button collapsed fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#f3">Est-ce que le collage du script coupe la session Winbox ?</button></h2>
                <div id="f3" class="accordion-collapse collapse" data-bs-parent="#faqAcc"><div class="accordion-body bg-white text-muted">Non ! Notre nouveau moteur applique la configuration sans détruire le Bridge existant. Le script s'exécute de A à Z sans aucune déconnexion intermédiaire.</div></div>
            </div>
        </div>
    </div>
</section>
"""

@app.route('/')
def home():
    try:
        return render_page(HOME_BODY, title="Plateforme d'Ingénierie Réseau")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur Serveur</h1><pre>{e}</pre>", 500


# ===================== COMMANDE =====================
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

            # Nouvelles options pro
            router_name = (request.form.get('router_name') or '').strip()
            mac_spoof = request.form.get('mac_spoof') == '1'
            mac_address = (request.form.get('mac_address') or '').strip()
            sleep_mode = request.form.get('sleep_mode') or 'off'
            client_limit = request.form.get('client_limit') or '0'

            subnet_info = get_next_lan_subnet()
            order_id = 'KTR-' + uuid.uuid4().hex[:8].upper()
            license_key = 'LIC-' + secrets.token_hex(16).upper()

            if not router_name:
                router_name = generate_router_name(license_key)
            if mac_spoof and not mac_address:
                mac_address = generate_random_mac()

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
                router_name=router_name,
                mac_spoof=mac_spoof,
                mac_address=mac_address,
                sleep_mode=sleep_mode,
                client_limit=client_limit,
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(new_order)
            db.session.commit()
            return redirect(url_for('pay', order_id=order_id))

        preselect = request.args.get('pack', 'warp')
        options_html = '<option value="">-- Sélectionnez votre routeur --</option>'
        for key, info in MIKROTIK_MODELS.items():
            options_html += f'<option value="{key}">{info["name"]}</option>'
        options_html += '<option value="other">Autre / Modèle non listé</option>'

        c1 = 'checked' if preselect == 'standard' else ''
        c2 = 'checked' if preselect == 'warp' else ''
        c3 = 'checked' if preselect == 'hotspot' else ''

        body = f"""
<section class="py-5">
    <div class="container" style="max-width:880px">
        <div class="form-card">
            <h2 class="fw-bold mb-2 text-center" style="color:#001e3c"><i class="fas fa-sliders-h me-2" style="color:var(--neon-blue)"></i>Générateur de Configuration MikroTik</h2>
            <p class="text-muted text-center mb-4">Personnalisez les paramètres pour générer un script 100% adapté à votre routeur</p>
            
            <form method="POST" action="/order">
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Nom complet du client</label>
                        <input type="text" name="client_name" class="form-control" required placeholder="Ex: Jean Eric">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label"><i class="fab fa-whatsapp text-success me-1"></i>Numéro WhatsApp (pour notification)</label>
                        <input type="text" name="whatsapp" class="form-control" required placeholder="+261 34 XX XXX XX">
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label">Formule choisie</label>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <input type="radio" name="plan_type" value="standard" id="p1" class="pack-radio" {c1}>
                            <label class="pack-label" for="p1"><h6>Pack Essentiel</h6><div class="price-tag">30 000 Ar</div></label>
                        </div>
                        <div class="col-md-4">
                            <input type="radio" name="plan_type" value="warp" id="p2" class="pack-radio" {c2}>
                            <label class="pack-label" for="p2"><h6>Pack Sécurité VPN</h6><div class="price-tag">50 000 Ar</div></label>
                        </div>
                        <div class="col-md-4">
                            <input type="radio" name="plan_type" value="hotspot" id="p3" class="pack-radio" {c3}>
                            <label class="pack-label" for="p3"><h6>Pack Hotspot Pro</h6><div class="price-tag">80 000 Ar</div></label>
                        </div>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Modèle MikroTik</label>
                    <select name="mikrotik_model" class="form-select" id="modelSelect" required>{options_html}</select>
                </div>
                <div class="mb-3" id="otherModelDiv" style="display:none">
                    <label class="form-label">Indiquez la référence exacte de votre routeur</label>
                    <input type="text" name="other_model" class="form-control" placeholder="Ex: RB1100AHx4">
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Nom du réseau Wi-Fi (SSID)</label>
                        <input type="text" name="ssid" class="form-control" value="KETRIKA-WiFi">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Mot de passe Wi-Fi (min. 8 caractères)</label>
                        <input type="text" name="wifi_password" class="form-control" minlength="8" value="ketrika2024">
                    </div>
                </div>

                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Interface WAN (Câble FAI / Modem Source)</label>
                        <input type="text" name="wan_interface" class="form-control" value="ether1">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Masquage TTL (Anti-Partage FAI)</label>
                        <select name="ttl_value" class="form-select">
                            <option value="64" selected>64 (Recommandé standard / Haut Débit)</option>
                            <option value="65">65 (Opérateurs 4G spécifiques)</option>
                            <option value="128">128 (Windows direct)</option>
                            <option value="0">Désactivé</option>
                        </select>
                    </div>
                </div>

                <!-- OPTIONS AVANCÉES -->
                <div class="advanced-box">
                    <div class="advanced-title"><i class="fas fa-shield-alt"></i> Options Avancées d'Ingénierie Réseau</div>
                    
                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Nom personnalisé du routeur (Identity)</label>
                            <input type="text" name="router_name" class="form-control" placeholder="Ex: HOME-ROUTER (Laisser vide pour auto)">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Mode Veille Nocturne Wi-Fi (Économie &amp; Sécurité)</label>
                            <select name="sleep_mode" class="form-select">
                                <option value="off" selected>Désactivé (Wi-Fi 24h/24)</option>
                                <option value="00-06">Éteindre le Wi-Fi de 00h00 à 06h00</option>
                                <option value="01-05">Éteindre le Wi-Fi de 01h00 à 05h00</option>
                                <option value="23-07">Éteindre le Wi-Fi de 23h00 à 07h00</option>
                                <option value="02-06">Éteindre le Wi-Fi de 02h00 à 06h00</option>
                            </select>
                        </div>
                    </div>

                    <div class="row g-3 mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Limite par client individuel (QoS PCQ)</label>
                            <select name="client_limit" class="form-select">
                                <option value="0" selected>Illimité par appareil</option>
                                <option value="2M">2 Mbps max par appareil</option>
                                <option value="5M">5 Mbps max par appareil</option>
                                <option value="10M">10 Mbps max par appareil</option>
                                <option value="20M">20 Mbps max par appareil</option>
                            </select>
                        </div>
                        <div class="col-md-6 d-flex align-items-center pt-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="mac_spoof" value="1" id="macCheck" checked>
                                <label class="form-check-label fw-bold" for="macCheck">
                                    Changement d'adresse MAC WAN automatique (Anti-détection FAI)
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="hotspotOptions" style="display:none;background:#f0f7ff;padding:20px;border-radius:14px;border:1px solid #cce5ff" class="mb-4">
                    <h6 class="fw-bold text-primary mb-2"><i class="fas fa-wifi me-1"></i> Paramètres du Portail Captif Hotspot</h6>
                    <div class="form-check mb-2">
                        <input type="checkbox" name="voucher_enabled" class="form-check-input" id="vcCheck" value="1" checked>
                        <label class="form-check-label fw-bold" for="vcCheck">Générer 10 tickets/vouchers d'accès Wi-Fi automatiquement</label>
                    </div>
                </div>

                <button type="submit" class="btn-cta-form"><i class="fas fa-check-circle me-2"></i>Valider et passer au paiement</button>
            </form>
        </div>
    </div>
</section>
"""
        js = """
<script>
document.querySelectorAll('input[name=plan_type]').forEach(function(r){
    r.addEventListener('change',function(){
        document.getElementById('hotspotOptions').style.display = (this.value==='hotspot') ? 'block' : 'none';
    });
});
document.getElementById('modelSelect').addEventListener('change',function(){
    document.getElementById('otherModelDiv').style.display = (this.value==='other') ? 'block' : 'none';
});
(function(){
    var s = document.querySelector('input[name=plan_type]:checked');
    if(s && s.value==='hotspot') document.getElementById('hotspotOptions').style.display='block';
})();
</script>
"""
        return render_page(body, title="Configurer mon MikroTik", extra_script=js)
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ===================== PAIEMENT =====================
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
        <div class="form-card">
            <div style="font-size: 5rem; color: #00cc6a;" class="mb-3"><i class="fas fa-check-circle"></i></div>
            <h3 class="fw-bold">Capture d'écran reçue !</h3>
            <p class="text-muted fs-5">Votre paiement est en cours de validation par notre équipe technique.</p>
            <hr>
            <div class="alert alert-info text-start">
                <h6 class="fw-bold"><i class="fas fa-info-circle me-1"></i>Comment récupérer votre script ?</h6>
                <p class="mb-0 small">Dès validation (délai : ~10 minutes), rendez-vous dans le menu <strong>"Ma Licence"</strong> et saisissez votre référence : <strong>{order_id}</strong>.</p>
            </div>
            <div class="d-grid gap-2 mt-4">
                <a href="/my-license" class="btn btn-hero-primary"><i class="fas fa-key me-2"></i>Accéder à "Ma Licence"</a>
                <a href="/" class="btn btn-outline-secondary rounded-pill">Retour à l'accueil</a>
            </div>
        </div>
    </div>
</section>
"""
            return render_page(body, title="Paiement Transmis")

        plan = safe_get(order_obj, 'plan_type', 'standard')
        price_map = {'standard': ('30 000 Ar', 'Pack Essentiel'), 'warp': ('50 000 Ar', 'Pack Sécurité VPN'), 'hotspot': ('80 000 Ar', 'Pack Business Hotspot')}
        price, name = price_map.get(plan, ('30 000 Ar', 'Pack Essentiel'))

        body = f"""
<section class="py-5">
    <div class="container" style="max-width:720px">
        <div class="form-card">
            <h3 class="text-center fw-bold mb-4" style="color:#001e3c"><i class="fas fa-mobile-alt me-2" style="color:var(--cyber-green)"></i>Finalisation du Paiement</h3>
            
            <div class="summary-box-pro mb-4">
                <div class="row">
                    <div class="col-6"><strong>Référence :</strong> {safe_get(order_obj, 'order_id')}</div>
                    <div class="col-6 text-end"><strong>Formule :</strong> {name}</div>
                    <div class="col-12 mt-2 pt-2 border-top"><strong>Montant à payer :</strong> <span class="fs-4 fw-bold text-success">{price}</span></div>
                </div>
            </div>

            <div class="alert alert-warning p-3 mb-4">
                <h6 class="fw-bold mb-3"><i class="fas fa-wallet me-2"></i>Envoyez exactement <strong>{price}</strong> :</h6>
                <div class="p-3 mb-2 rounded bg-white border-start border-4 border-success">
                    <span class="text-muted small">MVola :</span><br>
                    <strong class="fs-5" style="color:#00cc6a;letter-spacing:1px">{MVOLA_NUMBER}</strong>
                </div>
                <div class="p-3 mb-2 rounded bg-white border-start border-4 border-warning">
                    <span class="text-muted small">Orange Money :</span><br>
                    <strong class="fs-5" style="color:#ff6b1a;letter-spacing:1px">{ORANGE_NUMBER}</strong>
                </div>
                <div class="text-center mt-3 small">
                    <i class="fas fa-user-check me-1"></i>Titulaire du compte : <strong>{PAYMENT_NAME}</strong>
                </div>
            </div>

            <form method="POST" action="/pay/{order_id}" enctype="multipart/form-data">
                <div class="mb-3">
                    <label class="form-label">Capture d'écran de la preuve de transfert</label>
                    <input type="file" name="payment_proof" class="form-control" accept="image/*" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Confirmez votre numéro WhatsApp</label>
                    <input type="text" name="whatsapp_confirm" class="form-control" value="{safe_get(order_obj, 'whatsapp_number')}" required>
                </div>
                <button type="submit" class="btn-cta-form"><i class="fas fa-upload me-2"></i>Transmettre la capture d'écran</button>
            </form>
        </div>
    </div>
</section>
"""
        return render_page(body, title="Instructions de Paiement")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur paiement</h1><pre>{e}</pre>", 500


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
                error = '<div class="alert alert-warning mt-3"><i class="fas fa-exclamation-triangle me-2"></i>Veuillez saisir votre référence ou clé.</div>'
            else:
                order_obj = Order.query.filter(
                    (db.func.upper(Order.license_key) == key) | 
                    (db.func.upper(Order.order_id) == key)
                ).first()
                
                if order_obj:
                    return redirect(url_for('license_page', key=order_obj.license_key))
                else:
                    error = f'''<div class="alert alert-danger mt-3">
                        <i class="fas fa-times-circle me-2"></i><strong>Référence introuvable.</strong><br>
                        <small>Vérifiez votre référence de commande (ex: <code>{saved_key}</code>) ou contactez le support.</small>
                    </div>'''

        body = f"""
<section class="py-5">
    <div class="container" style="max-width: 760px">
        <div class="license-hero mb-4">
            <div style="font-size: 3.5rem; color: var(--cyber-cyan);" class="mb-2"><i class="fas fa-key"></i></div>
            <h2>Accès Configuration &amp; Téléchargements</h2>
            <p class="text-white-50 mb-4">Saisissez votre référence de commande (<code>KTR-...</code>) ou votre clé de licence (<code>LIC-...</code>)</p>
            
            <form method="POST">
                <input type="text" name="license_key" class="form-control license-input mb-3" placeholder="KTR-XXXXXXXX ou LIC-XXXXXXXX" value="{saved_key}" required autocomplete="off">
                <button type="submit" class="btn btn-hero-primary"><i class="fas fa-unlock me-2"></i>Afficher mon script MikroTik</button>
            </form>
            {error}
        </div>
    </div>
</section>
"""
        return render_page(body, title="Espace Licence")
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


# ===================== SCRIPT & GUIDE =====================
@app.route('/license/<key>')
def license_page(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            order_obj = Order.query.filter_by(order_id=key).first()
            if not order_obj:
                abort(404)

        if safe_get(order_obj, 'status') != 'active':
            ref = safe_get(order_obj, 'order_id')
            body = f"""
<section class="py-5 text-center">
    <div class="container" style="max-width: 650px">
        <div class="form-card">
            <div style="font-size: 4.5rem; color: #ffc107;" class="mb-3"><i class="fas fa-clock"></i></div>
            <h4 class="fw-bold">Activation en cours</h4>
            <p class="text-muted">Votre commande <code>{ref}</code> est en cours de validation par notre administrateur.</p>
            <div class="alert alert-info mt-4 text-start small">
                <strong>Délai moyen :</strong> moins de 10 minutes après envoi de la capture de paiement. Rafraîchissez cette page dans quelques instants.
            </div>
            <a href="https://wa.me/261{WHATSAPP_NUMBER}" target="_blank" class="btn btn-success rounded-pill px-4 mt-2">
                <i class="fab fa-whatsapp me-2"></i>Contacter le support
            </a>
        </div>
    </div>
</section>
"""
            return render_page(body, title="Validation en cours")

        script = generate_script(order_obj)
        esc_script = script.replace('<', '&lt;').replace('>', '&gt;')
        plan = safe_get(order_obj, 'plan_type')

        secret_guide_btn = ""
        if plan in ['warp', 'hotspot']:
            secret_guide_btn = f"""
            <div class="guide-secret-box text-start mt-4">
                <h5><i class="fas fa-user-secret me-2"></i>Guide Exclusif : Contournement Restrictions FAI</h5>
                <p class="small text-white-50 mb-3">Téléchargez le dossier technique expliquant le fonctionnement du masquage TTL, du MSS Clamping et les réglages optimaux.</p>
                <a href="/download-guide/{safe_get(order_obj, 'license_key')}" class="btn-download-secret">
                    <i class="fas fa-file-download me-2"></i>Télécharger le Guide Secret (.txt)
                </a>
            </div>
            """

        body = f"""
<section class="py-5">
    <div class="container" style="max-width: 920px">
        <div class="form-card">
            <div class="text-center mb-4">
                <div style="font-size: 3rem; color: var(--cyber-green);"><i class="fas fa-check-circle"></i></div>
                <h3 class="fw-bold" style="color:#001e3c">Configuration Prête &amp; Active</h3>
                <span class="badge bg-success py-2 px-3">{safe_get(order_obj, 'license_key')}</span>
            </div>

            <div class="summary-box-pro mb-4">
                <div class="row small">
                    <div class="col-md-4"><strong>Client :</strong> {safe_get(order_obj, 'client_name')}</div>
                    <div class="col-md-4"><strong>Routeur :</strong> {safe_get(order_obj, 'mikrotik_model')}</div>
                    <div class="col-md-4"><strong>Wi-Fi SSID :</strong> {safe_get(order_obj, 'ssid')}</div>
                </div>
            </div>

            <h6 class="fw-bold mb-2">Script de Configuration RouterOS v7 :</h6>
            <div class="script-area mb-3" id="scrText">{esc_script}</div>

            <div class="row g-3">
                <div class="col-6">
                    <button class="btn btn-hero-primary w-100" id="cpBtn" onclick="cp()"><i class="fas fa-copy me-2"></i>Copier le script</button>
                </div>
                <div class="col-6">
                    <a href="/download/{safe_get(order_obj, 'license_key')}" class="btn btn-outline-primary w-100 py-3 rounded-pill fw-bold"><i class="fas fa-download me-2"></i>Télécharger (.rsc)</a>
                </div>
            </div>

            {secret_guide_btn}

            <div class="alert alert-info mt-4 small">
                <h6 class="fw-bold"><i class="fas fa-terminal me-1"></i>Procédure d'injection dans Winbox :</h6>
                <ol class="mb-0 ps-3">
                    <li>Ouvrez <strong>Winbox</strong> et connectez-vous à votre MikroTik.</li>
                    <li>Cliquez sur <strong>New Terminal</strong> dans le menu de gauche.</li>
                    <li>Cliquez sur <strong>"Copier le script"</strong> ci-dessus puis faites <strong>Ctrl+V</strong> (ou clic droit &rarr; Paste) dans le terminal.</li>
                    <li>Le routeur applique tous les réglages et redémarre automatiquement.</li>
                </ol>
            </div>
        </div>
    </div>
</section>
"""
        js = """
<script>
function cp(){
    var t = document.getElementById('scrText').innerText;
    navigator.clipboard.writeText(t).then(function(){
        var b = document.getElementById('cpBtn');
        b.innerHTML = '<i class="fas fa-check me-2"></i>Script copié !';
        setTimeout(function(){ b.innerHTML = '<i class="fas fa-copy me-2"></i>Copier le script'; }, 2000);
    });
}
</script>
"""
        return render_page(body, title="Script de Configuration", extra_script=js)
    except HTTPException as e:
        raise e
    except Exception as e:
        traceback.print_exc()
        return f"<h1>Erreur</h1><pre>{e}</pre>", 500


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


@app.route('/download-guide/<key>')
def download_guide(key):
    try:
        order_obj = Order.query.filter_by(license_key=key).first()
        if not order_obj:
            order_obj = Order.query.filter_by(order_id=key).first()
            if not order_obj:
                abort(404)
        if safe_get(order_obj, 'status') != 'active':
            abort(403)

        guide_txt = generate_secret_guide(order_obj)
        fname = f"GUIDE_TECHNIQUE_KETRIKA_{key[:8]}.txt"
        
        return Response(
            guide_txt,
            mimetype="text/plain",
            headers={"Content-disposition": f"attachment; filename={fname}"}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return str(e), 500


# ===================== ADMIN =====================
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
            err = '<div class="alert alert-danger">Mot de passe incorrect</div>'

        body = f"""
<div class="d-flex align-items-center justify-content-center" style="min-height:75vh">
    <div class="form-card text-center" style="max-width:400px; width:100%;">
        <h3 class="fw-bold mb-3">Espace Administrateur</h3>
        {err}
        <form method="POST">
            <input type="password" name="password" class="form-control mb-3 text-center" placeholder="Mot de passe" required>
            <button class="btn btn-hero-primary w-100">Se connecter</button>
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
                <form method="POST" action="/admin/validate/{o.order_id}" style="display:inline"><button class="btn btn-sm btn-success text-white" title="Valider"><i class="fas fa-check"></i></button></form>
                <form method="POST" action="/admin/reject/{o.order_id}" style="display:inline"><button class="btn btn-sm btn-danger" title="Refuser"><i class="fas fa-times"></i></button></form>
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
    <td><strong>{safe_get(o, 'order_id')}</strong></td>
    <td>{safe_get(o, 'client_name')}</td>
    <td><a href="https://wa.me/{safe_get(o, 'whatsapp_number').replace(' ','').replace('+','')}" target="_blank">{safe_get(o, 'whatsapp_number')}</a></td>
    <td>{p_type.upper()}</td>
    <td><small class="text-muted">{safe_get(o, 'license_key', '')[:16]}...</small></td>
    <td>{proof_btn}</td>
    <td>{badg}</td>
    <td>{act}</td>
</tr>
"""
        if not rows:
            rows = '<tr><td colspan="8" class="text-center text-muted py-4">Aucune commande enregistrée</td></tr>'

        body = f"""
<div class="bg-dark py-3 mb-4">
    <div class="container d-flex justify-content-between align-items-center">
        <h5 class="text-white mb-0"><i class="fas fa-shield-alt me-2" style="color:var(--cyber-green)"></i>PANEL KETRIKA ADMIN</h5>
        <a href="/admin/logout" class="btn btn-sm btn-outline-light rounded-pill">Déconnexion</a>
    </div>
</div>
<section class="container pb-5">
    <div class="row g-3 mb-4 text-center">
        <div class="col-4"><div class="form-card py-3"><h5>Total</h5><div class="fs-2 fw-bold">{total}</div></div></div>
        <div class="col-4"><div class="form-card py-3"><h5>En attente</h5><div class="fs-2 fw-bold text-warning">{pending}</div></div></div>
        <div class="col-4"><div class="form-card py-3"><h5>Actifs</h5><div class="fs-2 fw-bold text-success">{active}</div></div></div>
    </div>
    <div class="card shadow-sm border-0 rounded-4 overflow-hidden">
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```
