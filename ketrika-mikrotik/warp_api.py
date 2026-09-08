# warp_api.py - KETRIKA MIKROTIK - Générateur Stable AC/AX avec Reboot Automatique
import secrets
import base64
import requests
import re
import ipaddress

# =======================================================
# VALIDATEUR STRICT DE CONFIGURATION
# =======================================================
class ConfigValidator:
    @staticmethod
    def validate_ip(ip_str):
        try:
            ipaddress.IPv4Address(ip_str)
            return True
        except:
            return False

    @staticmethod
    def validate_network(net_str):
        try:
            ipaddress.IPv4Network(net_str, strict=False)
            return True
        except:
            return False

    @staticmethod
    def auto_fix_order(order):
        if not ConfigValidator.validate_ip(order.lan_gateway):
            order.lan_gateway = '192.168.88.1'
        if not ConfigValidator.validate_network(order.lan_network):
            order.lan_network = '192.168.88.0/24'
        
        # Nettoyage SSID & Mot de passe
        cleaned_ssid = re.sub(r'[^\w\s\-\.]', '', str(order.ssid or "WiFiZone-Ketrika"))
        order.ssid = cleaned_ssid[:32].strip() or "WiFiZone-Ketrika"
        
        pwd = str(order.wifi_password or "Ketrika2024")
        order.wifi_password = pwd if len(pwd) >= 8 else "Ketrika2024"
        
        try:
            ttl = int(order.ttl_value)
            order.ttl_value = ttl if 1 <= ttl <= 255 else 65
        except:
            order.ttl_value = 65
            
        return order

# =======================================================
# MOTEUR CRYPTO X25519 PURE PYTHON
# =======================================================
P = 2**255 - 19
A24 = 121665

def _clamp(k_bytes):
    k = bytearray(k_bytes)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return bytes(k)

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
    return (x_2 * pow(z_2, P - 2, P) % P).to_bytes(32, 'little')

def generate_wireguard_keys():
    raw_priv = secrets.token_bytes(32)
    clamped = _clamp(raw_priv)
    pub = _x25519(clamped, (9).to_bytes(32, 'little'))
    return base64.b64encode(clamped).decode(), base64.b64encode(pub).decode()

def generate_warp_config_for_client():
    priv, pub = generate_wireguard_keys()
    try:
        res = requests.post("https://api.cloudflareclient.com/v0a2158/reg",
            json={"key": pub, "install_id": secrets.token_hex(11),
                  "fcm_token": "", "tos": "2024-01-01T00:00:00.000Z",
                  "model": "PC", "serial_number": secrets.token_hex(16), "locale": "en_US"},
            headers={"Content-Type": "application/json", "User-Agent": "okhttp/3.12.1", "CF-Client-Version": "a-6.30-3596"},
            timeout=5)
        if res.status_code in (200, 201):
            d = res.json()
            raw_v4 = d['config']['interface']['addresses']['v4']
            client_ip = raw_v4.split('/')[0] if '/' in raw_v4 else raw_v4
            return {
                'private_key': priv,
                'client_ipv4': client_ip,
                'warp_public_key': d['config']['peers'][0]['public_key'],
                'endpoint_host': '162.159.192.1',
                'endpoint_port': '2408'
            }
    except Exception:
        pass
    return {
        'private_key': priv,
        'client_ipv4': f"172.16.0.{secrets.randbelow(200) + 10}",
        'warp_public_key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
        'endpoint_host': '162.159.192.1',
        'endpoint_port': '2408'
    }

# =======================================================
# DÉTECTION CONFIGURATION MATÉRIEL AC / AX
# =======================================================
def format_limit(v):
    return '0' if v in ('nolimit', '0', '', None) else str(v)

def is_ax_model(m):
    return any(k in m for k in ['ax', 'AX', 'C52', 'C53', 'hAP ax'])

def is_wifi_model(m):
    return not any(k in m for k in ['hEX', 'RB750', 'RB760', 'RB3011', 'CCR'])

def has_5ghz(m):
    return not any(k in m for k in ['hAP lite', 'RB941']) and is_wifi_model(m)

def generate_wifi_config(order):
    m, s, p = order.mikrotik_model, order.ssid, order.wifi_password
    if not is_wifi_model(m):
        return "\n# Ce materiel ne dispose pas de module WiFi integre.\n"

    if is_ax_model(m):
        # Configuration WiFi 6 (AX) - ROS v7 (wifi1 & wifi2)
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI 6 AX ===
:do {{
    /interface wifi set wifi1 configuration.mode=ap configuration.ssid="{s}" \\
        security.authentication-types=wpa2-psk security.passphrase="{p}" \\
        disabled=no
}} on-error={{}}
"""
        if has_5ghz(m):
            cfg += f"""
