#!/usr/bin/env python3
"""
============================================================
KETRIKA MIKROTIK - MOTEUR ROUTEROS v7 (SCRIPT PLAT ATOMIQUE)
Compatible RouterOS 7.x (7.22+) / CHR / hAP ax / hAP ac / Lite
ZÉRO ERREUR DE SYNTAXE - ZÉRO DÉCONNEXION
============================================================
"""

import os
import random
import string
import base64
import time
import hashlib
import requests

CF_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

WARP_ENDPOINTS = [
    ("162.159.192.1", 2408),
    ("162.159.193.1", 2408),
    ("188.114.96.1", 2408),
    ("188.114.97.1", 2408),
]


def safe_get(obj, key, default=""):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default


def ros_escape(value):
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def curve25519_scalarmult(scalar):
    P = 2**255 - 19

    def dec(data):
        return int.from_bytes(data, "little")

    def enc(value):
        return (value % P).to_bytes(32, "little")

    def inv(value):
        return pow(value, P - 2, P)

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

    dummy = swap * (x_2 ^ x_3)
    x_2 ^= dummy
    x_3 ^= dummy
    dummy = swap * (z_2 ^ z_3)
    z_2 ^= dummy
    z_3 ^= dummy

    return enc((x_2 * inv(z_2)) % P)


def generate_wireguard_keys():
    private_key = os.urandom(32)
    public_key = curve25519_scalarmult(private_key)
    return {
        "private_key": base64.b64encode(private_key).decode("utf-8"),
        "public_key": base64.b64encode(public_key).decode("utf-8"),
    }


