#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - API Cloudflare WARP et Générateur de Scripts RouterOS v7
"""

import os
import re
import json
import random
import string
import base64
import time
import hashlib

# Clé publique Cloudflare WARP officielle
CF_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

def safe_get(obj, key, default=''):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default

def curve25519_scalarmult(scalar):
    """Calcul de clé publique Curve25519 pure-Python (évite la dépendance externe)"""
    P = 2**255 - 19
    def dec(s): return int.from_bytes(s, 'little')
    def enc(u): return (u % P).to_bytes(32, 'little')
    def inv(x): return pow(x, P - 2, P)

    k = bytearray(scalar)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64

    u = 9
    x_1 = u
    x_2 = 1
    z_2 = 0
    x_3 = u
    z_3 = 1
    swap = 0
    k_int = dec(k)

    for t in range(254, -1, -1):
        k_t = (k_int >> t) & 1
        swap ^= k_t
        # Conditional swap
        dummy = swap * (x_2 ^ x_3)
        x_2 ^= dummy
        x_3 ^= dummy
        dummy = swap * (z_2 ^ z_3)
        z_2 ^= dummy
        z_3 ^= dummy
        swap = k_t

        A = (x_2 + z_2) % P
        AA = (A * A) % P
        B = (x_2 - z_2) % P
        BB = (B * B) % P
        E = (AA - BB) % P
        C = (x_3 + z_3) % P
        D = (x_3 - z_3) % P
        DA = (D * A) % P
        CB = (C * B) % P
        x_3 = pow(DA + CB, 2, P)
        z_3 = (x_1 * pow(DA - CB, 2, P)) % P
        x_2 = (AA * BB) % P
        z_2 = (E * (AA + 121665 * E)) % P

    # Final swap
    dummy = swap * (x_2 ^ x_3)
    x_2 ^= dummy
    x_3 ^= dummy
    dummy = swap * (z_2 ^ z_3)
    z_2 ^= dummy
    z_3 ^= dummy

    return enc((x_2 * inv(z_2)) % P)

def generate_wireguard_keys():
    """Génère un couple de clés WireGuard valide"""
    priv = os.urandom(32)
    pub = curve25519_scalarmult(priv)
    return {
        'private_key': base64.b64encode(priv).decode('utf-8'),
        'public_key': base64.b64encode(pub).decode('utf-8')
    }

def register_warp(public_key):
    """Enregistre le client auprès de l'API Cloudflare WARP"""
    try:
        import requests
        url = "https://api.cloudflareclient.com/v0a2158/reg"
        headers = {"Content-Type": "application/json", "User-Agent": "okhttp/3.12.1"}
        payload = {
            "key": public_key,
            "install_id": "",
            "fcm_token": "",
            "tos": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "model": "MikroTik",
            "serial_number": hashlib.md5(public_key.encode()).hexdigest()[:16],
            "locale": "fr_MG"
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in [200, 201]:
            data = r.json()
            ipv4 = data.get("config", {}).get("interface", {}).get("addresses", {}).get("v4", "172.16.0.2")
            if '/' in ipv4:
                ipv4 = ipv4.split('/')[0]
            return {"success": True, "ipv4": ipv4}
    except Exception:
        pass
    return {"success": False, "ipv4": f"172.16.0.{random.randint(2,254)}"}

def generate_script(order):
    """Générateur de scripts RouterOS v7"""
    plan = safe_get(order, 'plan_type', 'standard')
    model = safe_get(order, 'mikrotik_model', 'hap_ac2')
    ssid = safe_get(order, 'ssid', 'KETRIKA-WiFi')
    wifi_pass = safe_get(order, 'wifi_password', 'ketrika2024')
    wan = safe_get(order, 'wan_interface', 'ether1')
    gw = safe_get(order, 'lan_gateway', '192.168.10.1')
    net = safe_get(order, 'lan_network', '192.168.10.0/24')
    pool = safe_get(order, 'dhcp_pool', '192.168.10.10-192.168.10.250')
    ttl = safe_get(order, 'ttl_value', '64')
    dl = safe_get(order, 'dl_limit', '0')
    ul = safe_get(order, 'ul_limit', '0')
    lic = safe_get(order, 'license_key', 'DEMO')

    from database import get_model_info
    info = get_model_info(model)
    wifi_type = info['wifi_type']

    # Clés et IP WARP
    keys = generate_wireguard_keys()
    warp_reg = register_warp(keys['public_key'])
    warp_ip = warp_reg['ipv4']
    endpoints = ["162.159.192.1", "162.159.193.1", "188.114.96.1", "188.114.97.1"]
    ports = [500, 853, 4500, 2408]
    endpoint = f"{random.choice(endpoints)}:{random.choice(ports)}"

    # 1. EN-TÊTE DU SCRIPT
    script_parts = []
    script_parts.append(f"""# ============================================================
# KETRIKA MIKROTIK - SCRIPT DE CONFIGURATION AUTOMATIQUE v7
# LICENCE : {lic}
# SYSTEME : RouterOS v7
# ============================================================

# --- Nettoyage complet ---
/ip firewall filter remove [find]
/ip firewall nat remove [find]
/ip firewall mangle remove [find]
/queue simple remove [find]
/ip dhcp-server remove [find]
/ip dhcp-server network remove [find]
/ip pool remove [find]
/interface bridge remove [find]
/ip address remove [find]
/ip route remove [find]
/ip dns set servers=""
/interface wireguard remove [find]
/routing table remove [find]
/routing rule remove [find]
/ip hotspot remove [find]
/ip hotspot profile remove [find]
/ip hotspot user remove [find]

# --- Création du Bridge ---
/interface bridge add name=bridge1 comment="LAN-KETRIKA"
""")

    # 2. ADJONCTION DES PORTS PHYSIQUES AU BRIDGE
    for i in range(1, info['eth_ports'] + 1):
        p = f"ether{i}"
        if p != wan:
            script_parts.append(f'/system scheduler add name="br-{p}" start-time=startup interval=0 on-event="/interface bridge port add bridge=bridge1 interface={p}; /system scheduler remove br-{p}"')

    # 3. RÉSEAU DE BASE
    script_parts.append(f"""
# --- Connexion Internet (Client DHCP sur port WAN) ---
/ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no

# --- Adresse IP Passerelle ---
/ip address add address={gw}/24 interface=bridge1

# --- Pool d'adresses et Serveur DHCP ---
/ip pool add name=pool-lan ranges={pool}
/ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no
/ip dhcp-server network add address={net} gateway={gw} dns-server={gw}

# --- Serveur DNS Sécurisé (Cloudflare DoH) ---
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server=https://cloudflare-dns.com/dns-query
""")

    # 4. CONFIGURATION WI-FI DÉTECTÉE
    if wifi_type == 'ax':
        script_parts.append(f"""
# --- Config WiFi 6 (AX) ---
/interface wifi set wifi1 configuration.ssid="{ssid}" configuration.country=madagascar security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="{wifi_pass}" disabled=no
/system scheduler add name="br-wifi1" start-time=startup interval=0 on-event="/interface bridge port add bridge=bridge1 interface=wifi1; /system scheduler remove br-wifi1"
""")
    elif wifi_type in ['ac', 'n']:
        script_parts.append(f"""
# --- Config WiFi 5 (AC) ---
/interface wireless set wlan1 mode=ap-bridge ssid="{ssid}" frequency=auto security-profile=default disabled=no
/interface wireless security-profiles set default mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}"
/system scheduler add name="br-wlan1" start-time=startup interval=0 on-event="/interface bridge port add bridge=bridge1 interface=wlan1; /system scheduler remove br-wlan1"
""")

    # 5. CONFIGURATION VPN WARP (SI PACK SÉCURITÉ OU HOTSPOT)
    if plan in ['warp', 'hotspot']:
        script_parts.append(f"""
# --- Tunnel Chiffré WireGuard WARP ---
/interface wireguard add name=wg-secure mtu=1280 listen-port=0 private-key="{keys['private_key']}" comment="WARP-KETRIKA"
/ip address add address={warp_ip}/32 interface=wg-secure
/interface wireguard peers add interface=wg-secure public-key="{CF_PUBLIC_KEY}" endpoint-address={endpoint.split(':')[0]} endpoint-port={endpoint.split(':')[1]} allowed-address=0.0.0.0/0 persistent-keepalive=25

# --- Routage Avancé (Table Dédiée) ---
/routing table add name=via-secure fib
/routing rule add src-address={net} action=lookup table=via-secure
/routing rule add dst-address={net} action=lookup-only-in-table table=main
/ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure

# --- Masquage & Anti-Fuite DNS ---
/ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade
/ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect
/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect

# --- Optimisation MSS (Anti-DPI / Starlink) ---
/ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes
""")

    # 6. PORTAIL CAPTIF (SI PACK HOTSPOT)
    if plan == 'hotspot':
        script_parts.append(f"""
# --- Portail Captif WiFi Zone ---
/ip dns static add name=wifi.ketrika.mg address={gw}
/ip hotspot profile add name=ketrika-hotspot hotspot-address={gw} dns-name=wifi.ketrika.mg login-by=http-pap,cookie http-cookie-lifetime=1d use-radius=no
/ip hotspot add name=hotspot-ketrika interface=bridge1 profile=ketrika-hotspot address-pool=pool-lan disabled=no

# --- Profils de Vitesse ---
/ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1
/ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2
/ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3

# --- Génération de 10 Vouchers de test ---
""")
        # Injection sécurisée des vouchers
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            script_parts.append(f'/ip hotspot user add name="{vc}" password="{vc}" profile="1jour" comment="Ticket-Test"')

        script_parts.append("""
# --- Firewall Blocage P2P / Torrents ---
/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6999 action=drop
/ip firewall filter add chain=forward protocol=udp dst-port=6881-6999 action=drop
""")

    # 7. SÉCURITÉ STANDARD ET TTL MASQUAGE
    script_parts.append(f"""
# --- Règles de NAT & Sécurité standard ---
/ip firewall nat add chain=srcnat out-interface={wan} action=masquerade
""")

    if str(ttl) != '0':
        script_parts.append(f'/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:{ttl} passthrough=yes')

    # 8. QOS
    if dl != '0' or ul != '0':
        lim_ul = f"{ul}" if 'M' in str(ul) else f"{ul}M"
        lim_dl = f"{dl}" if 'M' in str(dl) else f"{dl}M"
        script_parts.append(f'/queue simple add name="QoS-Global" target={net} max-limit={lim_ul}/{lim_dl}')

    # 9. PIED DE PAGE ET REBOOT AUTOMATIQUE
    script_parts.append(f"""
# --- Changement d'identité ---
/system identity set name="KETRIKA-{lic[-4:]}"

# --- Redémarrage automatique propre (3 secondes de sursis) ---
/system scheduler add name="reboot-auto" start-time=startup interval=3s on-event="/system reboot; /system scheduler remove reboot-auto"
:delay 1s
/system scheduler set reboot-auto start-time=[/system clock get time]
""")

    # Jointure de toutes les sections de façon propre et unifiée
    return "\n".join(script_parts)
