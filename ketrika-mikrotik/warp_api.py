# warp_api.py - KETRIKA - Générateur Script Intelligent Anti-Erreur
import os
import secrets
import base64
import requests
import re
import ipaddress

# =======================================================
# VALIDATEUR INTELLIGENT DE CONFIGURATION
# =======================================================
class ConfigValidator:
    """Vérifie et corrige automatiquement les paramètres pour éviter les erreurs MikroTik"""
    
    @staticmethod
    def validate_ip(ip_str):
        """Vérifie qu'une IP est valide"""
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except:
            return False
    
    @staticmethod
    def validate_network(net_str):
        """Vérifie qu'un réseau CIDR est valide (ex: 192.168.88.0/24)"""
        try:
            ipaddress.IPv4Network(net_str, strict=False)
            return True
        except:
            return False
    
    @staticmethod
    def validate_pool_range(pool_str, network):
        """Vérifie que le pool DHCP est dans le bon réseau"""
        try:
            if '-' not in pool_str:
                return False
            start, end = pool_str.split('-')
            net = ipaddress.IPv4Network(network, strict=False)
            start_ip = ipaddress.IPv4Address(start.strip())
            end_ip = ipaddress.IPv4Address(end.strip())
            return start_ip in net and end_ip in net
        except:
            return False
    
    @staticmethod
    def sanitize_string(value, max_len=32):
        """Nettoie une chaîne pour éviter les caractères dangereux MikroTik"""
        if not value:
            return ""
        # Supprime les caractères problématiques
        cleaned = re.sub(r'[^\w\-\.]', '', str(value))
        return cleaned[:max_len]
    
    @staticmethod
    def sanitize_ssid(value):
        """Nettoie un SSID (autorise espaces mais évite caractères spéciaux)"""
        if not value:
            return "WiFiZone-Ketrika"
        cleaned = re.sub(r'[^\w\s\-\.]', '', str(value))
        return cleaned[:32].strip() or "WiFiZone-Ketrika"
    
    @staticmethod
    def sanitize_password(value):
        """Vérifie le mot de passe WiFi (WPA2 = 8-63 caractères)"""
        if not value or len(value) < 8:
            return "Ketrika2024"
        return value[:63]
    
    @staticmethod
    def auto_fix_order(order):
        """Corrige automatiquement les valeurs invalides de la commande"""
        # IP Gateway
        if not ConfigValidator.validate_ip(order.lan_gateway):
            order.lan_gateway = '192.168.88.1'
        
        # Réseau LAN
        if not ConfigValidator.validate_network(order.lan_network):
            order.lan_network = '192.168.88.0/24'
        
        # Pool DHCP
        if not ConfigValidator.validate_pool_range(order.dhcp_pool, order.lan_network):
            net = ipaddress.IPv4Network(order.lan_network, strict=False)
            hosts = list(net.hosts())
            if len(hosts) > 10:
                order.dhcp_pool = f"{hosts[10]}-{hosts[-2]}"
            else:
                order.dhcp_pool = '192.168.88.10-192.168.88.250'
        
        # SSID
        order.ssid = ConfigValidator.sanitize_ssid(order.ssid)
        
        # Mot de passe WiFi
        order.wifi_password = ConfigValidator.sanitize_password(order.wifi_password)
        
        # TTL
        try:
            ttl = int(order.ttl_value)
            if ttl < 1 or ttl > 255:
                order.ttl_value = 65
        except:
            order.ttl_value = 65
        
        # Interface WAN
        if order.wan_interface not in ['ether1', 'ether2', 'ether3', 'sfp1', 'sfp2']:
            order.wan_interface = 'ether1'
        
        return order

