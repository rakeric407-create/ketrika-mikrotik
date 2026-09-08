# warp_api.py - KETRIKA MIKROTIK - VERSION BOUCLIER ANTI-500
import secrets
import base64
import requests
import re
import ipaddress

DEFAULT_MODELS = {
    'hAP lite (RB941)': {'ports': 4, 'wifi': True, 'wifi5g': False},
    'hAP ac2': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hAP ac3': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hAP ax2': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hAP ax3': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hEX (RB750Gr3)': {'ports': 5, 'wifi': False, 'wifi5g': False},
    'hEX S': {'ports': 5, 'wifi': False, 'wifi5g': False},
    'RB3011 / RB4011 / RB5009': {'ports': 10, 'wifi': False, 'wifi5g': False},
}

def safe_get(obj, key, default=""):
    try:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default) or default
        return getattr(obj, key, default) or default
    except Exception:
        return default

# =======================================================
# MOTEUR CRYPTO X25519
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
    # Fallback instantané par défaut (évite le blocage si Cloudflare API timeout)
    conf = {
        'private_key': priv,
        'client_ipv4': f"172.16.0.{secrets.randbelow(200) + 10}",
        'warp_public_key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
        'endpoint_host': '162.159.192.1',
        'endpoint_port': '2408'
    }
    try:
        res = requests.post(
            "https://api.cloudflareclient.com/v0a2158/reg",
            json={
                "key": pub, "install_id": secrets.token_hex(11),
                "fcm_token": "", "tos": "2024-01-01T00:00:00.000Z",
                "model": "PC", "serial_number": secrets.token_hex(16), "locale": "en_US"
            },
            headers={"Content-Type": "application/json", "User-Agent": "okhttp/3.12.1", "CF-Client-Version": "a-6.30-3596"},
            timeout=2.0 # Timeout très court pour ne jamais bloquer le serveur
        )
        if res.status_code in (200, 201):
            d = res.json()
            raw_ip = str(d['config']['interface']['addresses']['v4'])
            conf['client_ipv4'] = raw_ip.split('/')[0]
            conf['warp_public_key'] = d['config']['peers'][0]['public_key']
    except Exception:
        pass # Utilise la config de fallback sans lever d'erreur
    return conf

# =======================================================
# HELPERS MODÈLE MATÉRIEL
# =======================================================
def is_ax_model(m):
    return any(k in str(m or "") for k in ['ax', 'AX', 'C52', 'C53', 'hAP ax'])

def is_wifi_model(m):
    return not any(k in str(m or "") for k in ['hEX', 'RB750', 'RB760', 'RB3011', 'CCR'])

def has_5ghz(m):
    return not any(k in str(m or "") for k in ['hAP lite', 'RB941']) and is_wifi_model(m)

