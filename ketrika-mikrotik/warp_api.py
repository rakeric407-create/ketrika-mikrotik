# warp_api.py - KETRIKA MIKROTIK - Générateur Script Pro (Cloudflare WARP)
import os
import secrets
import base64
import requests

# =======================================================
# MOTEUR CRYPTOGRAPHIQUE X25519 PURE PYTHON (RFC 7748)
# =======================================================
P = 2**255 - 19
A24 = 121665

def _clamp(key_bytes):
    key = bytearray(key_bytes)
    key[0] &= 248
    key[31] &= 127
    key[31] |= 64
    return bytes(key)

def _x25519(k, u):
    k_int = int.from_bytes(_clamp(k), 'little')
    x_1 = int.from_bytes(u, 'little')
    x_2, z_2, x_3, z_3, swap = 1, 0, x_1, 1, 0

    for t in reversed(range(255)):
        k_t = (k_int >> t) & 1
        swap ^= k_t
        if swap:
            x_2, x_3 = x_3, x_2
            z_2, z_3 = z_3, z_2
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
        x_3 = ((DA + CB) ** 2) % P
        z_3 = (x_1 * ((DA - CB) ** 2)) % P
        x_2 = (AA * BB) % P
        z_2 = (E * (AA + (A24 * E))) % P

    if swap:
        x_2, x_3 = x_3, x_2
        z_2, z_3 = z_3, z_2

    result = (x_2 * pow(z_2, P - 2, P)) % P
    return result.to_bytes(32, 'little')

def generate_wireguard_keys():
    """Génère une paire de clés WireGuard (X25519) sans aucune dépendance C/Rust"""
    raw_priv = secrets.token_bytes(32)
    clamped_priv = _clamp(raw_priv)
    base_point = (9).to_bytes(32, 'little')
    raw_pub = _x25519(clamped_priv, base_point)
    priv_b64 = base64.b64encode(clamped_priv).decode('utf-8')
    pub_b64 = base64.b64encode(raw_pub).decode('utf-8')
    return priv_b64, pub_b64

def register_warp_account(public_key):
    """Enregistrement auto sur l'API Cloudflare Secure Tunnel"""
    url = "https://api.cloudflareclient.com/v0a2158/reg"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "okhttp/3.12.1",
        "CF-Client-Version": "a-6.30-3596",
    }
    payload = {
        "key": public_key,
        "install_id": secrets.token_hex(11),
        "fcm_token": "",
        "tos": "2024-01-01T00:00:00.000Z",
        "model": "PC",
        "serial_number": secrets.token_hex(16),
        "locale": "en_US"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=8)
        if res.status_code in (200, 201):
            data = res.json()
            return {
                'success': True,
                'client_ipv4': data['config']['interface']['addresses']['v4'],
                'warp_public_key': data['config']['peers'][0]['public_key'],
                'endpoint': data['config']['peers'][0]['endpoint']['host']
            }
    except Exception as e:
        print(f"Info Cloudflare API: {e}")
    return {'success': False}

def generate_warp_config_for_client():
    """Génère la config Cloudflare Secure Tunnel personnalisée par client"""
    priv_b64, pub_b64 = generate_wireguard_keys()
    warp_info = register_warp_account(pub_b64)
    
    if not warp_info or not warp_info.get('success'):
        return {
            'success': False,
            'private_key': priv_b64,
            'client_ipv4': '172.16.0.2',
            'warp_public_key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
            'endpoint_host': 'engage.cloudflareclient.com',
            'endpoint_port': '2408'
        }
    
    endpoint = warp_info['endpoint']
    host, port = endpoint.rsplit(':', 1) if ':' in endpoint else (endpoint, '2408')
    
    return {
        'success': True,
        'private_key': priv_b64,
        'client_ipv4': warp_info['client_ipv4'],
        'warp_public_key': warp_info['warp_public_key'],
        'endpoint_host': host,
        'endpoint_port': port
    }

# =======================================================
# DÉTECTION HARDWARE MIKROTIK
# =======================================================
def format_limit(value):
    if value in ('nolimit', '0', '', None):
        return '0'
    return str(value)

def is_ax_model(model_name):
    return any(k in model_name for k in ['ax', 'AX', 'C52', 'C53', 'hAP ax'])

def is_wifi_model(model_name):
    return not any(k in model_name for k in ['hEX', 'RB750', 'RB760', 'RB3011', 'CCR'])

