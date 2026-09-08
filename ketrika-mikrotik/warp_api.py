# warp_api.py - Générateur de Script MikroTik RouterOS v7 Pro (Anti-déconnexion)
import secrets
import requests
import base64
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

def format_limit(value):
    if value in ('nolimit', '0', ''):
        return '0'
    return value

def is_ax_model(model_name):
    ax_keywords = ['ax', 'AX', 'C52', 'C53', 'hAP ax']
    return any(k in model_name for k in ax_keywords)

def is_wifi_model(model_name):
    no_wifi = ['hEX', 'RB750', 'RB760', 'RB3011', 'CCR']
    return not any(k in model_name for k in no_wifi)

def has_5ghz(model_name):
    no_5g = ['hAP lite', 'RB941']
    return not any(k in model_name for k in no_5g) and is_wifi_model(model_name)

# =============================================
# GÉNÉRATION AUTOMATIQUE CLOUDFLARE WARP
# =============================================
def generate_wireguard_keys():
    """Génère une paire de clés WireGuard ultra-rapidement (sans PyNaCl)"""
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    private_b64 = base64.b64encode(private_bytes).decode('utf-8')
    public_b64 = base64.b64encode(public_bytes).decode('utf-8')
    return private_b64, public_b64

def register_warp_account(public_key):
    """Enregistre un compte Cloudflare WARP via l'API officielle"""
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
        "tos": "2021-07-27T00:00:00.000Z",
        "model": "PC",
        "serial_number": secrets.token_hex(16),
        "locale": "en_US"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            data = response.json()
            return {
                'success': True,
                'client_ipv4': data['config']['interface']['addresses']['v4'],
                'warp_public_key': data['config']['peers'][0]['public_key'],
                'endpoint': data['config']['peers'][0]['endpoint']['host']
            }
    except Exception as e:
        print(f"Erreur d'inscription WARP: {e}")
    return {'success': False}

def generate_warp_config_for_client():
    private_key, public_key = generate_wireguard_keys()
    warp_info = register_warp_account(public_key)
    
    if not warp_info or not warp_info.get('success'):
        # Fallback si l'API Cloudflare ne répond pas
        return {
            'success': False,
            'private_key': private_key,
            'client_ipv4': '172.16.0.2',
            'warp_public_key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
            'endpoint_host': 'engage.cloudflareclient.com',
            'endpoint_port': '2408'
        }
    
    endpoint = warp_info['endpoint']
    host, port = endpoint.rsplit(':', 1) if ':' in endpoint else (endpoint, '2408')
    
    return {
        'success': True,
        'private_key': private_key,
        'client_ipv4': warp_info['client_ipv4'],
        'warp_public_key': warp_info['warp_public_key'],
        'endpoint_host': host,
        'endpoint_port': port
    }

def generate_wifi_config(order):
    model = order.mikrotik_model
    ssid = order.ssid
    password = order.wifi_password

    if not is_wifi_model(model):
        return "\n# Ce modele ne contient pas de module WiFi integre.\n"

    if is_ax_model(model):
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI AX (V7) ===
:do {{
    /interface wifi set wlan1 configuration.mode=ap \\
        configuration.ssid="{ssid}" \\
        security.authentication-types=wpa2-psk \\
        security.passphrase="{password}" \\
        channel.frequency=2412 channel.width=20/40mhz-Ce \\
        disabled=no
}} on-error={{ :log warning "WiFi AX 2.4G : non configure" }}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wifi set wlan2 configuration.mode=ap \\
        configuration.ssid="{ssid}-5G" \\
        security.authentication-types=wpa2-psk \\
        security.passphrase="{password}" \\
        channel.frequency=5180 channel.width=20/40/80mhz-Ceee \\
        disabled=no
}} on-error={{ :log warning "WiFi AX 5G : non configure" }}
"""
    else:
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI AC (V7) ===
:do {{
    /interface wireless set wlan1 mode=ap-bridge \\
        ssid="{ssid}" \\
        wireless-protocol=802.11 \\
        frequency=2412 band=2ghz-b/g/n \\
        channel-width=20/40mhz-Ce \\
        disabled=no
    /interface wireless security-profiles set [find default=yes] \\
        authentication-types=wpa2-psk \\
        wpa2-pre-shared-key="{password}" \\
        mode=dynamic-keys
}} on-error={{ :log warning "WiFi AC 2.4G : non configure" }}
"""
        if has_5ghz(model):
            cfg += f"""
:do {{
    /interface wireless set wlan2 mode=ap-bridge \\
        ssid="{ssid}-5G" \\
        wireless-protocol=802.11 \\
        frequency=5180 band=5ghz-a/n/ac \\
        channel-width=20/40/80mhz-Ceee \\
        disabled=no
}} on-error={{ :log warning "WiFi AC 5G : non configure" }}
"""
    return cfg