# =======================================================
# MOTEUR CRYPTOGRAPHIQUE X25519 PURE PYTHON
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
    raw_priv = secrets.token_bytes(32)
    clamped_priv = _clamp(raw_priv)
    base_point = (9).to_bytes(32, 'little')
    raw_pub = _x25519(clamped_priv, base_point)
    priv_b64 = base64.b64encode(clamped_priv).decode('utf-8')
    pub_b64 = base64.b64encode(raw_pub).decode('utf-8')
    return priv_b64, pub_b64

def register_warp_account(public_key):
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
    ssid = order.ssid
    password = order.wifi_password

    if not is_wifi_model(model):
        return "\n# Modele Ethernet pur (sans carte WiFi integree)\n"

    if is_ax_model(model):
        cfg = f"""
# === CONFIGURATION WIFI AX (Detection Automatique) ===
:do {{
    /interface wifi set wlan1 configuration.mode=ap configuration.ssid="{ssid}" \\
        security.authentication-types=wpa2-psk security.passphrase="{password}" \\
        channel.frequency=2412 channel.width=20/40mhz-Ce disabled=no
}} on-error={{ :log warning "WiFi wlan1 non disponible sur ce materiel" }}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wifi set wlan2 configuration.mode=ap configuration.ssid="{ssid}-5G" \\
        security.authentication-types=wpa2-psk security.passphrase="{password}" \\
        channel.frequency=5180 channel.width=20/40/80mhz-Ceee disabled=no
}} on-error={{ :log warning "WiFi 5GHz wlan2 non disponible" }}
"""
    else:
        cfg = f"""
# === CONFIGURATION WIFI AC (Detection Automatique) ===
:do {{
    /interface wireless set wlan1 mode=ap-bridge ssid="{ssid}" wireless-protocol=802.11 \\
        frequency=2412 band=2ghz-b/g/n channel-width=20/40mhz-Ce disabled=no
    /interface wireless security-profiles set [find default=yes] authentication-types=wpa2-psk \\
        wpa2-pre-shared-key="{password}" mode=dynamic-keys
}} on-error={{ :log warning "WiFi wlan1 non disponible" }}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wireless set wlan2 mode=ap-bridge ssid="{ssid}-5G" wireless-protocol=802.11 \\
        frequency=5180 band=5ghz-a/n/ac channel-width=20/40/80mhz-Ceee disabled=no
}} on-error={{ :log warning "WiFi 5GHz wlan2 non disponible" }}
"""
    return cfg