def has_5ghz(model_name):
    return not any(k in model_name for k in ['hAP lite', 'RB941']) and is_wifi_model(model_name)

def generate_wifi_config(order):
    model = order.mikrotik_model
    ssid = order.ssid or "WiFiZone-Ketrika"
    password = order.wifi_password or "Ketrika2024"

    if not is_wifi_model(model):
        return "\n# Modèle Ethernet pur (sans carte WiFi intégrée)\n"

    if is_ax_model(model):
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI AX ===
:do {{
    /interface wifi set wlan1 configuration.mode=ap configuration.ssid="{ssid}" \\
        security.authentication-types=wpa2-psk security.passphrase="{password}" \\
        channel.frequency=2412 channel.width=20/40mhz-Ce disabled=no
}} on-error={{}}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wifi set wlan2 configuration.mode=ap configuration.ssid="{ssid}-5G" \\
        security.authentication-types=wpa2-psk security.passphrase="{password}" \\
        channel.frequency=5180 channel.width=20/40/80mhz-Ceee disabled=no
}} on-error={{}}
"""
    else:
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI AC ===
:do {{
    /interface wireless set wlan1 mode=ap-bridge ssid="{ssid}" wireless-protocol=802.11 \\
        frequency=2412 band=2ghz-b/g/n channel-width=20/40mhz-Ce disabled=no
    /interface wireless security-profiles set [find default=yes] authentication-types=wpa2-psk \\
        wpa2-pre-shared-key="{password}" mode=dynamic-keys
}} on-error={{}}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wireless set wlan2 mode=ap-bridge ssid="{ssid}-5G" wireless-protocol=802.11 \\
        frequency=5180 band=5ghz-a/n/ac channel-width=20/40/80mhz-Ceee disabled=no
}} on-error={{}}
"""
    return cfg

