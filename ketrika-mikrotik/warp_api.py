# warp_api.py - Génération des configs WARP/WireGuard
import secrets

def generate_warp_config(order):
    """Génère la section WireGuard WARP pour le script RSC"""

    # Clés WireGuard (à remplacer par les vraies depuis ton VPS)
    private_key = "GENERER_AVEC_wg_genkey"
    public_key_vps = "CLE_PUBLIQUE_DE_TON_VPS"
    vps_ip = "IP_DE_TON_VPS"
    vps_port = "51820"

    return f"""
# =============================================
# ☁️ CLOUDFLARE WARP VIA WIREGUARD
# =============================================
# Généré par KETRIKA WARP API
# Licence: {order.license_key}

/interface wireguard
add listen-port=13231 mtu=1420 name=wg-warp \\
    private-key="{private_key}" \\
    comment="[KETRIKA-WARP] Tunnel"

/interface wireguard peers
add allowed-address=0.0.0.0/0 \\
    endpoint-address={vps_ip} \\
    endpoint-port={vps_port} \\
    interface=wg-warp \\
    public-key="{public_key_vps}" \\
    persistent-keepalive=25 \\
    comment="[KETRIKA-WARP] Peer"

/ip address
add address=10.0.0.2/24 interface=wg-warp network=10.0.0.0

# --- Routage via WARP ---
/ip firewall mangle
add chain=prerouting in-interface=bridge1 dst-address=!{order.lan_network} \\
    action=mark-routing new-routing-mark=via-warp passthrough=yes \\
    comment="[KETRIKA-WARP] Mark for WARP"

/ip route
add dst-address=0.0.0.0/0 gateway=10.0.0.1 routing-table=via-warp \\
    comment="[KETRIKA-WARP] Default via WARP"

/ip firewall nat
add chain=srcnat out-interface=wg-warp action=masquerade \\
    comment="[KETRIKA-WARP] NAT WARP"

/ip dns
set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes
"""


def generate_base_anti_detection(order):
    """Anti-détection Starlink (tous les plans)"""
    wan = order.wan_interface
    ttl = order.ttl_value

    return f"""
# =============================================
# 🛡️ ANTI-DÉTECTION STARLINK
# =============================================

/ip firewall mangle
add chain=postrouting out-interface={wan} action=change-ttl \\
    new-ttl=set:{ttl} passthrough=no \\
    comment="[KETRIKA] Fix TTL OUT"

add chain=prerouting in-interface={wan} action=change-ttl \\
    new-ttl=set:{ttl} passthrough=no \\
    comment="[KETRIKA] Fix TTL IN"

add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn \\
    action=change-mss new-mss=clamp-to-pmtu passthrough=yes \\
    comment="[KETRIKA] Clamp MSS"

add chain=forward out-interface={wan} protocol=tcp \\
    action=change-mss new-mss=1360 passthrough=yes \\
    comment="[KETRIKA] Normalize MSS"

/ip firewall filter
add chain=forward out-interface={wan} protocol=icmp action=drop \\
    comment="[KETRIKA] Block ICMP Forward"
add chain=output out-interface={wan} protocol=icmp action=drop \\
    comment="[KETRIKA] Block ICMP Output"

add chain=input connection-state=established,related action=accept
add chain=input connection-state=invalid action=drop
add chain=input in-interface={wan} protocol=tcp dst-port=8291 action=drop
add chain=input in-interface={wan} action=drop
add chain=forward connection-state=established,related action=accept
add chain=forward connection-state=invalid action=drop
add chain=forward in-interface=bridge1 out-interface={wan} action=accept
"""


def generate_hotspot_section(order):
    """Section Hotspot + PPPoE + Vouchers"""
    rsc = f"""
# =============================================
# 🌐 HOTSPOT
# =============================================
/ip hotspot profile
add dns-name="wifi.ketrika.mg" hotspot-address={order.lan_gateway} \\
    login-by=http-chap,http-pap name=hsprof-ketrika

/ip hotspot
add address-pool=pool-lan disabled=no interface=bridge1 \\
    name=hotspot-ketrika profile=hsprof-ketrika

/ip hotspot user profile
add name=1heure rate-limit={order.ul_limit}/{order.dl_limit} \\
    shared-users=1 session-timeout=1h
add name=1jour rate-limit={order.ul_limit}/{order.dl_limit} \\
    shared-users=2 session-timeout=1d
add name=1semaine rate-limit={order.ul_limit}/{order.dl_limit} \\
    shared-users=3 session-timeout=7d
add name=1mois rate-limit={order.ul_limit}/{order.dl_limit} \\
    shared-users=3 session-timeout=30d

/ip hotspot user
add name=admin password=admin123 profile=1mois
"""

    if order.pppoe_enabled:
        rsc += f"""
# =============================================
# 📡 PPPoE SERVER
# =============================================
/ip pool
add name=pool-pppoe ranges=192.168.99.10-192.168.99.250

/ppp profile
add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 \\
    name=pppoe-ketrika rate-limit={order.ul_limit}/{order.dl_limit} \\
    remote-address=pool-pppoe

/interface pppoe-server server
add default-profile=pppoe-ketrika disabled=no interface=bridge1 \\
    one-session-per-host=yes service-name=KETRIKA

/ppp secret
add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
"""

    if order.voucher_enabled:
        rsc += "\n# --- Vouchers ---\n/ip hotspot user\n"
        for i in range(10):
            code = secrets.token_hex(4).upper()
            rsc += f'add name=V-{code} password={code} profile=1heure comment="Voucher 1H"\n'

    return rsc