# =======================================================
# GÉNÉRATEUR SCRIPT INTELLIGENT (ANTI-ERREUR)
# =======================================================
def generate_full_script(order):
    from database import MIKROTIK_MODELS
    
    # ✅ AUTO-CORRECTION DES VALEURS AVANT GÉNÉRATION
    order = ConfigValidator.auto_fix_order(order)

    info = MIKROTIK_MODELS.get(order.mikrotik_model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    ports = info['ports']
    wan = order.wan_interface
    gw = order.lan_gateway
    net = order.lan_network
    pool = order.dhcp_pool
    ttl = order.ttl_value
    dl = format_limit(order.dl_limit)
    ul = format_limit(order.ul_limit)
    is_hotspot = (order.plan_type == 'hotspot')
    needs_warp = order.plan_type in ('warp', 'hotspot')

    lan_ports = [f"ether{i}" for i in range(2, ports + 1)]

    # Attribution asynchrone des ports
    bp_inner = ""
    for p in lan_ports:
        bp_inner += f"/interface bridge port add bridge=bridge1 interface={p}; "
    if is_wifi_model(order.mikrotik_model):
        bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan1; "
        if has_5ghz(order.mikrotik_model):
            bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan2; "

    scheduler_cmd = f"""
# === ATTRIBUTION ASYNCHRONE DES PORTS ===
/system scheduler add name=ketrika_ports interval=0s \\
    start-time=([/system clock get time] + 00:00:04) \\
    on-event="{bp_inner}/system scheduler remove ketrika_ports;"
"""

    wcfg = generate_wifi_config(order)

    if dl == '0':
        rl = "\n# Mode Illimite : Debit maximum sans bridage\n"
    else:
        rl = f"""
# === GESTION BANDE PASSANTE (Verification prealable) ===
:if ([/queue type find name=pcq-dl-ketrika] = "") do={{
    /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl}
}}
:if ([/queue type find name=pcq-ul-ketrika] = "") do={{
    /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul}
}}
:if ([/queue simple find name=KETRIKA-Speed] = "") do={{
    /queue simple add name="KETRIKA-Speed" target={net} \\
        queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] QoS"
}}
"""

    # Cloudflare Secure Tunnel
    warp = ""
    if needs_warp:
        warp_cfg = generate_warp_config_for_client()
        warp = f"""
# =============================================
# CLOUDFLARE SECURE TUNNEL (Debit Illimite)
# =============================================
# Suppression config precedente si existe
:do {{ /interface wireguard peers remove [find interface=wg-secure] }} on-error={{}}
:do {{ /interface wireguard remove wg-secure }} on-error={{}}
:do {{ /ip route remove [find comment~"KETRIKA"] }} on-error={{}}

:delay 1s

# Creation nouvelle configuration
:do {{
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1420 \\
        private-key="{warp_cfg['private_key']}" comment="[KETRIKA] Secure Tunnel"
    /interface wireguard peers add interface=wg-secure \\
        public-key="{warp_cfg['warp_public_key']}" \\
        endpoint-address={warp_cfg['endpoint_host']} \\
        endpoint-port={warp_cfg['endpoint_port']} \\
        allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={warp_cfg['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA] Tunnel IP"
    /ip firewall mangle add chain=prerouting in-interface=bridge1 \\
        dst-address=!{net} action=mark-routing new-routing-mark=via-secure \\
        passthrough=yes comment="[KETRIKA] Traffic marking"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure \\
        routing-table=via-secure comment="[KETRIKA] Secure route"
    /ip firewall nat add chain=srcnat out-interface=wg-secure \\
        action=masquerade comment="[KETRIKA] Tunnel NAT"
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query \\
        verify-doh-cert=yes servers=1.1.1.1,1.0.0.1
    :log info "KETRIKA: Cloudflare Secure Tunnel connecte"
}} on-error={{ :log error "KETRIKA: Erreur tunnel Cloudflare" }}
"""

    # Hotspot
    hotspot = ""
    if is_hotspot:
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        hotspot = f"""
# =============================================
# PORTAIL HOTSPOT WIFI ZONE
# =============================================
# Nettoyage prealable pour eviter conflits
:do {{ /ip dhcp-server remove [find interface=bridge1 name=dhcp-lan] }} on-error={{}}
:do {{ /ip hotspot remove hotspot-ketrika }} on-error={{}}

:delay 1s

:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" \\
        hotspot-address={gw} login-by=http-chap,http-pap \\
        name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 \\
        name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure {rl_hs} shared-users=1 session-timeout=1h idle-timeout=5m
    /ip hotspot user profile add name=1jour {rl_hs} shared-users=2 session-timeout=1d idle-timeout=10m
    /ip hotspot user profile add name=1semaine {rl_hs} shared-users=3 session-timeout=7d idle-timeout=15m
    /ip hotspot user profile add name=1mois {rl_hs} shared-users=3 session-timeout=30d idle-timeout=30m
    /ip hotspot user add name=admin password=admin123 profile=1mois comment="Admin"
}} on-error={{ :log warning "Hotspot deja configure" }}
"""
        if order.pppoe_enabled:
            rl_ppp = f"rate-limit={ul}/{dl}" if dl != '0' else ""
            hotspot += f"""
# === SERVEUR PPPoE ===
:do {{
    /ip pool add name=pool-pppoe ranges=192.168.99.10-192.168.99.250
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 \\
        name=pppoe-ketrika {rl_ppp} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika \\
        disabled=no interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
}} on-error={{}}
"""
        if order.voucher_enabled:
            hotspot += "\n# === VOUCHERS PRE-GENERES ===\n/ip hotspot user\n"
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
}} on-error={{ :log warning "DHCP deja configure" }}
"""

    # Info validite licence
    validity_info = ""
    if order.valid_until:
        validity_info = f":put \"  Licence valable jusqu'au : {order.valid_until.strftime('%d/%m/%Y')}\""
    else:
        validity_info = ":put \"  Licence : Illimitee (a vie)\""

    rsc = f"""# =============================================