# =======================================================
# GÉNÉRATEUR GLOBAL DE SCRIPT .RSC (ULTRA-STABLE)
# =======================================================
def generate_full_script(order):
    from database import MIKROTIK_MODELS

    info = MIKROTIK_MODELS.get(order.mikrotik_model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    ports = info['ports']
    wan = order.wan_interface or 'ether1'
    gw = order.lan_gateway or '192.168.88.1'
    net = order.lan_network or '192.168.88.0/24'
    pool = order.dhcp_pool or '192.168.88.10-192.168.88.250'
    ttl = order.ttl_value or 65
    dl = format_limit(order.dl_limit)
    ul = format_limit(order.ul_limit)
    is_hotspot = (order.plan_type == 'hotspot')
    needs_warp = order.plan_type in ('warp', 'hotspot')

    lan_ports = [f"ether{i}" for i in range(2, ports + 1)]

    # Attribution asynchrone des ports (ZÉRO déconnexion)
    bp_inner = ""
    for p in lan_ports:
        bp_inner += f"/interface bridge port add bridge=bridge1 interface={p}; "
    if is_wifi_model(order.mikrotik_model):
        bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan1; "
        if has_5ghz(order.mikrotik_model):
            bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan2; "

    scheduler_cmd = f"""
# === ASSIGNATION ASYNCHRONE DES PORTS ===
/system scheduler add name=ketrika_setup interval=0s start-time=([/system clock get time] + 00:00:04) on-event="\\
    {bp_inner} \\
    /system scheduler remove ketrika_setup;"
"""

    wcfg = generate_wifi_config(order)

    if dl == '0':
        rl = "\n# Mode Illimité : Pas de bridage - Débit maximum stable garanti\n"
    else:
        rl = f"""
# === GESTION DE BANDE PASSANTE MULTI-CLIENTS ===
:do {{
    /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl}
    /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul}
    /queue simple add name="KETRIKA-Speed" target={net} queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] QoS"
}} on-error={{}}
"""

    # Cloudflare Secure Tunnel
    warp = ""
    if needs_warp:
        warp_cfg = generate_warp_config_for_client()
        warp = f"""
# =============================================
# ☁️ CLOUDFLARE SECURE TUNNEL (Débit Illimité & Stable)
# =============================================
:do {{
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1420 private-key="{warp_cfg['private_key']}" comment="[KETRIKA] Secure Tunnel"
    /interface wireguard peers add interface=wg-secure public-key="{warp_cfg['warp_public_key']}" endpoint-address={warp_cfg['endpoint_host']} endpoint-port={warp_cfg['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={warp_cfg['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA] Tunnel IP"
    /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address=!{net} action=mark-routing new-routing-mark=via-secure passthrough=yes comment="[KETRIKA] Traffic marking"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure comment="[KETRIKA] Secure route"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="[KETRIKA] Tunnel NAT"
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes servers=1.1.1.1,1.0.0.1
}} on-error={{}}
"""

    # Hotspot
    hotspot = ""
    if is_hotspot:
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        hotspot = f"""
# =============================================
# 🌐 PORTAIL HOTSPOT WIFI ZONE
# =============================================
:do {{ /ip dhcp-server remove [find interface=bridge1 name=dhcp-lan] }} on-error={{}}
:delay 1s
:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" hotspot-address={gw} login-by=http-chap,http-pap name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure {rl_hs} shared-users=1 session-timeout=1h idle-timeout=5m
    /ip hotspot user profile add name=1jour {rl_hs} shared-users=2 session-timeout=1d idle-timeout=10m
    /ip hotspot user profile add name=1semaine {rl_hs} shared-users=3 session-timeout=7d idle-timeout=15m
    /ip hotspot user profile add name=1mois {rl_hs} shared-users=3 session-timeout=30d idle-timeout=30m
    /ip hotspot user add name=admin password=admin123 profile=1mois comment="Admin"
}} on-error={{}}
"""
        if order.pppoe_enabled:
            rl_ppp = f"rate-limit={ul}/{dl}" if dl != '0' else ""
            hotspot += f"""
# === SERVEUR PPPoE ===
:do {{
    /ip pool add name=pool-pppoe ranges=192.168.99.10-192.168.99.250
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 name=pppoe-ketrika {rl_ppp} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika disabled=no interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
}} on-error={{}}
"""
        if order.voucher_enabled:
            hotspot += "\n# === VOUCHERS PRÉ-GÉNÉRÉS ===\n/ip hotspot user\n"
            for _ in range(10):
                c = secrets.token_hex(4).upper()
                hotspot += f'add name=V-{c} password={c} profile=1heure comment="Voucher 1H"\n'

    if is_hotspot:
        dhcp_section = f":do {{ /ip pool add name=pool-lan ranges={pool} }} on-error={{}}"
    else:
        dhcp_section = f"""
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24
}} on-error={{}}
"""

    rsc = f"""# =============================================
# KETRIKA MIKROTIK - Script Automatique
# Pack : {order.plan_type.upper()} | Matériel : {order.mikrotik_model}
# Licence : {order.license_key}
# =============================================

:put "Configuration KETRIKA en cours d'application..."
:delay 1s

# 1. BRIDGE PRINCIPAL
:do {{ /interface bridge add name=bridge1 protocol-mode=none comment="LAN" }} on-error={{}}

# 2. ADRESSE IP LAN
:do {{ /ip address add address={gw}/24 interface=bridge1 comment="Gateway" }} on-error={{}}

# 3. CLIENT DHCP WAN
:do {{ /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no }} on-error={{}}

# 4. SERVEUR DHCP LAN
{dhcp_section}

# 5. CONFIGURATION SANS FIL
{wcfg}

# 6. ATTRIBUTION ASYNCHRONE DES PORTS
{scheduler_cmd}

# 7. DNS SÉCURISÉ & NAT
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8
:do {{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade }} on-error={{}}

# 8. OPTIMISATION RÉSEAU AVANCÉE
:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL Norm"
    /ip firewall mangle add chain=prerouting in-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn action=change-mss new-mss=clamp-to-pmtu passthrough=yes
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp action=change-mss new-mss=1360 passthrough=yes
    /ip firewall filter add chain=forward out-interface={wan} protocol=icmp action=drop
    /ip firewall filter add chain=output out-interface={wan} protocol=icmp action=drop
    /ip firewall filter add chain=input connection-state=established,related action=accept
    /ip firewall filter add chain=input connection-state=invalid action=drop
    /ip firewall filter add chain=forward connection-state=established,related action=accept
    /ip firewall filter add chain=forward connection-state=invalid action=drop
    /ip firewall filter add chain=forward in-interface=bridge1 out-interface={wan} action=accept
}} on-error={{}}
{warp}{hotspot}{rl}
:put "================================================"
:put "  KETRIKA - Installation Réussie !"
:put "  Licence : {order.license_key}"
:put "  Configuration opérationnelle en 4 secondes"
:put "================================================"
"""
    return rsc
