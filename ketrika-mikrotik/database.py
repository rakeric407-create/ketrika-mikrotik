# database.py - KETRIKA MIKROTIK - Modèle Stable (1 Clé = 1 Routeur)
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import secrets

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Client
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(30))

    # Formule
    plan_type = db.Column(db.String(20), nullable=False)
    plan_price = db.Column(db.Integer, nullable=False)

    # Routeur
    mikrotik_model = db.Column(db.String(50), nullable=False)
    wan_interface = db.Column(db.String(20), default='ether1')
    lan_network = db.Column(db.String(20), default='192.168.88.0/24')
    lan_gateway = db.Column(db.String(20), default='192.168.88.1')
    dhcp_pool = db.Column(db.String(50), default='192.168.88.10-192.168.88.250')
    ssid = db.Column(db.String(50), default='WiFiZone-Ketrika')
    wifi_password = db.Column(db.String(50), default='Ketrika2024')
    ttl_value = db.Column(db.Integer, default=65)
    dl_limit = db.Column(db.String(20), default='10M')
    ul_limit = db.Column(db.String(20), default='5M')

    # Options Hotspot
    hotspot_name = db.Column(db.String(50))
    pppoe_enabled = db.Column(db.Boolean, default=False)
    voucher_enabled = db.Column(db.Boolean, default=False)

    # Paiement
    payment_proof = db.Column(db.String(200))
    payment_method = db.Column(db.String(30))

    # Statut & Licence
    status = db.Column(db.String(20), default='pending')
    license_key = db.Column(db.String(50), unique=True)
    script_content = db.Column(db.Text)

    def generate_order_id(self):
        self.order_id = f"KTK-{datetime.now().strftime('%y%m%d')}-{secrets.token_hex(3).upper()}"

    def generate_license_key(self):
        h = secrets.token_hex(8).upper()
        self.license_key = f"KTK-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    @property
    def status_badge(self):
        return {
            'pending': '🟡 En attente',
            'delivered': '🟢 Actif (1 Routeur Verrouillé)',
            'rejected': '🔴 Rejeté'
        }.get(self.status, self.status)

MIKROTIK_MODELS = {
    'hAP lite (RB941)':       {'ports': 4, 'wifi': True,  'wifi5g': False},
    'hAP ac2 (RBD52G)':       {'ports': 5, 'wifi': True,  'wifi5g': True},
    'hAP ac3 (RBD53iG)':      {'ports': 5, 'wifi': True,  'wifi5g': True},
    'hAP ax2 (C52iG)':        {'ports': 5, 'wifi': True,  'wifi5g': True},
    'hAP ax3 (C53UiG+)':      {'ports': 5, 'wifi': True,  'wifi5g': True},
    'hEX (RB750Gr3)':         {'ports': 5, 'wifi': False, 'wifi5g': False},
    'hEX S (RB760iGS)':       {'ports': 5, 'wifi': False, 'wifi5g': False},
    'RB3011':                 {'ports': 10,'wifi': False, 'wifi5g': False},
    'RB4011':                 {'ports': 10,'wifi': True,  'wifi5g': True},
    'CCR1009':                {'ports': 8, 'wifi': False, 'wifi5g': False},
    'CCR2004':                {'ports': 12,'wifi': False, 'wifi5g': False},
}

PLANS = {
    'basic': {
        'name': 'Pack Essentiel',
        'subtitle': 'Configuration standard optimisée',
        'price': 30000,
        'currency': 'Ar',
        'features': [
            '1 Clé = 1 Routeur Verrouillé',
            'Bridge & interfaces auto-configurés',
            'DHCP Server & NAT sécurisé',
            'Normalisation TCP & Protection FAI',
            'Attribution asynchrone (Zéro coupure)',
            'Garantie sans erreur RouterOS v7'
        ],
        'color': '#0284c7'
    },
    'warp': {
        'name': 'Pack Premium Cloudflare',
        'subtitle': 'Débit illimité & Tunnel Sécurisé',
        'price': 50000,
        'currency': 'Ar',
        'features': [
            '1 Clé = 1 Routeur Verrouillé',
            'Cloudflare Secure WireGuard Tunnel',
            'Débit illimité sans perte de vitesse',
            'Chiffrement AES-256 complet',
            'Stabilité multi-utilisateurs garantie',
            'DNS-over-HTTPS (DoH) intégré',
            'Clés WireGuard auto-générées'
        ],
        'color': '#10b981',
        'popular': True
    },
    'hotspot': {
        'name': 'Pack Business WiFi Zone',
        'subtitle': 'Solution complète opérateur',
        'price': 80000,
        'currency': 'Ar',
        'features': [
            '1 Clé = 1 Routeur Verrouillé',
            'Tout le Pack Premium inclus',
            'Portail Hotspot RouterOS v7',
            'Serveur PPPoE multi-clients',
            'Gestion de vitesse par utilisateur',
            '10 Vouchers pré-générés',
            'Profils horaires (1h, 1j, 1sem, 1mois)'
        ],
        'color': '#f97316'
    }
}

PAYMENT_CONFIG = {
    'mvola': '038 28 171 00',
    'orange': '037 39 755 72',
    'beneficiaire': 'Jean Eric',
    'whatsapp': '038 28 171 00'
}
