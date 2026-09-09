#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Base de données et dictionnaire de modèles
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Order(db.Model):
    """Modèle de commande client"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    license_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    client_name = db.Column(db.String(200), nullable=False)
    whatsapp_number = db.Column(db.String(50), nullable=False)
    plan_type = db.Column(db.String(20), nullable=False, default='standard')
    mikrotik_model = db.Column(db.String(100), nullable=False)
    ssid = db.Column(db.String(100), default='KETRIKA-WiFi')
    wifi_password = db.Column(db.String(100), default='12345678')
    wan_interface = db.Column(db.String(50), default='ether1')
    lan_gateway = db.Column(db.String(50), default='192.168.88.1')
    lan_network = db.Column(db.String(50), default='192.168.88.0/24')
    dhcp_pool = db.Column(db.String(100), default='192.168.88.10-192.168.88.250')
    ttl_value = db.Column(db.String(10), default='64')
    dl_limit = db.Column(db.String(20), default='0')
    ul_limit = db.Column(db.String(20), default='0')
    pppoe_enabled = db.Column(db.Boolean, default=False)
    voucher_enabled = db.Column(db.Boolean, default=True)
    
    # NOUVEAUX CHAMPS
    router_name = db.Column(db.String(100), default='')  # Nom personnalisé du routeur
    mac_spoof = db.Column(db.Boolean, default=False)  # Activer changement MAC
    mac_address = db.Column(db.String(20), default='')  # MAC générée
    sleep_mode = db.Column(db.String(20), default='off')  # off, 00-06, 01-05, 23-07, 02-06
    client_limit = db.Column(db.String(20), default='0')  # Limite par client (Mbps)
    
    payment_proof = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Order {self.order_id}>'


def get_next_lan_subnet():
    """Génère un sous-réseau LAN unique pour chaque nouveau client."""
    try:
        last_order = Order.query.order_by(Order.id.desc()).first()
        if last_order and last_order.lan_gateway:
            parts = last_order.lan_gateway.split('.')
            if len(parts) == 4:
                third_octet = int(parts[2]) + 1
                if third_octet > 254 or third_octet < 10:
                    third_octet = 10
            else:
                third_octet = 10
        else:
            third_octet = 10
    except Exception:
        third_octet = 10

    return {
        'gateway': f'192.168.{third_octet}.1',
        'network': f'192.168.{third_octet}.0/24',
        'pool': f'192.168.{third_octet}.10-192.168.{third_octet}.250'
    }


# Dictionnaire complet des modèles MikroTik
MIKROTIK_MODELS = {
    'hap_lite': {'name': 'hAP lite (RB941-2nD)', 'eth_ports': 4, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n', 'wifi_iface': 'wlan1'},
    'hap': {'name': 'hAP (RB951Ui-2nD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n', 'wifi_iface': 'wlan1'},
    'hap_ac_lite': {'name': 'hAP ac lite (RB952Ui-5ac2nD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'hap_ac2': {'name': 'hAP ac² (RB952Ui-5ac2nD-TC)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'hap_ac3': {'name': 'hAP ac³ (RBD53iG-5HacD2HnD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'hap_ax_lite': {'name': 'hAP ax lite (L41G-2axD)', 'eth_ports': 4, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'hap_ax2': {'name': 'hAP ax² (C52iG-5HaxD2HaxD-TC)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'hap_ax3': {'name': 'hAP ax³ (C53UiG+5HPaxD2HPaxD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'cap_ac': {'name': 'cAP ac (RBcAPGi-5acD2nD)', 'eth_ports': 2, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'cap_ax': {'name': 'cAP ax (CAPGi-5HaxD2HaxD)', 'eth_ports': 2, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'wap_ac': {'name': 'wAP ac (RBwAPG-5HacT2HnD)', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'wap_ax': {'name': 'wAP ax (L11UG-5HaxD)', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'chateau_ax': {'name': 'Chateau ax (S53UG+5HaxD2HaxD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'chateau_lte6': {'name': 'Chateau LTE6 (D53G-5HacD2HnD-TC&EG12)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'audience': {'name': 'Audience (RBD25G-5HPacQD2HPnD)', 'eth_ports': 2, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'hex': {'name': 'hEX (RB750Gr3)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'hex_s': {'name': 'hEX S (RB760iGS)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'hex_lite': {'name': 'hEX lite (RB750r2)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'hex_poe': {'name': 'hEX PoE (RB960PGS)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'rb2011': {'name': 'RB2011UiAS-2HnD-IN', 'eth_ports': 10, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n', 'wifi_iface': 'wlan1'},
    'rb3011': {'name': 'RB3011UiAS-RM', 'eth_ports': 10, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'rb4011': {'name': 'RB4011iGS+RM', 'eth_ports': 10, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'rb5009': {'name': 'RB5009UG+S+IN', 'eth_ports': 8, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'ccr2004': {'name': 'CCR2004-1G-12S+2XS', 'eth_ports': 1, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'ccr2116': {'name': 'CCR2116-12G-4S+', 'eth_ports': 12, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'l009': {'name': 'L009UiGS-RM', 'eth_ports': 8, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None},
    'l009_wifi': {'name': 'L009UiGS-2HaxD-IN', 'eth_ports': 8, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'},
    'ltap_lte6': {'name': 'LtAP LTE6 kit', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n', 'wifi_iface': 'wlan1'},
    'sxtsq_5ac': {'name': 'SXTsq 5 ac (RBSXTsqG-5acD)', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
    'omnitik_5ac': {'name': 'OmniTIK 5 ac (RBOmniTikPG-5HacD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'},
}


def get_model_info(model_key):
    """Retourne les caractéristiques d'un modèle de routeur avec détection intelligente"""
    if model_key in MIKROTIK_MODELS:
        return MIKROTIK_MODELS[model_key]
    
    m_lower = str(model_key).lower()
    
    # Détection AX (WiFi 6)
    if 'ax' in m_lower:
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax', 'wifi_iface': 'wifi1'}
    # Détection AC (WiFi 5)
    elif 'ac' in m_lower or 'dual' in m_lower:
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac', 'wifi_iface': 'wlan1'}
    # Détection modèles sans WiFi
    elif any(x in m_lower for x in ['hex', 'rb750', 'rb760', 'rb3011', 'rb4011', 'rb5009', 'ccr', 'l009r', 'crs']):
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none', 'wifi_iface': None}
    
    # Par défaut : WiFi N basique
    return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n', 'wifi_iface': 'wlan1'}


def generate_random_mac():
    """Génère une adresse MAC aléatoire réaliste (préfixe Vendor commun)"""
    import random
    # Préfixes OUI communs de fabricants (pour paraître légitime)
    vendors = [
        '00:1A:2B',  # Apple
        '00:16:CB',  # Apple
        '3C:22:FB',  # Apple
        'A4:5E:60',  # Apple
        '00:26:BB',  # Apple
        'AC:BC:32',  # Apple
        '00:23:15',  # Intel
        '00:15:00',  # Intel
        '00:1F:3C',  # Intel
        '00:24:D7',  # Intel
    ]
    prefix = random.choice(vendors)
    suffix = ':'.join(['%02X' % random.randint(0, 255) for _ in range(3)])
    return f"{prefix}:{suffix}"


def generate_router_name(license_key):
    """Génère un nom de routeur aléatoire crédible"""
    import random
    prefixes = ['HOME', 'OFFICE', 'HOTEL', 'WIFI', 'NET', 'ROUTER', 'BOX', 'CONNECT']
    prefix = random.choice(prefixes)
    suffix = license_key[-4:] if license_key else str(random.randint(1000, 9999))
    return f"{prefix}-{suffix}"