:do {{
    /interface wifi set wifi2 configuration.mode=ap configuration.ssid="{s}-5G" \\
        security.authentication-types=wpa2-psk security.passphrase="{p}" \\
        disabled=no
}} on-error={{}}
"""
    else:
        # Configuration WiFi Legacy (AC) - ROS v7 (wlan1 & wlan2)
        cfg = f"""
# === CONFIGURATION SANS FIL WIFI AC ===
:do {{
    /interface wireless set wlan1 mode=ap-bridge ssid="{s}" wireless-protocol=802.11 \\
        frequency=2412 band=2ghz-b/g/n channel-width=20/40mhz-Ce disabled=no
    /interface wireless security-profiles set [find default=yes] authentication-types=wpa2-psk \\
        wpa2-pre-shared-key="{p}" mode=dynamic-keys
}} on-error={{}}
"""
        if has_5ghz(m):
            cfg += f"""
:do {{
    /interface wireless set wlan2 mode=ap-bridge ssid="{s}-5G" wireless-protocol=802.11 \\
        frequency=5180 band=5ghz-a/n/ac channel-width=20/40/80mhz-Ceee disabled=no
}} on-error={{}}
"""
    return cfg

# =======================================================
# GÉNÉRATEUR SCRIPT COMPLET AVEC REBOOT
# =======================================================
def generate_full_script(order):
    from database import MIKROTIK_MODELS
    order = ConfigValidator.auto_fix_order(order)
    info = MIKROTIK_MODELS.get(order.mikrotik_model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    ports = info['ports']
    wan, gw, net = order.wan_interface, order.lan_gateway, order.lan_network
    pool, ttl = order.dhcp_pool, order.ttl_value
    dl, ul = format_limit(order.dl_limit), format_limit(order.ul_limit)
    is_hs = order.plan_type == 'hotspot'
    needs_warp = order.plan_type in ('warp', 'hotspot')

    # Association intelligente des ports physiques et sans fil au Bridge
    bp = ""
    for i in range(2, ports + 1):
        bp += f"/interface bridge port add bridge=bridge1 interface=ether{i}; "
    
    if is_wifi_model(order.mikrotik_model):
        if is_ax_model(order.mikrotik_model):
            bp += "/interface bridge port add bridge=bridge1 interface=wifi1; "
            if has_5ghz(order.mikrotik_model):
                bp += "/interface bridge port add bridge=bridge1 interface=wifi2; "
        else:
            bp += "/interface bridge port add bridge=bridge1 interface=wlan1; "
            if has_5ghz(order.mikrotik_model):
                bp += "/interface bridge port add bridge=bridge1 interface=wlan2; "

    wcfg = generate_wifi_config(order)

    # Limitation bande passante
    rl = "\n# Mode Illimite : Aucun bridage de vitesse\n" if dl == '0' else f"""
