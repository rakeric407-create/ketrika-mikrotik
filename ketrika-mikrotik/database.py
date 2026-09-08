# database.py - Modèles KETRIKA avec système de licence intelligent
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
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
    license_duration = db.Column(db.String(20), default='lifetime')  # lifetime, 1year, 6months, 3months
    valid_until = db.Column(db.DateTime)  # NULL = à vie
    validated_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)

    script_content = db.Column(db.Text)

    def generate_order_id(self):
        self.order_id = f"KTK-{datetime.now().strftime('%y%m%d')}-{secrets.token_hex(3).upper()}"

    def generate_license_key(self):
        h = secrets.token_hex(8).upper()
        self.license_key = f"KTK-{h[:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"

    def set_license_duration(self, duration):
        """Définit la durée de validité de la licence"""
        self.license_duration = duration
        if duration == 'lifetime':
            self.valid_until = None
        elif duration == '1year':
            self.valid_until = datetime.utcnow() + timedelta(days=365)
        elif duration == '6months':
            self.valid_until = datetime.utcnow() + timedelta(days=180)
        elif duration == '3months':
            self.valid_until = datetime.utcnow() + timedelta(days=90)

    @property
    def is_license_valid(self):
        """Vérifie si la licence est encore valide"""
        if not self.license_key:
            return False
        if self.valid_until is None:
            return True  # Licence à vie
        return datetime.utcnow() < self.valid_until

    @property
    def days_remaining(self):
        """Nombre de jours restants sur la licence"""
        if self.valid_until is None:
            return "À vie ♾️"
        delta = self.valid_until - datetime.utcnow()
        if delta.days < 0:
            return "Expirée"
        return f"{delta.days} jours"

    @property
    def status_badge(self):
        return {
            'pending': '🟡 En attente',
            'validated': '🟢 Validé',
            'delivered': '✅ Livré',
            'rejected': '🔴 Rejeté',
            'expired': '⏰ Expiré'
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

# Options de durée de licence avec supplément de prix
LICENSE_DURATIONS = {
    '3months':  {'label': '3 mois',        'days': 90,   'price_add': 0},
    '6months':  {'label': '6 mois',        'days': 180,  'price_add': 5000},
    '1year':    {'label': '1 an',          'days': 365,  'price_add': 10000},
    'lifetime': {'label': 'À vie ♾️',      'days': None, 'price_add': 20000},
}

PLANS = {
    'basic': {
        'name': 'Pack Essentiel',
        'subtitle': 'Configuration standard optimisée',
        'price': 30000,
        'currency': 'Ar',
        'features': [
            'Configuration Bridge automatique',
            'Serveur DHCP intégré',
            'Firewall RouterOS v7 sécurisé',
            'DNS Cloudflare 1.1.1.1',
            'Normalisation TCP/MSS',
            'Attribution asynchrone des ports',
            'Support WhatsApp 30 jours'
        ],
        'color': '#0284c7'
    },
    'warp': {
        'name': 'Pack Premium Cloudflare',
        'subtitle': 'Débit illimité & stabilité',
        'price': 50000,
        'currency': 'Ar',
        'features': [
            'Tout le Pack Essentiel inclus',
            'Cloudflare Secure Tunnel',
            'Débit illimité sans perte',
            'Chiffrement AES-256',
            'Latence optimisée mondiale',
            'DNS-over-HTTPS intégré',
            'Multi-clients stable',
            'Confidentialité totale'
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
            'Tout le Pack Premium inclus',
            'Portail Hotspot professionnel',
            'Serveur PPPoE multi-clients',
            'QoS par utilisateur',
            '10 Vouchers pré-générés',
            'Profils (1h/1j/1sem/1mois)',
            'Queue PCQ dynamique',
            'Formation revente incluse'
        ],
        'color': '#f97316'
    }
}

# Coordonnées de paiement
PAYMENT_INFO = {
    'mvola':   {'number': '038 28 171 00', 'name': 'Jean Eric', 'label': 'MVola'},
    'orange':  {'number': '037 39 755 72', 'name': 'Jean Eric', 'label': 'Orange Money'},
    'whatsapp':{'number': '038 28 171 00', 'name': 'Jean Eric', 'label': 'WhatsApp Support'},
}