def generate_full_script(order):
    """Génère le script RSC COMPLET selon le plan"""
    from database import MIKROTIK_MODELS

    model_info = MIKROTIK_MODELS.get(order.mikrotik_model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    num_ports = model_info['ports']
    has_wifi = model_info['wifi']
    has_5g = model_info.get('wifi5g', False)
    wan = order.wan_interface
    gw = order.lan_gateway
    net = order.lan_network
    pool = order.dhcp_pool

    # Ports LAN
    lan_ports = [f"ether{i}" for i in range(2, num_ports + 1)]
    bridge_ports = "".join(f"add bridge=bridge1 interface={p}\n" for p in lan_ports)
    if has_wifi:
        bridge_ports += "add bridge=bridge1 interface=wlan1\n"
    if has_5g:
        bridge_ports += "add bridge=bridge1 interface=wlan2\n"

    # WiFi config
    wifi_cfg = ""
    if has_wifi:
        wifi_cfg = f"""
/interface wifi
set wlan1 configuration.mode=ap configuration.ssid="{order.ssid}" \\
    security.authentication-types=wpa2-psk \\
    security.passphrase="{order.wifi_password}" \\
    channel.frequency=2412 channel.width=20/40mhz-Ce disabled=no
"""
    if has_5g:
        wifi_cfg += f"""
/interface wifi
set wlan2 configuration.mode=ap configuration.ssid="{order.ssid}-5G" \\
    security.authentication-types=wpa2-psk \\
    security.passphrase="{order.wifi_password}" \\
    channel.frequency=5180 channel.width=20/40/80mhz-Ceee disabled=no
"""

    # ---- ASSEMBLAGE COMPLET ----
    rsc = f"""# =============================================
# KETRIKA MIKROTIK - Configuration Auto
# Plan: {order.plan_type.upper()}
# Modèle: {order.mikrotik_model} ({num_ports} ports)
# Licence: {order.license_key}
# RouterOS v7
# =============================================

# === 1. BRIDGE ===
/interface bridge
add name=bridge1 protocol-mode=none

/interface bridge port
{bridge_ports}

# === 2. IP ===
/ip address
add address={gw}/24 interface=bridge1

# === 3. DHCP WAN (Starlink) ===
/ip dhcp-client
add interface={wan} disabled=no add-default-route=yes use-peer-dns=no

# === 4. DHCP LAN ===
/ip pool
add name=pool-lan ranges={pool}

/ip dhcp-server
add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no

/ip dhcp-server network
add address={net} gateway={gw} dns-server=1.1.1.1,8.8.8.8 netmask=24

# === 5. DNS ===
/ip dns
set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8

# === 6. NAT ===
/ip firewall nat
add chain=srcnat out-interface={wan} action=masquerade

# === 7. WIFI ===
{wifi_cfg}
"""

    # Anti-détection (TOUS les plans)
    rsc += generate_base_anti_detection(order)

    # WARP (plans warp et hotspot)
    if order.plan_type in ['warp', 'hotspot']:
        rsc += generate_warp_config(order)

    # Hotspot (plan hotspot)
    if order.plan_type == 'hotspot':
        rsc += generate_hotspot_section(order)

    # Rate limit
    rsc += f"""
# === RATE LIMIT ===
/queue type
add kind=pcq name=pcq-dl pcq-classifier=dst-address pcq-rate={order.dl_limit}
add kind=pcq name=pcq-ul pcq-classifier=src-address pcq-rate={order.ul_limit}

/queue simple
add name="KETRIKA-Limit" target={net} \\
    queue=pcq-ul/pcq-dl comment="[KETRIKA] Rate Limit"
"""

    # Footer avec les 3 méthodes
    rsc += f"""
# =============================================
# ✅ TERMINÉ - Licence: {order.license_key}
# =============================================
# 3 MÉTHODES (sans redémarrage):
# 1) WinBox → New Terminal → Coller ce script
# 2) WinBox → Files → Upload .rsc → /import file-name=ketrika.rsc
# 3) SSH: ssh admin@{gw} → Coller ou /import
# =============================================
"""
    return rsc