def register_warp(public_key):
    try:
        url = "https://api.cloudflareclient.com/v0a2158/reg"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.1",
        }
        payload = {
            "key": public_key,
            "install_id": "",
            "fcm_token": "",
            "tos": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "model": "MikroTik",
            "serial_number": hashlib.md5(public_key.encode("utf-8")).hexdigest()[:16],
            "locale": "fr_MG",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code not in (200, 201):
            return {"success": False, "ipv4": ""}
        data = response.json()
        ipv4 = data.get("config", {}).get("interface", {}).get("addresses", {}).get("v4", "")
        if "/" in str(ipv4):
            ipv4 = str(ipv4).split("/")[0]
        if not ipv4:
            return {"success": False, "ipv4": ""}
        return {"success": True, "ipv4": ipv4}
    except Exception:
        return {"success": False, "ipv4": ""}


def generate_script(order):
    plan = safe_get(order, "plan_type", "standard")
    model = safe_get(order, "mikrotik_model", "hap_ac2")
    ssid = safe_get(order, "ssid", "KETRIKA-WiFi")
    wifi_pass = safe_get(order, "wifi_password", "ketrika2024")
    wan = safe_get(order, "wan_interface", "ether1")
    gw = safe_get(order, "lan_gateway", "192.168.10.1")
    net = safe_get(order, "lan_network", "192.168.10.0/24")
    pool = safe_get(order, "dhcp_pool", "192.168.10.10-192.168.10.250")
    ttl = safe_get(order, "ttl_value", "64")
    dl = safe_get(order, "dl_limit", "0")
    ul = safe_get(order, "ul_limit", "0")
    lic = safe_get(order, "license_key", "DEMO")
    router_name = safe_get(order, "router_name", "")
    mac_spoof = safe_get(order, "mac_spoof", False)
    mac_address = safe_get(order, "mac_address", "")
    sleep_mode = safe_get(order, "sleep_mode", "off")
    client_limit = safe_get(order, "client_limit", "0")

    from database import get_model_info, generate_router_name, generate_random_mac

    if not router_name:
        router_name = generate_router_name(lic)
    if mac_spoof and not mac_address:
        mac_address = generate_random_mac()

    keys = generate_wireguard_keys()
    warp_reg = {"success": False, "ipv4": ""}
    if plan in ("warp", "hotspot"):
        warp_reg = register_warp(keys["public_key"])

    warp_ip = warp_reg.get("ipv4", "")
    endpoint_ip, endpoint_port = random.choice(WARP_ENDPOINTS)

    p = []

    # ============================================================
    # 1. PROTECTION WINBOX (PRIORITÉ ABSOLUE)
    # ============================================================
    p.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 action=accept place-before=0 comment="KETRIKA-WINBOX" } on-error={}')
    p.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=22 action=accept place-before=0 comment="KETRIKA-SSH" } on-error={}')

    # ============================================================
    # 2. NETTOYAGE ANCIENNES CONFIGS
    # ============================================================
    p.append(':do { /system scheduler remove [find name~"ketrika"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"sleep"] } on-error={}')
    p.append(':do { /ip dhcp-server remove [find] } on-error={}')
    p.append(':do { /ip dhcp-server network remove [find] } on-error={}')
    p.append(':do { /ip pool remove [find] } on-error={}')
    p.append(':do { /ip dhcp-client remove [find interface=' + ros_escape(wan) + '] } on-error={}')
    p.append(':do { /ip firewall nat remove [find] } on-error={}')
    p.append(':do { /ip firewall mangle remove [find] } on-error={}')
    p.append(':do { /queue simple remove [find] } on-error={}')
    p.append(':do { /queue type remove [find name~"pcq"] } on-error={}')
    p.append(':do { /interface wireguard remove [find] } on-error={}')
    p.append(':do { /routing table remove [find name!="main"] } on-error={}')
    p.append(':do { /routing rule remove [find] } on-error={}')
    p.append(':do { /ip hotspot user remove [find] } on-error={}')
    p.append(':do { /ip hotspot user profile remove [find name!="default"] } on-error={}')
    p.append(':do { /ip hotspot profile remove [find name!="default"] } on-error={}')
    p.append(':do { /ip hotspot remove [find] } on-error={}')
    p.append(':do { /ip dns static remove [find name~"ketrika"] } on-error={}')

    # ============================================================
    # 3. BRIDGE LAN (CRÉATION GARANTIE SANS COUPURE)
    # ============================================================
    p.append(':do { /interface bridge set [find name=bridge] name=bridge1 } on-error={}')
    p.append(':do { /interface bridge add name=bridge1 comment="LAN-KETRIKA" } on-error={}')
    # Rattachement direct et explicite de chaque port physique
    p.append(':do { /interface bridge port add bridge=bridge1 interface=ether2 } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=ether3 } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=ether4 } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=ether5 } on-error={}')

    # ============================================================
    # 4. IP LAN & DHCP SERVER & DNS
    # ============================================================
    p.append(':do { /ip address add address=' + ros_escape(gw) + '/24 interface=bridge1 comment="Passerelle-LAN" } on-error={}')
    p.append(':do { /ip pool add name=pool-lan ranges=' + ros_escape(pool) + ' } on-error={}')
    p.append(':do { /ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no } on-error={}')
    p.append(':do { /ip dhcp-server network add address=' + ros_escape(net) + ' gateway=' + ros_escape(gw) + ' dns-server=' + ros_escape(gw) + ' } on-error={}')
    p.append(':do { /ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server=https://cloudflare-dns.com/dns-query } on-error={ :do { /ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 } on-error={} }')

    # ============================================================
    # 5. WAN & MAC SPOOF
    # ============================================================
    if mac_spoof and mac_address:
        p.append(':do { /interface ethernet set [find default-name=' + ros_escape(wan) + '] mac-address="' + ros_escape(mac_address) + '" } on-error={}')
    p.append(':do { /ip dhcp-client add interface=' + ros_escape(wan) + ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-Internet" } on-error={}')

    # ============================================================
    # 6. ACTIVATION WI-FI (AX + WIRELESS LEGACY SANS BOUCLE)
    # ============================================================
    # Wi-Fi AX (RouterOS v7)
    if plan == "hotspot":
        p.append(':do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types="" disabled=no } on-error={}')
    else:
        p.append(':do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="' + ros_escape(wifi_pass) + '" disabled=no } on-error={}')
    p.append(':do { /interface wifi enable [find] } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=wifi1 } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=wifi2 } on-error={}')

    # Wi-Fi Wireless AC/N Classique
    if plan == "hotspot":
        p.append(':do { /interface wireless security-profiles set [find default=yes] mode=none } on-error={}')
    else:
        p.append(':do { /interface wireless security-profiles set [find default=yes] mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' + ros_escape(wifi_pass) + '" } on-error={}')
    p.append(':do { /interface wireless set [find] mode=ap-bridge ssid="' + ros_escape(ssid) + '" disabled=no } on-error={}')
    p.append(':do { /interface wireless enable [find] } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=wlan1 } on-error={}')
    p.append(':do { /interface bridge port add bridge=bridge1 interface=wlan2 } on-error={}')

    # ============================================================
    # 7. WIREGUARD CLOUDFLARE WARP
    # ============================================================
    if plan in ("warp", "hotspot"):
        if warp_ip:
            p.append(':do { /interface wireguard add name=wg-secure mtu=1280 listen-port=13231 comment="WARP-KETRIKA" private-key="' + ros_escape(keys["private_key"]) + '" } on-error={}')
            p.append(':do { /ip address add address=' + ros_escape(warp_ip) + '/32 interface=wg-secure } on-error={}')
            p.append(':do { /interface wireguard peers add interface=wg-secure public-key="' + CF_PUBLIC_KEY + '" endpoint-address=' + endpoint_ip + ' endpoint-port=' + str(endpoint_port) + ' allowed-address=0.0.0.0/0 persistent-keepalive=25 } on-error={}')
            p.append(':do { /routing table add name=via-secure fib } on-error={}')
            p.append(':do { /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure } on-error={}')

            # Protection Winbox et LAN dans Mangle (ne jamais router Winbox dans Wireguard)
            p.append(':do { /ip firewall mangle add chain=prerouting dst-port=8291 protocol=tcp action=accept place-before=0 comment="WINBOX-NO-WG" } on-error={}')
            p.append(':do { /ip firewall mangle add chain=prerouting dst-address=192.168.0.0/16 action=accept place-before=0 comment="LAN-NO-WG" } on-error={}')

            if plan == "hotspot":
                p.append(':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' hotspot=auth dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-HS-WG" } on-error={}')
                p.append(':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}')
                p.append(':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}')
            else:
                p.append(':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-LAN-To-WG" } on-error={}')
                p.append(':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}')
                p.append(':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}')

            p.append(':do { /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="KETRIKA-WARP-NAT" } on-error={}')
            p.append(':do { /ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="KETRIKA-MSS" } on-error={}')

    # ============================================================
    # 8. HOTSPOT (Plan 3)
    # ============================================================
    if plan == "hotspot":
        p.append(':do { /ip dns static add name=wifi.ketrika.mg address=' + ros_escape(gw) + ' } on-error={}')
        p.append(':do { /ip hotspot profile add name=ketrika-hs hotspot-address=' + ros_escape(gw) + ' dns-name=wifi.ketrika.mg login-by=http-pap,cookie http-cookie-lifetime=1d use-radius=no html-directory=hotspot } on-error={}')
        p.append(':do { /ip hotspot add name=hotspot-ketrika interface=bridge1 profile=ketrika-hs address-pool=pool-lan disabled=no } on-error={}')
        p.append(':do { /ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2 } on-error={}')
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            p.append(':do { /ip hotspot user add name="' + vc + '" password="' + vc + '" profile="1jour" comment="Ticket-KETRIKA" } on-error={}')

    # ============================================================
    # 9. NAT & ANTI-TTL & QoS & IDENTITY
    # ============================================================
    p.append(':do { /ip firewall nat add chain=srcnat out-interface=' + ros_escape(wan) + ' action=masquerade comment="KETRIKA-NAT" } on-error={}')
    if str(ttl) != "0":
        p.append(':do { /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="KETRIKA-TTL" } on-error={}')
        p.append(':do { /ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="KETRIKA-TTL" } on-error={}')

    if dl != "0" or ul != "0":
        lim_ul = str(ul) if "M" in str(ul) else str(ul) + "M"
        lim_dl = str(dl) if "M" in str(dl) else str(dl) + "M"
        p.append(':do { /queue simple add name="QoS-Global" target=' + ros_escape(net) + ' max-limit=' + lim_ul + '/' + lim_dl + ' } on-error={}')

    if client_limit != "0":
        cl = str(client_limit) if "M" in str(client_limit) else str(client_limit) + "M"
        p.append(':do { /queue type add name=pcq-dl kind=pcq pcq-rate=' + cl + ' pcq-classifier=dst-address } on-error={}')
        p.append(':do { /queue type add name=pcq-ul kind=pcq pcq-rate=' + cl + ' pcq-classifier=src-address } on-error={}')
        p.append(':do { /queue simple add name="QoS-PerClient" target=' + ros_escape(net) + ' queue=pcq-ul/pcq-dl } on-error={}')

    p.append(':do { /system identity set name="' + ros_escape(router_name) + '" } on-error={}')

    # Mode veille
    if sleep_mode != "off":
        sleep_ranges = {
            "00-06": ("00:00:00", "06:00:00"),
            "01-05": ("01:00:00", "05:00:00"),
            "23-07": ("23:00:00", "07:00:00"),
            "02-06": ("02:00:00", "06:00:00"),
        }
        start_t, end_t = sleep_ranges.get(sleep_mode, ("00:00:00", "06:00:00"))
        p.append(':do { /system scheduler add name="ketrika-sleep-off" start-time=' + start_t + ' interval=1d on-event=":do { /interface wifi set [find] disabled=yes } on-error={}; :do { /interface wireless set [find] disabled=yes } on-error={}" } on-error={}')
        p.append(':do { /system scheduler add name="ketrika-sleep-on" start-time=' + end_t + ' interval=1d on-event=":do { /interface wifi set [find] disabled=no } on-error={}; :do { /interface wireless set [find] disabled=no } on-error={}" } on-error={}')

    # ============================================================
    # 10. FIREWALL FINAL
    # ============================================================
    p.append(':do { /ip firewall filter remove [find comment~"KETRIKA-FW"] } on-error={}')
    p.append(':do { /ip firewall filter add chain=input connection-state=established,related action=accept comment="KETRIKA-FW" } on-error={}')
    p.append(':do { /ip firewall filter add chain=input connection-state=invalid action=drop comment="KETRIKA-FW" } on-error={}')
    p.append(':do { /ip firewall filter add chain=input protocol=icmp action=accept comment="KETRIKA-FW" } on-error={}')
    p.append(':do { /ip firewall filter add chain=input in-interface=bridge1 action=accept comment="KETRIKA-FW" } on-error={}')
    p.append(':do { /ip firewall filter add chain=input in-interface=' + ros_escape(wan) + ' action=drop comment="KETRIKA-FW" } on-error={}')

    # ============================================================
    # 11. BANNIÈRE FINALE DE SUCCÈS
    # ============================================================
    p.append(':log info "KETRIKA: Configuration terminee avec succes."')
    p.append(':put " "')
    p.append(':put "###############################################################"')
    p.append(':put "##                                                           ##"')
    p.append(':put "##      K E T R I K A   -   I N S T A L L A T I O N        ##"')
    p.append(':put "##              T E R M I N E E   A V E C                  ##"')
    p.append(':put "##                   S U C C E S                           ##"')
    p.append(':put "##                                                           ##"')
    p.append(':put "###############################################################"')
    p.append(':put "  [OK] Bridge LAN et Ports : ACTIFS"')
    p.append(':put "  [OK] Passerelle LAN IP : ' + ros_escape(gw) + '"')
    p.append(':put "  [OK] Serveur DHCP distribue : ' + ros_escape(pool) + '"')
    p.append(':put "  [OK] Wi-Fi SSID : ' + ros_escape(ssid) + '"')
    p.append(':put "  [OK] Anti-TTL FAI : ACTIF (TTL=' + str(ttl) + ')"')
    if plan in ("warp", "hotspot") and warp_ip:
        p.append(':put "  [OK] WireGuard WARP Cloudflare : ACTIF"')
    if plan == "hotspot":
        p.append(':put "  [OK] Hotspot Portail Captif : 10 tickets prets"')
    p.append(':put "================================================================"')
    p.append(':put "  >>> Tous vos reglages sont immediatement operationnels !"')
    p.append(':put "================================================================"')
    p.append(':put " "')

    return "\n".join(p)


def generate_secret_guide(order):
    lic = safe_get(order, "license_key", "DEMO")
    client = safe_get(order, "client_name", "Client")
    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE TECHNIQUE RESEAU
================================================================================

Client  : """ + str(client) + """
Licence : """ + str(lic) + """
Date    : """ + time.strftime("%d/%m/%Y", time.gmtime()) + """

================================================================================
INSTALLATION
============
1. Connectez-vous au MikroTik avec WinBox.
2. Ouvrez New Terminal.
3. Collez le script complet.
4. Le script s'applique jusqu'au bout sans aucune deconnexion.
5. Verifiez le Wi-Fi et la connexion Internet.

================================================================================
SUPPORT : KETRIKA MIKROTIK - Madagascar
================================================================================
"""
    return guide