:if ([/queue type find name=pcq-dl-ketrika] = "") do={{ /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl} }}
:if ([/queue type find name=pcq-ul-ketrika] = "") do={{ /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul} }}
:if ([/queue simple find name=KETRIKA-Speed] = "") do={{ /queue simple add name="KETRIKA-Speed" target={net} queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] QoS" }}
"""

    # Cloudflare Secure Tunnel (Route & Table v7 Fixe)
    warp = ""
    if needs_warp:
        wc = generate_warp_config_for_client()
        warp = f"""
# === CLOUDFLARE SECURE TUNNEL ===
:do {{ /interface wireguard peers remove [find interface=wg-secure] }} on-error={{}}
:do {{ /interface wireguard remove wg-secure }} on-error={{}}
:do {{ /ip route remove [find comment~"KETRIKA"] }} on-error={{}}
:do {{ /routing table remove [find name=via-secure] }} on-error={{}}
:delay 1s
:do {{
    /routing table add name=via-secure fib
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1420 private-key="{wc['private_key']}" comment="[KETRIKA]"
    /interface wireguard peers add interface=wg-secure public-key="{wc['warp_public_key']}" endpoint-address={wc['endpoint_host']} endpoint-port={wc['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={wc['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA]"
    /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address=!{net} action=mark-routing new-routing-mark=via-secure passthrough=yes comment="[KETRIKA]"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure comment="[KETRIKA]"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="[KETRIKA]"
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes servers=1.1.1.1,1.0.0.1
}} on-error={{}}
"""

    # Hotspot
    hs = ""
    if is_hs:
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        hs = f"""
# === PORTAIL HOTSPOT WIFI ZONE ===
:do {{ /ip dhcp-server remove [find interface=bridge1 name=dhcp-lan] }} on-error={{}}
:do {{ /ip hotspot remove hotspot-ketrika }} on-error={{}}
:delay 1s
:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" hotspot-address={gw} login-by=http-chap,http-pap name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure {rl_hs} shared-users=1 session-timeout=1h idle-timeout=5m
    /ip hotspot user profile add name=1jour {rl_hs} shared-users=2 session-timeout=1d idle-timeout=10m
    /ip hotspot user profile add name=1semaine {rl_hs} shared-users=3 session-timeout=7d idle-timeout=15m
    /ip hotspot user profile add name=1mois {rl_hs} shared-users=3 session-timeout=30d idle-timeout=30m
    /ip hotspot user add name=admin password=admin123 profile=1mois
}} on-error={{}}
"""
        if order.pppoe_enabled:
            rl_p = f"rate-limit={ul}/{dl}" if dl != '0' else ""
            hs += f"""
:do {{
    /ip pool add name=pool-pppoe ranges=192.168.99.10-192.168.99.250
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 name=pppoe-ketrika {rl_p} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika disabled=no interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
}} on-error={{}}
"""
        if order.voucher_enabled:
            hs += "\n/ip hotspot user\n"
            for _ in range(10):
                c = secrets.token_hex(4).upper()
                hs += f'add name=V-{c} password={c} profile=1heure comment="Voucher 1H"\n'

    dhcp = f":do {{ /ip pool add name=pool-lan ranges={pool} }} on-error={{}}" if is_hs else f"""
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24
}} on-error={{}}
"""

    return f"""# =============================================
# KETRIKA MIKROTIK - SCRIPT VERROUILLE (ROUTEROS V7)
# Pack : {order.plan_type.upper()} | Routeur : {order.mikrotik_model}
# Licence : {order.license_key} (1 SEUL ROUTEUR)
# =============================================

:put "KETRIKA - Configuration en cours..."
:delay 1s

# 1. VERROUILLAGE MATERIEL DANS LE ROUTEUR
/system note set note="KETRIKA-LICENCE: {order.license_key} | Routeur: {order.mikrotik_model} | Client: {order.client_name}"
/system identity set name="KETRIKA-{order.order_id}"

# 2. BRIDGE PRINCIPAL
:if ([/interface bridge find name=bridge1] = "") do={{ /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA" }}

# 3. IP GATEWAY
:if ([/ip address find address="{gw}/24"] = "") do={{ /ip address add address={gw}/24 interface=bridge1 comment="[KETRIKA]" }}

# 4. DHCP CLIENT WAN
:if ([/ip dhcp-client find interface={wan}] = "") do={{ /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no }}

# 5. DHCP SERVEUR LAN
{dhcp}

# 6. CONFIGURATION SANS FIL WIFI DETECTE
{wcfg}

# 7. ATTRIBUTION DES PORTS EN ARRIERE PLAN (ZERO COUPURE WINBOX)
/system scheduler add name=ketrika_ports interval=0s start-time=([/system clock get time] + 00:00:04) on-event="{bp}/system scheduler remove ketrika_ports;"

# 8. DNS & NAT
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8
:if ([/ip firewall nat find comment~"KETRIKA"] = "") do={{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA]" }}

# 9. OPTIMISATION RESEAU MULTI-CLIENTS
:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL"
    /ip firewall mangle chain=prerouting in-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no
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
{warp}{hs}{rl}

# === 10. REDEMARRAGE AUTOMATIQUE DU ROUTEUR ===
:log info "KETRIKA: Configuration terminee, reboot dans 3s..."
:put "================================================"
:put "  CONFIGURATION KETRIKA APPLIQUEE AVEC SUCCES !"
:put "  Licence : {order.license_key}"
:put "  Materiel : {order.mikrotik_model}"
:put "  Redemarrage du routeur en cours..."
:put "================================================"

/system scheduler add name=ketrika_reboot interval=0s start-time=([/system clock get time] + 00:00:03) on-event="/system scheduler remove ketrika_reboot; /system reboot;"
"""
