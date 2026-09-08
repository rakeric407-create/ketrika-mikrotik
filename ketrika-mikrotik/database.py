# database.py - Modèles de données KETRIKA
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
    order_id = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(30))

    plan_type = db.Column(db.String(20), nullable=False)
    plan_price = db.Column(db.Integer, nullable=False)

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

    hotspot_name = db.Column(db.String(50))
    pppoe_enabled = db.Column(db.Boolean, default=False)
    voucher_enabled = db.Column(db.Boolean, default=False)

    payment_proof = db.Column(db.String(200))
    payment_method = db.Column(db.String(30))

    status = db.Column(db.String(20), default='pending')
    license_key = db.Column(db.String(50))
    validated_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)

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
            'validated': '🟢 Validé',
            'delivered': '✅ Livré',
            'rejected': '🔴 Rejeté'
        }.get(self.status, self.status)

MIKROTIK_MODELS = {
    'hAP lite (RB941)':       {'ports': 4, 'wifi': True,  'wifi5g': False, 'poe': False},
    'hAP ac2 (RBD52G)':       {'ports': 5, 'wifi': True,  'wifi5g': True,  'poe': False},
    'hAP ac3 (RBD53iG)':      {'ports': 5, 'wifi': True,  'wifi5g': True,  'poe': True},
    'hAP ax2 (C52iG)':        {'ports': 5, 'wifi': True,  'wifi5g': True,  'poe': False},
    'hAP ax3 (C53UiG+)':      {'ports': 5, 'wifi': True,  'wifi5g': True,  'poe': True},
    'hEX (RB750Gr3)':         {'ports': 5, 'wifi': False, 'wifi5g': False, 'poe': False},
    'hEX S (RB760iGS)':       {'ports': 5, 'wifi': False, 'wifi5g': False, 'poe': True},
    'RB3011':                 {'ports': 10,'wifi': False, 'wifi5g': False, 'poe': True},
    'RB4011':                 {'ports': 10,'wifi': True,  'wifi5g': True,  'poe': True},
    'CCR1009':                {'ports': 8, 'wifi': False, 'wifi5g': False, 'poe': False},
    'CCR2004':                {'ports': 12,'wifi': False, 'wifi5g': False, 'poe': False},
}

PLANS = {
    'basic': {
        'name': 'Pack Essentiel',
        'subtitle': 'Configuration optimisée standard',
        'price': 50000,
        'currency': 'Ar',
        'features': [
            'Configuration Bridge automatique',
            'Serveur DHCP intégré',
            'Firewall RouterOS v7 sécurisé',
            'DNS Cloudflare 1.1.1.1 optimisé',
            'Normalisation des paquets TCP',
            'Assignation asynchrone des ports',
            'Support technique 30 jours'
        ],
        'color': '#0284c7'
    },
    'warp': {
        'name': 'Pack Premium Cloudflare',
        'subtitle': 'Débit illimité & stabilité maximale',
        'price': 100000,
        'currency': 'Ar',
        'features': [
            'Tout le Pack Essentiel inclus',
            'Tunnel Cloudflare Secure WireGuard',
            'Débit illimité sans perte de vitesse',
            'Chiffrement AES-256 professionnel',
            'Latence optimisée mondialement',
            'DNS-over-HTTPS (DoH) intégré',
            'Stabilité multi-clients garantie',
            'Anonymat & confidentialité totale'
        ],
        'color': '#10b981',
        'popular': True
    },
    'hotspot': {
        'name': 'Pack Business WiFi Zone',
        'subtitle': 'Solution complète pour opérateurs',
        'price': 200000,
        'currency': 'Ar',
        'features': [
            'Tout le Pack Premium inclus',
            'Portail Hotspot professionnel',
            'Serveur PPPoE multi-clients',
            'Gestion de bande passante par utilisateur',
            '10 Vouchers pré-générés',
            'Profils tarifaires (1h, 1j, 1sem, 1mois)',
            'File d\'attente PCQ dynamique',
            'Formation à la revente incluse'
        ],
        'color': '#f97316'
    }
}
