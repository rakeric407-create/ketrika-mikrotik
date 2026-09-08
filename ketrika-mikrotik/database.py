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
    payment_proof = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Order {self.order_id}>'

def get_next_lan_subnet():
    """
    Génère un sous-réseau LAN unique pour chaque nouveau client.
    Incrémente automatiquement le 3ème octet de l'IP (192.168.10.1, 192.168.11.1, etc.)
    """
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

# Dictionnaire complet de tous les modèles MikroTik existants
MIKROTIK_MODELS = {
    'hap_lite': {'name': 'hAP lite (RB941-2nD)', 'eth_ports': 4, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n'},
    'hap_lite_tc': {'name': 'hAP lite TC (RB941-2nD-TC)', 'eth_ports': 4, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n'},
    'hap': {'name': 'hAP (RB951Ui-2nD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n'},
    'hap_ac_lite': {'name': 'hAP ac lite (RB952Ui-5ac2nD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'},
    'hap_ac2': {'name': 'hAP ac² (RB952Ui-5ac2nD-TC)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'},
    'hap_ac3': {'name': 'hAP ac³ (RBD53iG-5HacD2HnD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'},
    'hap_ax_lite': {'name': 'hAP ax lite (L41G-2axD)', 'eth_ports': 4, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'ax'},
    'hap_ax2': {'name': 'hAP ax² (C52iG-5HaxD2HaxD-TC)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax'},
    'hap_ax3': {'name': 'hAP ax³ (C53UiG+5HPaxD2HPaxD)', 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax'},
    'cap_ac': {'name': 'cAP ac (RBcAPGi-5acD2nD)', 'eth_ports': 2, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'},
    'cap_ax': {'name': 'cAP ax (CAPGi-5HaxD2HaxD)', 'eth_ports': 2, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax'},
    'wap_ac': {'name': 'wAP ac (RBwAPG-5HacT2HnD)', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'},
    'wap_ax': {'name': 'wAP ax (L11UG-5HaxD)', 'eth_ports': 1, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax'},
    'hex': {'name': 'hEX (RB750Gr3)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'hex_s': {'name': 'hEX S (RB760iGS)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'hex_lite': {'name': 'hEX lite (RB750r2)', 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'rb3011': {'name': 'RB3011UiAS-RM', 'eth_ports': 10, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'rb4011': {'name': 'RB4011iGS+RM', 'eth_ports': 10, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'rb5009': {'name': 'RB5009UG+S+IN', 'eth_ports': 8, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'ccr2004': {'name': 'CCR2004-1G-12S+2XS', 'eth_ports': 1, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'ccr2116': {'name': 'CCR2116-12G-4S+', 'eth_ports': 12, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'l009': {'name': 'L009UiGS-RM', 'eth_ports': 8, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'},
    'l009_wifi': {'name': 'L009UiGS-2HaxD-IN', 'eth_ports': 8, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'ax'}
}

def get_model_info(model_key):
    """Retourne les caractéristiques d'un modèle de routeur"""
    if model_key in MIKROTIK_MODELS:
        return MIKROTIK_MODELS[model_key]
    
    # Détection automatique intelligente si modèle "Autre" saisi manuellement
    m_lower = str(model_key).lower()
    if 'ax' in m_lower:
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ax'}
    elif 'ac' in m_lower or 'dual' in m_lower:
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': True, 'wifi_type': 'ac'}
    elif 'hex' in m_lower or 'rb' in m_lower or 'ccr' in m_lower or 'l009' in m_lower:
        return {'name': model_key, 'eth_ports': 5, 'has_wifi': False, 'has_5ghz': False, 'wifi_type': 'none'}
    
    return {'name': model_key, 'eth_ports': 5, 'has_wifi': True, 'has_5ghz': False, 'wifi_type': 'n'}