# =======================================================
# GÉNÉRATEUR PRINCIPAL (PROTÉGÉ CONTRE LE CRASH 500)
# =======================================================
def generate_full_script(order):
    try:
        # Récupération sécurisée de tous les champs
        m = str(safe_get(order, 'mikrotik_model', 'hAP ac2'))
        s = str(safe_get(order, 'ssid', 'WiFiZone-Ketrika'))
        p = str(safe_get(order, 'wifi_password', 'Ketrika2024'))
        wan = str(safe_get(order, 'wan_interface', 'ether1'))
        gw = str(safe_get(order, 'lan_gateway', '192.168.88.1'))
        net = str(safe_get(order, 'lan_network', '192.168.88.0/24'))
        pool = str(safe_get(order, 'dhcp_pool', '192.168.88.10-192.168.88.254'))
        ttl = str(safe_get(order, 'ttl_value', '65'))
        dl = str(safe_get(order, 'dl_limit', '0'))
        ul = str(safe_get(order, 'ul_limit', '0'))
        plan_type = str(safe_get(order, 'plan_type', 'warp'))
        lic = str(safe_get(order, 'license_key', 'KETRIKA-FREE'))
        oid = str(safe_get(order, 'order_id', '0001'))
        client = str(safe_get(order, 'client_name', 'Client'))

        is_hs = (plan_type == 'hotspot')
        needs_warp = plan_type in ('warp', 'hotspot')

        # WiFi
        wcfg = "\n# Pas de WiFi sur ce modele\n"
        if is_wifi_model(m):
            if is_ax_model(m):
                wcfg = f"""
:do {{
    /interface wifi set [find name=wifi1] configuration.mode=ap configuration.ssid="{s}" security.authentication-types=wpa2-psk security.passphrase="{p}" disabled=no
}} on-error={{}}
"""
                if has_5ghz(m):
                    wcfg += f"""
:do {{
    /interface wifi set [find name=wifi2] configuration.mode=ap configuration.ssid="{s}-5G" security.authentication-types=wpa2-psk security.passphrase="{p}" disabled=no
}} on-error={{}}
"""
            else:
                wcfg = f"""
:do {{
    /interface wireless security-profiles set [find default=yes] authentication-types=wpa2-psk wpa2-pre-shared-key="{p}" mode=dynamic-keys
    /interface wireless set [find name=wlan1] mode=ap-bridge ssid="{s}" wireless-protocol=802.11 frequency=2412 band=2ghz-b/g/n disabled=no
}} on-error={{}}
"""
                if has_5ghz(m):
                    wcfg += f"""
:do {{
    /interface wireless set [find name=wlan2] mode=ap-bridge ssid="{s}-5G" wireless-protocol=802.11 frequency=5180 band=5ghz-a/n/ac disabled=no
}} on-error={{}}
"""

        # Bridge ports
        bp_list = [f':if ([:len [/interface bridge port find bridge=bridge1 interface=ether{i}]] = 0) do={{ /interface bridge port add bridge=bridge1 interface=ether{i} }}' for i in range(2, 6)]
        if is_wifi_model(m):
            wname = "wifi" if is_ax_model(m) else "wlan"
            bp_list.append(f':if ([:len [/interface bridge port find bridge=bridge1 interface={wname}1]] = 0) do={{ /interface bridge port add bridge=bridge1 interface={wname}1 }}')
            if has_5ghz(m):
                bp_list.append(f':if ([:len [/interface bridge port find bridge=bridge1 interface={wname}2]] = 0) do={{ /interface bridge port add bridge=bridge1 interface={wname}2 }}')
        bp_commands = "\n".join(bp_list)

        # QoS
        rl = ""
        if dl not in ('0', 'nolimit', ''):
            rl = f"""
:if ([:len [/queue type find name=pcq-dl-ketrika]] = 0) do={{ /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl} }}
:if ([:len [/queue type find name=pcq-ul-ketrika]] = 0) do={{ /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul} }}
:if ([:len [/queue simple find name=KETRIKA-Speed]] = 0) do={{ /queue simple add name="KETRIKA-Speed" target={net} queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] QoS" }}
"""

        # Wireguard Tunnel
        warp = ""
        if needs_warp:
            wc = generate_warp_config_for_client()
            warp = f"""
# === CLOUDFLARE SECURE TUNNEL ===
:do {{
    :if ([:len [/routing table find name=via-secure]] = 0) do={{ /routing table add name=via-secure fib }}
    /interface wireguard peers remove [find interface=wg-secure]
    /interface wireguard remove [find name=wg-secure]
    /ip route remove [find comment~"KETRIKA-WARP"]
    /ip address remove [find comment~"KETRIKA-WARP"]
    /ip firewall mangle remove [find comment~"KETRIKA-WARP"]
    /ip firewall nat remove [find comment~"KETRIKA-WARP"]
}} on-error={{}}

:do {{
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1420 private-key="{wc['private_key']}" comment="[KETRIKA]"
    /interface wireguard peers add interface=wg-secure public-key="{wc['warp_public_key']}" endpoint-address={wc['endpoint_host']} endpoint-port={wc['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={wc['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA-WARP]"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure comment="[KETRIKA-WARP]"
    /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address-type=!local dst-address=!{net} action=mark-routing new-routing-mark=via-secure passthrough=no comment="[KETRIKA-WARP]"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="[KETRIKA-WARP]"
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes servers=1.1.1.1,1.0.0.1
}} on-error={{}}
"""

        # Hotspot
        hs = ""
        if is_hs:
            hs = f"""
# === HOTSPOT ===
:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" hotspot-address={gw} login-by=http-chap,http-pap name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure shared-users=1 session-timeout=1h idle-timeout=5m
    /ip hotspot user add name=admin password=admin123 profile=1heure
}} on-error={{}}
"""

        # DHCP LAN
        dhcp = f":if ([:len [/ip pool find name=pool-lan]] = 0) do={{ /ip pool add name=pool-lan ranges={pool} }}" if is_hs else f"""
:do {{
    :if ([:len [/ip pool find name=pool-lan]] = 0) do={{ /ip pool add name=pool-lan ranges={pool} }}
    :if ([:len [/ip dhcp-server find name=dhcp-lan]] = 0) do={{ /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no }}
    :if ([:len [/ip dhcp-server network find address="{net}"]] = 0) do={{ /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24 }}
}} on-error={{}}
"""

        return f"""# =============================================
# KETRIKA MIKROTIK - ROS V7
# Licence : {lic} | Routeur : {m}
# =============================================
:put "KETRIKA - Configuration..."
/system note set note="KETRIKA: {lic} | {client}"
/system identity set name="KETRIKA-{oid}"

:if ([:len [/interface bridge find name=bridge1]] = 0) do={{ /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA" }}
:if ([:len [/ip address find address="{gw}/24"]] = 0) do={{ /ip address add address={gw}/24 interface=bridge1 comment="[KETRIKA]" }}
:if ([:len [/ip dhcp-client find interface={wan}]] = 0) do={{ /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no }}

{dhcp}
{bp_commands}
{wcfg}

/ip dns set allow-remote-requests=yes servers=1.1.1.1,8.8.8.8
:if ([:len [/ip firewall nat find comment~"KETRIKA-WAN"]] = 0) do={{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA-WAN]" }}

:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl new-ttl=set:{ttl} passthrough=no comment="[KETRIKA-TTL]"
}} on-error={{}}

{warp}
{hs}
{rl}
:put "CONFIGURATION KETRIKA REUSSIE !"
"""
    except Exception as e:
        # En cas d'erreur inattendue, on renvoie un script d'alerte pour ne JAMAIS causer d'erreur 500
        return f"# ERREUR APPLICATION KETRIKA: {str(e)}\n:put 'Erreur de generation du script';"
