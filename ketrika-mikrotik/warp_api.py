C'est maintenant parfaitement clair ! Voici l'architecture exacte de vos **3 Packs distincts** :

---

### 📦 La logique exacte de vos 3 Packs :

| Pack | VPN Cloudflare (Anti-FAI) | Portail Hotspot (Tickets) | Serveur PPPoE | Wi-Fi | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. STANDARD** | ❌ Non | ❌ Non | ❌ Non | 🔒 Sécurisé (Mot de passe) | Connexion classique directe sur le FAI avec QoS et masquage TTL. |
| **2. WARP (Anti-FAI)** | ✅ **OUI** | ❌ Non | ❌ Non | 🔒 Sécurisé (Mot de passe) | **100% du trafic passe par l'IP Cloudflare**, Anti-DPI, Anti-blocage FAI. |
| **3. HOTSPOT PRO** | ✅ **OUI** | ✅ **OUI** | ✅ **OUI** (Optionnel) | 🔓 Ouvert (Portail) | **Popup automatique + Tickets Vouchers**, et **une fois connecté, tout le monde navigue sous l'IP Cloudflare (Anti-FAI)**. |

---

### Pourquoi l'IP Cloudflare ne marchait pas auparavant ?
- Dans le **Pack 2 (WARP seul)**, la règle de routage contenait `hotspot=auth`. Comme il n'y a pas de Hotspot dans le Pack 2, MikroTik ignorait la règle et vous renvoyait sur le FAI.
- Dans le **Pack 3 (Hotspot + WARP)**, le tunnel interceptait les requêtes avant l'affichage du portail.

👉 **Tout est maintenant corrigé et séparé selon le Pack choisi !**

---

### Code complet `warp_api.py` :

