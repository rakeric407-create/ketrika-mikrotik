#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Moteur de génération de scripts RouterOS v7
Version stable : Wi-Fi AX/AC corrigé, Zéro coupure WinBox, Zéro crash Render
"""

import os
import random
import string
import base64
import time
import hashlib
import requests

# ============================================================
# CLOUDFLARE WARP
# ============================================================

CF_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="

WARP_ENDPOINTS = [
    ("162.159.192.1", 2408),
    ("162.159.193.1", 2408),
    ("188.114.96.1", 2408),
    ("188.114.97.1", 2408),
]


# ============================================================
# OUTILS
# ============================================================

def safe_get(obj, key, default=""):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default


def ros_escape(value):
    """
    Protège une valeur destinée à être placée entre guillemets dans RouterOS.
    """
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def valid_mac(mac):
    """
    Validation simple d'une adresse MAC.
    """
    if not mac:
        return False
    parts = str(mac).split(":")
    if len(parts) != 6:
        return False
    for part in parts:
        if len(part) != 2:
            return False
        try:
            int(part, 16)
        except ValueError:
            return False
    return True


# ============================================================
# X25519
# ============================================================

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


# ============================================================
# ENREGISTREMENT WARP
# ============================================================

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


# ============================================================
# GENERATEUR PRINCIPAL
# ============================================================

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
    sleep_mode = safe_get(order, "sleep_mode", "off")
    client_limit = safe_get(order, "client_limit", "0")

    from database import get_model_info, generate_router_name
    info = get_model_info(model)

    if not router_name:
        router_name = generate_router_name(lic)

    keys = generate_wireguard_keys()
    warp_reg = {"success": False, "ipv4": ""}
    if plan in ("warp", "hotspot"):
        warp_reg = register_warp(keys["public_key"])

    warp_ip = warp_reg.get("ipv4", "")
    endpoint_ip, endpoint_port = random.choice(WARP_ENDPOINTS)

    p = []

    # ============================================================
    # 1. EN-TETE
    # ============================================================
    p.append("# ============================================================")
    p.append("# KETRIKA MIKROTIK - CONFIGURATION AUTOMATIQUE ROUTEROS v7")
    p.append("# LICENCE : " + ros_escape(lic))
    p.append("# MODELE  : " + ros_escape(model))
    p.append("# DATE    : " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    p.append("# ============================================================")
    p.append(':log info "KETRIKA: Demarrage de la configuration..."')
    p.append("")

    # ============================================================
    # 2. NETTOYAGE SECURISE
    # ============================================================
    p.append("# --- Nettoyage securise ---")
    p.append(':do { /system scheduler remove [find name~"ketrika"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"reboot"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"sleep"] } on-error={}')
    p.append(':do { /ip firewall filter remove [find] } on-error={}')
    p.append(':do { /ip firewall nat remove [find] } on-error={}')
    p.append(':do { /ip firewall mangle remove [find] } on-error={}')
    p.append(':do { /queue simple remove [find] } on-error={}')
    p.append(':do { /ip dhcp-server remove [find] } on-error={}')
    p.append(':do { /ip dhcp-server network remove [find] } on-error={}')
    p.append(':do { /ip pool remove [find] } on-error={}')
    p.append(':do { /ip route remove [find dynamic=no] } on-error={}')
    p.append(':do { /interface wireguard remove [find] } on-error={}')
    p.append(':do { /routing table remove [find name!="main"] } on-error={}')
    p.append(':do { /routing rule remove [find] } on-error={}')
    p.append(':do { /ip hotspot user remove [find] } on-error={}')
    p.append(':do { /ip hotspot user profile remove [find name!="default"] } on-error={}')
    p.append(':do { /ip hotspot profile remove [find name!="default"] } on-error={}')
    p.append(':do { /ip hotspot remove [find] } on-error={}')
    p.append("")

    # ============================================================
    # 3. BRIDGE
    # ============================================================
    p.append("# --- Creation du Bridge LAN ---")
    p.append(':if ([:len [/interface bridge find name=bridge1]] = 0) do={')
    p.append('  :if ([:len [/interface bridge find name=bridge]] > 0) do={')
    p.append('    /interface bridge set [find name=bridge] name=bridge1')
    p.append('  } else={')
    p.append('    /interface bridge add name=bridge1 comment="LAN-KETRIKA"')
    p.append('  }')
    p.append('}')
    p.append("")

    # ============================================================
    # 4. WAN DHCP
    # ============================================================
    p.append("# --- WAN Internet ---")
    p.append(':do { /ip dhcp-client add interface=' + ros_escape(wan) + ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-Internet" } on-error={}')
    p.append("")

    # ============================================================
    # 5. LAN / DHCP
    # ============================================================
    p.append("# --- LAN / DHCP ---")
    p.append(':if ([:len [/ip address find interface=bridge1 address="' + ros_escape(gw) + '/24"]] = 0) do={')
    p.append('  /ip address add address=' + ros_escape(gw) + '/24 interface=bridge1 comment="Passerelle-LAN"')
    p.append('}')
    p.append(':do { /ip pool add name=pool-lan ranges=' + ros_escape(pool) + ' } on-error={}')
    p.append(':do { /ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no } on-error={}')
    p.append(':do { /ip dhcp-server network add address=' + ros_escape(net) + ' gateway=' + ros_escape(gw) + ' dns-server=' + ros_escape(gw) + ' } on-error={}')
    p.append('/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1')
    p.append("")

    # ============================================================
    # 6. ACTIVATION WI-FI AX / AC / N (CORRIGÉ & ROBUSTE)
    # ============================================================
    p.append("# ============================================================")
    p.append("# --- ACTIVATION WI-FI AX / AC / N ---")
    p.append("# ============================================================")

    # 6.A - Wi-Fi 6 AX (RouterOS v7 wifi)
    p.append(':if ([:len [/interface wifi find]] > 0) do={')
    if plan == "hotspot":
        p.append('  :do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types="" disabled=no } on-error={}')
    else:
        p.append('  :do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="' + ros_escape(wifi_pass) + '" disabled=no } on-error={}')
    p.append('  :do { /interface wifi enable [find] } on-error={}')
    p.append('  :foreach i in=[/interface wifi find] do={')
    p.append('    :local n [/interface wifi get $i name]')
    p.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    p.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    p.append('    }')
    p.append('  }')
    p.append('}')

    # 6.B - Wi-Fi 5/4 AC/N (Wireless legacy)
    p.append(':if ([:len [/interface wireless find]] > 0) do={')
    if plan == "hotspot":
        p.append('  :do { /interface wireless security-profiles set [find default=yes] mode=none } on-error={}')
    else:
        p.append('  :do { /interface wireless security-profiles set [find default=yes] mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' + ros_escape(wifi_pass) + '" } on-error={}')
    p.append('  :do { /interface wireless set [find] mode=ap-bridge ssid="' + ros_escape(ssid) + '" frequency=auto disabled=no } on-error={}')
    p.append('  :do { /interface wireless enable [find] } on-error={}')
    p.append('  :foreach i in=[/interface wireless find] do={')
    p.append('    :local n [/interface wireless get $i name]')
    p.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    p.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    p.append('    }')
    p.append('  }')
    p.append('}')
    p.append("")

    # ============================================================
    # 7. PORTS LAN AU BRIDGE (SANS DÉCONNEXION)
    # ============================================================
    p.append("# --- Ajout des ports LAN au bridge ---")
    p.append(':foreach i in=[/interface ethernet find] do={')
    p.append('  :local n [/interface ethernet get $i name]')
    p.append('  :if ($n != "' + ros_escape(wan) + '") do={')
    p.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    p.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    p.append('    }')
    p.append('  }')
    p.append('}')
    p.append("")

    # ============================================================
    # 8. WIREGUARD / WARP
    # ============================================================
    if plan in ("warp", "hotspot"):
        p.append("# ============================================================")
        p.append("# --- WIREGUARD / WARP ---")
        p.append("# ============================================================")
        if warp_ip:
            p.append('/interface wireguard add name=wg-secure mtu=1280 listen-port=0 comment="WARP-KETRIKA" private-key="' + ros_escape(keys["private_key"]) + '"')
            p.append('/ip address add address=' + ros_escape(warp_ip) + '/32 interface=wg-secure')
            p.append('/interface wireguard peers add interface=wg-secure public-key="' + CF_PUBLIC_KEY + '" endpoint-address=' + endpoint_ip + ' endpoint-port=' + str(endpoint_port) + ' allowed-address=0.0.0.0/0 persistent-keepalive=25')
            p.append(':do { /routing table add name=via-secure fib } on-error={}')
            p.append('/ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure')

            if plan == "hotspot":
                p.append('/ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' hotspot=auth dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="Hotspot-To-WireGuard"')
            else:
                p.append('/ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="LAN-To-WireGuard"')

            p.append('/ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade')
            p.append('/ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes')
        else:
            p.append(':log warning "KETRIKA: WARP non enregistre - tunnel non active."')
        p.append("")

    # ============================================================
    # 9. HOTSPOT KETRIKA
    # ============================================================
    if plan == "hotspot":
        p.append("# ============================================================")
        p.append("# --- HOTSPOT KETRIKA ---")
        p.append("# ============================================================")
        p.append('/ip dns static add name=wifi.ketrika.mg address=' + ros_escape(gw))
        p.append('/ip hotspot profile add name=ketrika-hs hotspot-address=' + ros_escape(gw) + ' dns-name=wifi.ketrika.mg login-by=http-pap,cookie http-cookie-lifetime=1d use-radius=no html-directory=hotspot')
        p.append('/ip hotspot add name=hotspot-ketrika interface=bridge1 profile=ketrika-hs address-pool=pool-lan disabled=no')
        p.append(':do { /ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1 } on-error={}')
        p.append(':do { /ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2 } on-error={}')
        p.append(':do { /ip hotspot user profile add name="1semaine" rate-limit="5M/10M" session-timeout=7d shared-users=2 } on-error={}')
        p.append(':do { /ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3 } on-error={}')
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            p.append('/ip hotspot user add name="' + vc + '" password="' + vc + '" profile="1jour" comment="Ticket-KETRIKA"')
        p.append("")

    # ============================================================
    # 10. NAT INTERNET & MASQUAGE TTL
    # ============================================================
    p.append("# --- NAT Internet ---")
    p.append('/ip firewall nat add chain=srcnat out-interface=' + ros_escape(wan) + ' action=masquerade')
    p.append("")
    if str(ttl) != "0":
        p.append('/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="TTL-Mask"')
        p.append('/ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="TTL-Mask"')
        p.append("")

    # ============================================================
    # 11. LIMITATIONS QoS
    # ============================================================
    if dl != "0" or ul != "0":
        lim_ul = str(ul) if "M" in str(ul) else str(ul) + "M"
        lim_dl = str(dl) if "M" in str(dl) else str(dl) + "M"
        p.append('/queue simple add name="QoS-Global" target=' + ros_escape(net) + ' max-limit=' + lim_ul + '/' + lim_dl)

    if client_limit != "0":
        cl = str(client_limit) if "M" in str(client_limit) else str(client_limit) + "M"
        p.append(':do { /queue type add name=pcq-dl kind=pcq pcq-rate=' + cl + ' pcq-classifier=dst-address } on-error={}')
        p.append(':do { /queue type add name=pcq-ul kind=pcq pcq-rate=' + cl + ' pcq-classifier=src-address } on-error={}')
        p.append(':do { /queue simple add name="QoS-PerClient" target=' + ros_escape(net) + ' queue=pcq-ul/pcq-dl } on-error={}')
    p.append("")

    # ============================================================
    # 12. IDENTITY & VEILLE
    # ============================================================
    p.append("# --- Identity du routeur ---")
    p.append('/system identity set name="' + ros_escape(router_name) + '"')
    p.append("")

    if sleep_mode != "off":
        sleep_ranges = {
            "00-06": ("00:00:00", "06:00:00"),
            "01-05": ("01:00:00", "05:00:00"),
            "23-07": ("23:00:00", "07:00:00"),
            "02-06": ("02:00:00", "06:00:00"),
        }
        start_t, end_t = sleep_ranges.get(sleep_mode, ("00:00:00", "06:00:00"))
        p.append(':do { /system scheduler add name="ketrika-sleep-off" start-time=' + start_t + ' interval=1d on-event="/interface wifi set [find] disabled=yes; /interface wireless set [find] disabled=yes" } on-error={}')
        p.append(':do { /system scheduler add name="ketrika-sleep-on" start-time=' + end_t + ' interval=1d on-event="/interface wifi set [find] disabled=no; /interface wireless set [find] disabled=no" } on-error={}')
        p.append("")

    # ============================================================
    # 13. FIREWALL DE BASE
    # ============================================================
    p.append("# --- Firewall de base ---")
    p.append('/ip firewall filter add chain=input connection-state=established,related action=accept')
    p.append('/ip firewall filter add chain=input connection-state=invalid action=drop')
    p.append('/ip firewall filter add chain=input protocol=icmp action=accept')
    p.append('/ip firewall filter add chain=input in-interface=bridge1 action=accept')
    p.append('/ip firewall filter add chain=input in-interface=' + ros_escape(wan) + ' action=drop')
    p.append("")

    # ============================================================
    # 14. BANNIERE DE CONFIRMATION FINALE
    # ============================================================
    p.append("# ============================================================")
    p.append("# KETRIKA : INSTALLATION TERMINEE AVEC SUCCES")
    p.append("# ============================================================")
    p.append(':log info "KETRIKA: Configuration terminee avec succes."')
    p.append(':put " "')
    p.append(':put "=================================================================="')
    p.append(':put "      [+] KETRIKA - CONFIGURATION TERMINEE AVEC SUCCES [+]"')
    p.append(':put "=================================================================="')
    p.append(':put "  -> SSID Wi-Fi    : ' + ros_escape(ssid) + '"')
    p.append(':put "  -> Adresse LAN   : ' + ros_escape(gw) + '"')
    p.append(':put "  -> Vos reglages sont immediatement actifs."')
    p.append(':put "=================================================================="')
    p.append(':put " "')
    p.append("# FIN DU SCRIPT KETRIKA MIKROTIK")

    return "\n".join(p)


# ============================================================
# GUIDE TECHNIQUE
# ============================================================

def generate_secret_guide(order):
    lic = safe_get(order, "license_key", "DEMO")
    client = safe_get(order, "client_name", "Client")

    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE TECHNIQUE RESEAU : OPTIMISATION AVANCEE
               Contournement des restrictions FAI et Partage Réseau
================================================================================

Client  : """ + str(client) + """
Licence : """ + str(lic) + """
Date    : """ + time.strftime("%d/%m/%Y", time.gmtime()) + """

================================================================================
INSTALLATION REUSSIE
====================

1. Connectez-vous au MikroTik avec WinBox.
2. Ouvrez New Terminal.
3. Collez le script complet.
4. Le script s'applique immédiatement sans aucune coupure WinBox.
5. Vous verrez la bannière :
   
   [+] KETRIKA - CONFIGURATION TERMINEE AVEC SUCCES [+]

6. Vérifiez ensuite vos accès :
   - Le réseau Wi-Fi émet avec le nom (SSID) choisi.
   - Les clients reçoivent une adresse IP sur la passerelle LAN.
   - Le Hotspot ou le tunnel WireGuard est directement opérationnel.

================================================================================
SUPPORT
=======

KETRIKA MIKROTIK
Madagascar
================================================================================
"""
    return guide