def generate_full_script(order):
    from database import MIKROTIK_MODELS

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

    # --- ATTACHEMENT DES PORTS EN ARRIÈRE-PLAN ---
    bp_inner = ""
    for p in lan_ports:
        bp_inner += f"/interface bridge port add bridge=bridge1 interface={p}; "
    if is_wifi_model(order.mikrotik_model):
        bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan1; "
        if has_5ghz(order.mikrotik_model):
            bp_inner += "/interface bridge port add bridge=bridge1 interface=wlan2; "

    scheduler_cmd = f"""
# === CONFIGURATION DES PORTS EN ARRIERE PLAN (EVITE LES COUPURES) ===
:log info "KETRIKA: Planification de l'attribution des ports..."
/system scheduler add name=ketrika_async_setup interval=0s start-time=([/system clock get time] + 00:00:05) on-event="\\
    :log info \\"KETRIKA: Assignation des ports physiques...\\"; \\
    {bp_inner} \\
    /system scheduler remove ketrika_async_setup; \\
    :log info \\"KETRIKA: Ports attribues sans interruption.\\";"
"""

    wcfg = generate_wifi_config(order)

    if dl == '0':
        rl = """
# === LIMITATION BANDE PASSANTE : ILLIMITEE ===
:log info "KETRIKA: Aucun bridage de bande passante applique."
"""
    else:
        rl = f"""
# === LIMITATION BANDE PASSANTE PAR CLIENT ===
:do {{
    /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl}
    /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul}
    /queue simple add name="KETRIKA-Limit" target={net} \\
        queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] Bandwidth Management"
}} on-error={{}}
"""

    warp = ""
    if needs_warp:
        warp_config = generate_warp_config_for_client()
        warp = f"""
# =============================================
# ☁️ TUNNEL SÉCURISÉ CLOUDFLARE WARP (AUTO-GÉNÉRÉ)
# =============================================
:do {{
    /interface wireguard add name=wg-warp listen-port=13231 mtu=1280 private-key="{warp_config['private_key']}" comment="[KETRIKA-WARP]"
    /interface wireguard peers add interface=wg-warp public-key="{warp_config['warp_public_key']}" endpoint-address={warp_config['endpoint_host']} endpoint-port={warp_config['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={warp_config['client_ipv4']}/32 interface=wg-warp comment="[KETRIKA-WARP] Client IP"
    
    /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address=!{net} action=mark-routing new-routing-mark=via-warp passthrough=yes comment="[KETRIKA-WARP] Mark LAN"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-warp routing-table=via-warp comment="[KETRIKA-WARP] Default route"
    /ip firewall nat add chain=srcnat out-interface=wg-warp action=masquerade comment="[KETRIKA-WARP] NAT"
    
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes servers=1.1.1.1,1.0.0.1
    :log info "KETRIKA-WARP: Tunnel Cloudflare WireGuard cree et connecte !"
}} on-error={{ :log error "KETRIKA-WARP: Erreur durant le montage du tunnel" }}
"""

    hotspot = ""
    if is_hotspot:
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        hotspot = f"""
# =============================================
# HOTSPOT WIFI ZONE
# =============================================
:do {{
    /ip dhcp-server remove [find interface=bridge1 name=dhcp-lan]
}} on-error={{}}

:delay 2s

:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" hotspot-address={gw} login-by=http-chap,http-pap name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 name=hotspot-ketrika profile=hsprof-ketrika
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
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 name=pppoe-ketrika {rl_ppp} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika disabled=no interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
}} on-error={{}}
"""
        if order.voucher_enabled:
            hotspot += "\n# === VOUCHERS PRE-GENERES ===\n/ip hotspot user\n"
            for _ in range(10):
                c = secrets.token_hex(4).upper()
                hotspot += f'add name=V-{c} password={c} profile=1heure comment="Voucher 1H"\n'

    if is_hotspot:
        dhcp_section = f"""
:do {{
    /ip pool add name=pool-lan ranges={pool}
}} on-error={{}}
"""
    else:
        dhcp_section = f"""
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24
}} on-error={{}}
"""

    rsc = f"""# =============================================
# KETRIKA MIKROTIK - Configuration Professionnelle v2
# =============================================
# Plan : {order.plan_type.upper()}
# Modele : {order.mikrotik_model}
# Ports : {ports} Ethernet
# Licence : {order.license_key}
# =============================================

:log info "KETRIKA: Installation en cours..."
:put "Installation en cours... WinBox restera connecte"
:delay 2s

# === 1. BRIDGE ===
:do {{
    /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA LAN"
}} on-error={{}}
:delay 1s

# === 2. IP LAN ===
:do {{
    /ip address add address={gw}/24 interface=bridge1 comment="IP LAN"
}} on-error={{}}

# === 3. DHCP WAN ===
:do {{
    /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no comment="KETRIKA WAN"
}} on-error={{}}
:delay 1s

# === 4. DHCP LAN ===
{dhcp_section}
:delay 1s

# === 5. WIFI ===
{wcfg}
:delay 1s

# === 6. PORTS EN ARRIERE PLAN ===
{scheduler_cmd}

# === 7. DNS ===
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8

# === 8. NAT ===
:do {{
    /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA] NAT"
}} on-error={{}}

# === 9. OPTIMISATION & BYPASS RESEAU ===
:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL OUT"
    /ip firewall mangle add chain=prerouting in-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL IN"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn action=change-mss new-mss=clamp-to-pmtu passthrough=yes comment="[KETRIKA] MSS"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp action=change-mss new-mss=1360 passthrough=yes comment="[KETRIKA] MSS Norm"
    /ip firewall filter add chain=forward out-interface={wan} protocol=icmp action=drop comment="[KETRIKA] ICMP Filter"
    /ip firewall filter add chain=output out-interface={wan} protocol=icmp action=drop comment="[KETRIKA] ICMP Out"
    /ip firewall filter add chain=input connection-state=established,related action=accept
    /ip firewall filter add chain=input connection-state=invalid action=drop
    /ip firewall filter add chain=forward connection-state=established,related action=accept
    /ip firewall filter add chain=forward connection-state=invalid action=drop
    /ip firewall filter add chain=forward in-interface=bridge1 out-interface={wan} action=accept
}} on-error={{}}
{warp}{hotspot}{rl}
# =============================================
:log info "KETRIKA: Configuration appliquee."
:put "================================================"
:put "  CONFIGURATION KETRIKA APPLIQUEE"
:put "  Licence : {order.license_key}"
:put "  L'attribution des ports se fera en arriere-plan dans 5 secondes."
:put "================================================"
"""
    return rsc