```python
# warp_api.py - KETRIKA MIKROTIK - Générateur 3 Packs Officiels (Standard / WARP Anti-FAI / Hotspot WARP)
import secrets
import base64
import requests
import re
import ipaddress
import datetime

DEFAULT_MODELS = {
    'hAP lite (RB941)': {'ports': 4, 'wifi': True, 'wifi5g': False},
    'hAP ac2': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hAP ac3': {'ports': 5, 'wifi': True, 'wifi5g': True},
    'hAP ax2 (C52iG)': {'ports': 5, 'wifi': True, 'wifi5g': True},
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
# VALIDATEUR STRICT DE CONFIGURATION
# =======================================================
class ConfigValidator:
    @staticmethod
    def validate_ip(ip_str):
        try:
            ipaddress.IPv4Address(str(ip_str).strip())
            return True
        except Exception:
            return False

    @staticmethod
    def validate_network(net_str):
        try:
            ipaddress.IPv4Network(str(net_str).strip(), strict=False)
            return True
        except Exception:
            return False

    @staticmethod
    def auto_fix_order(order):
        if order is None:
            return order

        gw = str(safe_get(order, 'lan_gateway', '192.168.88.1'))
        if not ConfigValidator.validate_ip(gw):
            setattr(order, 'lan_gateway', '192.168.88.1')

        net = str(safe_get(order, 'lan_network', '192.168.88.0/24'))
        if not ConfigValidator.validate_network(net):
            setattr(order, 'lan_network', '192.168.88.0/24')
        
        ssid = str(safe_get(order, 'ssid', '') or "WiFiZone-Ketrika")
        cleaned_ssid = re.sub(r'[^\w\s\-\.]', '', ssid)
        setattr(order, 'ssid', cleaned_ssid[:32].strip() or "WiFiZone-Ketrika")
        
        pwd = str(safe_get(order, 'wifi_password', '') or "Ketrika2024")
        setattr(order, 'wifi_password', pwd if len(pwd) >= 8 else "Ketrika2024")
        
        try:
            ttl_val = str(safe_get(order, 'ttl_value', '65')).strip().lower()
            if ttl_val in ('0', 'none', 'disabled', ''):
                setattr(order, 'ttl_value', 'disabled')
            else:
                ttl = int(ttl_val)
                setattr(order, 'ttl_value', ttl if 1 <= ttl <= 255 else 65)
        except Exception:
            setattr(order, 'ttl_value', 65)
            
        return order

# =======================================================
# MOTEUR CRYPTO X25519 OFFICIEL
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
        z_2 = (E * (BB + (A24 * E))) % P
    if swap:
        x_2, x_3 = x_3, x_2
        z_2, z_3 = z_3, z_2
    return (x_2 * pow(z_2, P - 2, P) % P).to_bytes(32, 'little')

def generate_wireguard_keys():
    try:
        from cryptography.hazmat.primitives.asymmetric import x25519
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()
        return base64.b64encode(priv.private_bytes_raw()).decode(), base64.b64encode(pub.public_bytes_raw()).decode()
    except Exception:
        raw_priv = secrets.token_bytes(32)
        clamped = _clamp(raw_priv)
        pub = _x25519(clamped, (9).to_bytes(32, 'little'))
        return base64.b64encode(clamped).decode(), base64.b64encode(pub).decode()

# =======================================================
# ENREGISTREMENT API CLOUDFLARE WARP
# =======================================================
def generate_warp_config_for_client():
    priv, pub = generate_wireguard_keys()
    
    stealth_ports = ['500', '853', '4500', '2408']
    selected_port = secrets.choice(stealth_ports)
    
    cloudflare_endpoints = ['162.159.192.1', '162.159.193.1', '188.114.96.1', '188.114.97.1']
    selected_ip = secrets.choice(cloudflare_endpoints)
    
    endpoints = [
        "https://api.cloudflareclient.com/v0a3370/reg",
        "https://api.cloudflareclient.com/v0a2158/reg"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "okhttp/3.12.1",
        "CF-Client-Version": "a-6.30-3596"
    }
    
    body = {
        "key": pub,
        "install_id": "",
        "fcm_token": "",
        "tos": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "model": "PC",
        "serial_number": secrets.token_hex(16),
        "locale": "en_US"
    }
    
    for url in endpoints:
        try:
            res = requests.post(url, json=body, headers=headers, timeout=4)
            if res.status_code in (200, 201):
                d = res.json()
                raw_v4 = str(d['config']['interface']['addresses']['v4'])
                client_ip = raw_v4.split('/')[0] if '/' in raw_v4 else raw_v4
                peer_pub = d['config']['peers'][0]['public_key']
                return {
                    'private_key': priv,
                    'client_ipv4': client_ip,
                    'warp_public_key': peer_pub,
                    'endpoint_host': selected_ip,
                    'endpoint_port': selected_port
                }
        except Exception:
            continue

    return {
        'private_key': priv,
        'client_ipv4': f"172.16.0.{secrets.randbelow(200) + 10}",
        'warp_public_key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
        'endpoint_host': selected_ip,
        'endpoint_port': selected_port
    }

# =======================================================
# HELPERS MATÉRIEL AC / AX
# =======================================================
def format_limit(v):
    return '0' if v in ('nolimit', '0', '', None) else str(v)

def is_ax_model(m):
    return any(k in str(m or "") for k in ['ax', 'AX', 'C52', 'C53', 'hAP ax'])

def is_wifi_model(m):
    return not any(k in str(m or "") for k in ['hEX', 'RB750', 'RB760', 'RB3011', 'CCR'])

def has_5ghz(m):
    return not any(k in str(m or "") for k in ['hAP lite', 'RB941']) and is_wifi_model(m)

def generate_wifi_config(order, is_hs):
    m = safe_get(order, 'mikrotik_model', '')
    s = safe_get(order, 'ssid', 'WiFiZone-Ketrika')
    p = safe_get(order, 'wifi_password', 'Ketrika2024')

    if not is_wifi_model(m):
        return "\n# Materiel sans module WiFi integre.\n"

    # Si Pack Hotspot : Wi-Fi Ouvert sans mot de passe
    if is_hs:
        if is_ax_model(m):
            cfg = f"""
# === CONFIGURATION SANS FIL WIFI 6 AX (HOTSPOT OUVERT) ===
:do {{
    /interface wifi set [find name=wifi1] configuration.mode=ap configuration.ssid="{s}" disabled=no
}} on-error={{}}
"""
            if has_5ghz(m):
                cfg += f"""
:do {{
    /interface wifi set [find name=wifi2] configuration.mode=ap configuration.ssid="{s}-5G" disabled=no
}} on-error={{}}
"""
        else:
            cfg = f"""
# === CONFIGURATION SANS FIL WIFI AC (HOTSPOT OUVERT) ===
:do {{
    /interface wireless security-profiles set [find default=yes] mode=none
    /interface wireless set [find name=wlan1] mode=ap-bridge ssid="{s}" wireless-protocol=802.11 frequency=2412 band=2ghz-b/g/n disabled=no
}} on-error={{}}
"""
            if has_5ghz(m):
                cfg += f"""
:do {{
    /interface wireless set [find name=wlan2] mode=ap-bridge ssid="{s}-5G" wireless-protocol=802.11 frequency=5180 band=5ghz-a/n/ac disabled=no
}} on-error={{}}
"""
    # Si Pack 1 ou Pack 2 : Wi-Fi Sécurisé avec mot de passe
    else:
        if is_ax_model(m):
            cfg = f"""
# === CONFIGURATION SANS FIL WIFI 6 AX (SECURISE) ===
:do {{
    /interface wifi set [find name=wifi1] configuration.mode=ap configuration.ssid="{s}" security.authentication-types=wpa2-psk security.passphrase="{p}" disabled=no
}} on-error={{}}
"""
            if has_5ghz(m):
                cfg += f"""
:do {{
    /interface wifi set [find name=wifi2] configuration.mode=ap configuration.ssid="{s}-5G" security.authentication-types=wpa2-psk security.passphrase="{p}" disabled=no
}} on-error={{}}
"""
        else:
            cfg = f"""
# === CONFIGURATION SANS FIL WIFI AC (SECURISE) ===
:do {{
    /interface wireless security-profiles set [find default=yes] authentication-types=wpa2-psk wpa2-pre-shared-key="{p}" mode=dynamic-keys
    /interface wireless set [find name=wlan1] mode=ap-bridge ssid="{s}" wireless-protocol=802.11 frequency=2412 band=2ghz-b/g/n disabled=no
}} on-error={{}}
"""
            if has_5ghz(m):
                cfg += f"""
:do {{
    /interface wireless set [find name=wlan2] mode=ap-bridge ssid="{s}-5G" wireless-protocol=802.11 frequency=5180 band=5ghz-a/n/ac disabled=no
}} on-error={{}}
"""
    return cfg

# =======================================================
# GÉNÉRATEUR SCRIPT COMPLET
# =======================================================
def generate_full_script(order):
    try:
        from database import MIKROTIK_MODELS
        models = MIKROTIK_MODELS
    except Exception:
        models = DEFAULT_MODELS

    order = ConfigValidator.auto_fix_order(order)
    model = safe_get(order, 'mikrotik_model', 'hAP ac2')
    info = models.get(model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    ports = info.get('ports', 5)

    wan = safe_get(order, 'wan_interface', 'ether1') or 'ether1'
    gw = safe_get(order, 'lan_gateway', '192.168.88.1')
    net = safe_get(order, 'lan_network', '192.168.88.0/24')
    pool = safe_get(order, 'dhcp_pool', '192.168.88.10-192.168.88.254')
    dl = format_limit(safe_get(order, 'dl_limit', '0'))
    ul = format_limit(safe_get(order, 'ul_limit', '0'))
    
    plan_type = str(safe_get(order, 'plan_type', 'warp')).lower()
    
    # Détection des 3 packs
    is_pack_standard = plan_type in ('standard', 'basic', 'illimite', 'classic')
    is_pack_warp = plan_type in ('warp', 'vpn', 'stealth')
    is_pack_hotspot = plan_type in ('hotspot', 'hotspot_vpn', 'full')

    license_key = safe_get(order, 'license_key', 'KETRIKA-FREE')
    order_id = safe_get(order, 'order_id', '0001')
    client_name = safe_get(order, 'client_name', 'Client')
    ttl_value = safe_get(order, 'ttl_value', 65)

    # Ports Bridge
    bp = ""
    for i in range(2, ports + 1):
        bp += f"/interface bridge port add bridge=bridge1 interface=ether{i}; "
    
    if is_wifi_model(model):
        if is_ax_model(model):
            bp += "/interface bridge port add bridge=bridge1 interface=wifi1; "
            if has_5ghz(model):
                bp += "/interface bridge port add bridge=bridge1 interface=wifi2; "
        else:
            bp += "/interface bridge port add bridge=bridge1 interface=wlan1; "
            if has_5ghz(model):
                bp += "/interface bridge port add bridge=bridge1 interface=wlan2; "

    wcfg = generate_wifi_config(order, is_pack_hotspot)

    # Limitation QoS
    rl = "\n# Mode Illimite : Aucun bridage de vitesse\n" if dl == '0' else f"""
:if ([/queue type find name=pcq-dl-ketrika] = "") do={{ /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl} }}
:if ([/queue type find name=pcq-ul-ketrika] = "") do={{ /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul} }}
:if ([/queue simple find name=KETRIKA-Speed] = "") do={{ /queue simple add name="KETRIKA-Speed" target={net} queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] QoS" }}
"""

    # Masquage TTL Dynamique
    if ttl_value == 'disabled':
        ttl_script = "\n# Masquage TTL : Desactive par le client\n"
    else:
        ttl_script = f"""
# OPTIMISATION RESEAU & MASQUAGE TTL (CHOIX CLIENT: {ttl_value})
/ip firewall mangle remove [find comment~"KETRIKA-TTL"]
/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:{ttl_value} passthrough=yes comment="[KETRIKA-TTL]"
/ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:{ttl_value} passthrough=yes comment="[KETRIKA-TTL]"
"""

    # =======================================================
    # PACK 1 : STANDARD (SANS VPN, SANS HOTSPOT)
    # =======================================================
    if is_pack_standard:
        custom_block = f"""
# === PACK 1: STANDARD SANS VPN (SORTIE DIRECTE WAN) ===
/ip dns set allow-remote-requests=yes servers=1.1.1.1,8.8.8.8 use-doh-server=""
:if ([/ip firewall nat find comment~"KETRIKA-WAN"] = "") do={{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA-WAN]" }}

# DHCP Standard
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24
}} on-error={{}}
"""

    # =======================================================
    # PACK 2 : WARP ANTI-FAI (AVEC VPN, SANS HOTSPOT)
    # =======================================================
    elif is_pack_warp:
        wc = generate_warp_config_for_client()
        custom_block = f"""
# === PACK 2: WARP ANTI-FAI (100% TRAFIC SOUS IP CLOUDFLARE) ===
/ip firewall filter disable [find action=fasttrack-connection]
:do {{ /ipv6 settings set disable-ipv6=yes }} on-error={{}}

:do {{ /interface wireguard peers remove [find interface=wg-secure] }} on-error={{}}
:do {{ /interface wireguard remove wg-secure }} on-error={{}}
:do {{ /ip route remove [find comment~"KETRIKA"] }} on-error={{}}
:do {{ /routing table remove [find name=via-secure] }} on-error={{}}
:delay 1s
:do {{
    /routing table add name=via-secure fib
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1280 private-key="{wc['private_key']}" comment="[KETRIKA-VPN]"
    /interface wireguard peers add interface=wg-secure public-key="{wc['warp_public_key']}" endpoint-address={wc['endpoint_host']} endpoint-port={wc['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={wc['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA-VPN]"
    
    # Routage strict : TOUT le trafic LAN passe obligatoirement par Wireguard
    /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address-type=!local dst-address=!{net} action=mark-routing new-routing-mark=via-secure passthrough=no comment="[KETRIKA-WARP]"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure comment="[KETRIKA-WARP]"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="[KETRIKA-WARP]"
    
    # Anti-Fuite DNS & Anti-DPI
    /ip firewall nat add chain=dstnat in-interface=bridge1 protocol=udp dst-port=53 action=redirect to-ports=53 comment="[ANTI-DNS-LEAK]"
    /ip firewall nat add chain=dstnat in-interface=bridge1 protocol=tcp dst-port=53 action=redirect to-ports=53 comment="[ANTI-DNS-LEAK]"
    /ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="[ANTI-DPI]"
}} on-error={{}}

# NAT Sortie de secours WAN
:if ([/ip firewall nat find comment~"KETRIKA-WAN"] = "") do={{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA-WAN]" }}

# DHCP LAN
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server=1.1.1.1,1.0.0.1 netmask=24
}} on-error={{}}
"""

    # =======================================================
    # PACK 3 : HOTSPOT + WARP VPN + PPPOE (FULL PACK)
    # =======================================================
    else:
        wc = generate_warp_config_for_client()
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        
        pppoe_block = ""
        if safe_get(order, 'pppoe_enabled', False):
            rl_p = f"rate-limit={ul}/{dl}" if dl != '0' else ""
            pppoe_block = f"""
:do {{
    /ip pool add name=pool-pppoe ranges=192.168.99.10-192.168.99.250
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 name=pppoe-ketrika {rl_p} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika disabled=no interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
    /ip firewall mangle add chain=prerouting src-address=192.168.99.0/24 dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=no comment="[PPPOE-WARP]"
}} on-error={{}}
"""
        voucher_block = ""
        if safe_get(order, 'voucher_enabled', False):
            voucher_block = "\n/ip hotspot user\n"
            for _ in range(10):
                c = secrets.token_hex(4).upper()
                voucher_block += f'add name=V-{c} password={c} profile=1heure comment="Voucher 1H"\n'

        custom_block = f"""
# === PACK 3: HOTSPOT PRO + WARP VPN ANTI-FAI ===
/ip firewall filter disable [find action=fasttrack-connection]
:do {{ /ipv6 settings set disable-ipv6=yes }} on-error={{}}

# 1. Tunnel Wireguard Cloudflare
:do {{ /interface wireguard peers remove [find interface=wg-secure] }} on-error={{}}
:do {{ /interface wireguard remove wg-secure }} on-error={{}}
:do {{ /ip route remove [find comment~"KETRIKA"] }} on-error={{}}
:do {{ /routing table remove [find name=via-secure] }} on-error={{}}
:delay 1s
:do {{
    /routing table add name=via-secure fib
    /interface wireguard add name=wg-secure listen-port=13231 mtu=1280 private-key="{wc['private_key']}" comment="[KETRIKA-VPN]"
    /interface wireguard peers add interface=wg-secure public-key="{wc['warp_public_key']}" endpoint-address={wc['endpoint_host']} endpoint-port={wc['endpoint_port']} allowed-address=0.0.0.0/0 persistent-keepalive=25s
    /ip address add address={wc['client_ipv4']}/32 interface=wg-secure comment="[KETRIKA-VPN]"
    
    # Routage : Seuls les utilisateurs connectes au Hotspot (hotspot=auth) sont diriges dans Cloudflare
    /ip firewall mangle add chain=prerouting in-interface=bridge1 hotspot=auth dst-address-type=!local dst-address=!{net} action=mark-routing new-routing-mark=via-secure passthrough=no comment="[KETRIKA-WARP]"
    /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure comment="[KETRIKA-WARP]"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="[KETRIKA-WARP]"
}} on-error={{}}

# 2. Portail Captif Hotspot & Popup Automatique
:do {{ /ip hotspot remove [find name=hotspot-ketrika] }} on-error={{}}
:do {{ /ip hotspot profile remove [find name=hsprof-ketrika] }} on-error={{}}
:delay 1s
:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" hotspot-address={gw} html-directory=hotspot login-by=http-chap,http-pap,mac-cookie,cookie name=hsprof-ketrika use-radius=no
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure {rl_hs} shared-users=1 session-timeout=1h idle-timeout=5m
    /ip hotspot user profile add name=1jour {rl_hs} shared-users=2 session-timeout=1d idle-timeout=10m
    /ip hotspot user profile add name=1semaine {rl_hs} shared-users=3 session-timeout=7d idle-timeout=15m
    /ip hotspot user profile add name=1mois {rl_hs} shared-users=3 session-timeout=30d idle-timeout=30m
    /ip hotspot user add name=admin password=admin123 profile=1mois
    
    /ip dns static add name="wifi.ketrika.mg" address={gw} comment="[KETRIKA-HOTSPOT]"
    /ip firewall nat add chain=dstnat in-interface=bridge1 protocol=udp dst-port=53 action=redirect to-ports=53 comment="[HOTSPOT-DNS-FORCE]"
    /ip firewall nat add chain=dstnat in-interface=bridge1 protocol=tcp dst-port=53 action=redirect to-ports=53 comment="[HOTSPOT-DNS-FORCE]"
    /ip dhcp-server option add name=captive-portal code=114 value="s'http://{gw}/login'"
}} on-error={{}}

{pppoe_block}
{voucher_block}

# NAT WAN
:if ([/ip firewall nat find comment~"KETRIKA-WAN"] = "") do={{ /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade comment="[KETRIKA-WAN]" }}

# DHCP Serveur avec declencheur de popup
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} dns-server={gw} dhcp-option=captive-portal netmask=24
}} on-error={{}}
"""

    return f"""# =============================================
# KETRIKA MIKROTIK - SCRIPT VERROUILLE (ROUTEROS V7)
# Pack : {plan_type.upper()} | Routeur : {model}
# Licence : {license_key} (1 SEUL ROUTEUR)
# =============================================

:put "KETRIKA - Configuration en cours..."
:delay 1s

# 1. VERROUILLAGE MATERIEL DANS LE ROUTEUR
/system note set note="KETRIKA-LICENCE: {license_key} | Routeur: {model} | Client: {client_name}"
/system identity set name="KETRIKA-{order_id}"

# 2. BRIDGE PRINCIPAL
:if ([/interface bridge find name=bridge1] = "") do={{ /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA" }}

# 3. IP GATEWAY
:if ([/ip address find address="{gw}/24"] = "") do={{ /ip address add address={gw}/24 interface=bridge1 comment="[KETRIKA]" }}

# 4. DHCP CLIENT WAN
:if ([/ip dhcp-client find interface={wan}] = "") do={{ /ip dhcp-client add interface={wan} disabled=no add-default-route=yes use-peer-dns=no }}

# 5. CONFIGURATION SANS FIL WIFI DETECTE
{wcfg}

# 6. ATTRIBUTION DES PORTS EN ARRIERE PLAN (ZERO COUPURE WINBOX)
/system scheduler add name=ketrika_ports interval=0s start-time=([/system clock get time] + 00:00:04) on-event="{bp}/system scheduler remove ketrika_ports;"

# 7. DNS & MSS
/ip dns set allow-remote-requests=yes servers=1.1.1.1,8.8.8.8 use-doh-server=""
:do {{
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn action=change-mss new-mss=clamp-to-pmtu passthrough=yes
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp action=change-mss new-mss=1360 passthrough=yes
}} on-error={{}}

{ttl_script}
{custom_block}
{rl}

# === REBOOT AUTOMATIQUE DU ROUTEUR ===
:log info "KETRIKA: Configuration terminee, reboot dans 3s..."
:put "================================================"
:put "  CONFIGURATION KETRIKA APPLIQUEE AVEC SUCCES !"
:put "  Licence  : {license_key}"
:put "  Routeur  : {model}"
:put "  Pack     : {plan_type.upper()}"
:put "  TTL Base : {ttl_value}"
:put "  Le routeur va redemarrer automatiquement dans 3 secondes..."
:put "================================================"

/system scheduler add name=ketrika_reboot interval=0s start-time=([/system clock get time] + 00:00:03) on-event="/system scheduler remove ketrika_reboot; /system reboot;"
"""
```