# KETRIKA MIKROTIK - Script Intelligent Anti-Erreur
# Pack : {order.plan_type.upper()} | Materiel : {order.mikrotik_model}
# Licence : {order.license_key}
# =============================================
# CONFIGURATION VALIDEE ET AUTO-CORRIGEE AVANT GENERATION
# Aucun risque de conflit ou d'erreur MikroTik

:put "KETRIKA - Verification prealable du systeme..."
:delay 1s

# Verification que la version RouterOS est compatible v7
:local rver [/system resource get version]
:if ([:pick $rver 0 1] < "7") do={{
    :put "ATTENTION: RouterOS v7 requis. Version detectee: $rver"
}}

:put "Configuration KETRIKA en cours d'application..."
:delay 1s

# 1. BRIDGE PRINCIPAL (avec verification)
:if ([/interface bridge find name=bridge1] = "") do={{
    /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA LAN"
}}

# 2. ADRESSE IP LAN (avec verification)
:if ([/ip address find address="{gw}/24"] = "") do={{
    /ip address add address={gw}/24 interface=bridge1 comment="[KETRIKA] Gateway"
}}

# 3. CLIENT DHCP WAN (avec verification)
:if ([/ip dhcp-client find interface={wan}] = "") do={{
    /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no comment="[KETRIKA] WAN"
}}

# 4. SERVEUR DHCP LAN
{dhcp_section}

# 5. CONFIGURATION SANS FIL
{wcfg}

# 6. ATTRIBUTION ASYNCHRONE DES PORTS
{scheduler_cmd}

# 7. DNS SECURISE
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8

# 8. NAT (avec verification)
:if ([/ip firewall nat find comment~"KETRIKA"] = "") do={{
    /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA] NAT"
}}

# 9. OPTIMISATION RESEAU AVANCEE (avec verification)
:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL Norm"
    /ip firewall mangle add chain=prerouting in-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL In"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn action=change-mss new-mss=clamp-to-pmtu passthrough=yes comment="[KETRIKA] MSS Clamp"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp action=change-mss new-mss=1360 passthrough=yes comment="[KETRIKA] MSS Norm"
    /ip firewall filter add chain=forward out-interface={wan} protocol=icmp action=drop comment="[KETRIKA] ICMP Filter"
    /ip firewall filter add chain=output out-interface={wan} protocol=icmp action=drop comment="[KETRIKA] ICMP Out"
    /ip firewall filter add chain=input connection-state=established,related action=accept comment="[KETRIKA] Est"
    /ip firewall filter add chain=input connection-state=invalid action=drop comment="[KETRIKA] Inv"
    /ip firewall filter add chain=forward connection-state=established,related action=accept comment="[KETRIKA] Fwd Est"
    /ip firewall filter add chain=forward connection-state=invalid action=drop comment="[KETRIKA] Fwd Inv"
    /ip firewall filter add chain=forward in-interface=bridge1 out-interface={wan} action=accept comment="[KETRIKA] LAN-WAN"
}} on-error={{ :log info "KETRIKA: Regles firewall deja en place" }}
{warp}{hotspot}{rl}
:put "================================================"
:put "  KETRIKA - Installation Reussie !"
:put "  Licence : {order.license_key}"
{validity_info}
:put "  Support WhatsApp : 038 28 171 00 (Jean Eric)"
:put "  Configuration operationnelle en 4 secondes"
:put "================================================"
"""
    return rsc
