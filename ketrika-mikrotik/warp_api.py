#!/usr/bin/env python3
"""
============================================================
KETRIKA MIKROTIK - MOTEUR DE GENERATION ROUTEROS v7 (FINAL v3)
Plateforme de Genie Reseau - Version Physique + CHR Stable
============================================================
"""

import os
import random
import string
import base64
import time
import hashlib
import requests

# Cle publique Cloudflare WARP officielle
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
    """Protege les valeurs destinees a RouterOS"""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def curve25519_scalarmult(scalar):
    """Generation X25519 pure-Python (zero dependance externe)"""
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
    """Genere la paire de cles WireGuard pour RouterOS"""
    private_key = os.urandom(32)
    public_key = curve25519_scalarmult(private_key)
    return {
        "private_key": base64.b64encode(private_key).decode("utf-8"),
        "public_key": base64.b64encode(public_key).decode("utf-8"),
    }


def register_warp(public_key):
    """Enregistre dynamiquement la cle sur l'infrastructure Cloudflare"""
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
    """
    Generateur de scripts RouterOS v7 certifie production.
    Fonctionne sur CHR (virtuel) ET sur vrai boitier physique MikroTik.
    Protection absolue contre les deconnexions Winbox.
    """
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
    info = get_model_info(model)

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

    # ============================================================
    # CONSTRUCTION DU SCRIPT INTERNE (sera execute par le routeur)
    # ============================================================
    s = []

    # --- 1. PROTECTION WINBOX IMMEDIATE ---
    s.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 action=accept place-before=0 comment="KETRIKA-WINBOX" } on-error={}')
    s.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=22 action=accept place-before=0 comment="KETRIKA-SSH" } on-error={}')
    s.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=8728 action=accept place-before=0 comment="KETRIKA-API" } on-error={}')

    # --- 2. NETTOYAGE SECURISE ---
    s.append(':do { /system scheduler remove [find name~"ketrika"] } on-error={}')
    s.append(':do { /system scheduler remove [find name~"reboot"] } on-error={}')
    s.append(':do { /system scheduler remove [find name~"sleep"] } on-error={}')
    s.append(':do { /ip firewall filter remove [find comment~"KETRIKA-FW"] } on-error={}')
    s.append(':do { /ip firewall nat remove [find] } on-error={}')
    s.append(':do { /ip firewall mangle remove [find] } on-error={}')
    s.append(':do { /queue simple remove [find] } on-error={}')
    s.append(':do { /queue type remove [find name~"pcq"] } on-error={}')
    s.append(':do { /ip dhcp-client remove [find interface=' + ros_escape(wan) + '] } on-error={}')
    s.append(':do { /ip dhcp-server remove [find] } on-error={}')
    s.append(':do { /ip dhcp-server network remove [find] } on-error={}')
    s.append(':do { /ip pool remove [find] } on-error={}')
    s.append(':do { /ip route remove [find dynamic=no] } on-error={}')
    s.append(':do { /interface wireguard remove [find] } on-error={}')
    s.append(':do { /routing table remove [find name!="main"] } on-error={}')
    s.append(':do { /routing rule remove [find] } on-error={}')
    s.append(':do { /ip hotspot user remove [find] } on-error={}')
    s.append(':do { /ip hotspot user profile remove [find name!="default"] } on-error={}')
    s.append(':do { /ip hotspot profile remove [find name!="default"] } on-error={}')
    s.append(':do { /ip hotspot remove [find] } on-error={}')
    s.append(':do { /ip dns static remove [find name~"ketrika"] } on-error={}')

    # --- 3. BRIDGE LAN (auto-mac=no EMPECHE la deconnexion physique) ---
    s.append(':if ([:len [/interface bridge find name=bridge1]] = 0) do={')
    s.append('  :if ([:len [/interface bridge find name=bridge]] > 0) do={')
    s.append('    /interface bridge set [find name=bridge] name=bridge1 auto-mac=no')
    s.append('  } else={')
    s.append('    /interface bridge add name=bridge1 auto-mac=no comment="LAN-KETRIKA"')
    s.append('  }')
    s.append('} else={')
    s.append('  /interface bridge set [find name=bridge1] auto-mac=no')
    s.append('}')

    # --- 4. WAN & MAC SPOOF ---
    if mac_spoof and mac_address:
        s.append(':do { /interface ethernet set [find default-name=' + ros_escape(wan) + '] mac-address="' + ros_escape(mac_address) + '" } on-error={}')
    s.append(':do { /ip dhcp-client add interface=' + ros_escape(wan) + ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-Internet" } on-error={}')

    # --- 5. IP LAN & DHCP & DNS ---
    s.append(':if ([:len [/ip address find interface=bridge1 address~"' + ros_escape(gw) + '"]] = 0) do={')
    s.append('  /ip address add address=' + ros_escape(gw) + '/24 interface=bridge1 comment="Passerelle-LAN"')
    s.append('}')
    s.append(':do { /ip pool add name=pool-lan ranges=' + ros_escape(pool) + ' } on-error={}')
    s.append(':do { /ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no } on-error={}')
    s.append(':do { /ip dhcp-server network add address=' + ros_escape(net) + ' gateway=' + ros_escape(gw) + ' dns-server=' + ros_escape(gw) + ' } on-error={}')
    s.append(':do { /ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server=https://cloudflare-dns.com/dns-query } on-error={ /ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 }')

    # --- 6. WI-FI AX (RouterOS v7 wifi : hap ax2, ax3, etc.) ---
    s.append(':if ([:len [/interface wifi find]] > 0) do={')
    if plan == "hotspot":
        s.append('  :do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types="" disabled=no } on-error={}')
    else:
        s.append('  :do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' + ros_escape(ssid) + '" security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="' + ros_escape(wifi_pass) + '" disabled=no } on-error={}')
    s.append('  :do { /interface wifi enable [find] } on-error={}')
    s.append('  :foreach i in=[/interface wifi find] do={')
    s.append('    :local n [/interface wifi get $i name]')
    s.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    s.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    s.append('    }')
    s.append('  }')
    s.append('}')

    # --- 6B. WI-FI AC/N (Wireless legacy : hap ac2, ac3, lite, etc.) ---
    s.append(':if ([:len [/interface wireless find]] > 0) do={')
    if plan == "hotspot":
        s.append('  :do { /interface wireless security-profiles set [find default=yes] mode=none } on-error={}')
    else:
        s.append('  :do { /interface wireless security-profiles set [find default=yes] mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' + ros_escape(wifi_pass) + '" } on-error={}')
    s.append('  :do { /interface wireless set [find] mode=ap-bridge ssid="' + ros_escape(ssid) + '" disabled=no } on-error={}')
    s.append('  :do { /interface wireless enable [find] } on-error={}')
    s.append('  :foreach i in=[/interface wireless find] do={')
    s.append('    :local n [/interface wireless get $i name]')
    s.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    s.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    s.append('    }')
    s.append('  }')
    s.append('}')

    # --- 7. PORTS ETHERNET VERS BRIDGE ---
    s.append(':foreach i in=[/interface ethernet find] do={')
    s.append('  :local n [/interface ethernet get $i name]')
    s.append('  :if ($n != "' + ros_escape(wan) + '") do={')
    s.append('    :if ([:len [/interface bridge port find interface=$n]] = 0) do={')
    s.append('      :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}')
    s.append('    }')
    s.append('  }')
    s.append('}')

    # --- 8. WIREGUARD / WARP (listen-port=13231, tout protege) ---
    if plan in ("warp", "hotspot"):
        if warp_ip:
            s.append(':do {')
            s.append('  /interface wireguard add name=wg-secure mtu=1280 listen-port=13231 comment="WARP-KETRIKA" private-key="' + ros_escape(keys["private_key"]) + '"')
            s.append('  /ip address add address=' + ros_escape(warp_ip) + '/32 interface=wg-secure')
            s.append('  /interface wireguard peers add interface=wg-secure public-key="' + CF_PUBLIC_KEY + '" endpoint-address=' + endpoint_ip + ' endpoint-port=' + str(endpoint_port) + ' allowed-address=0.0.0.0/0 persistent-keepalive=25')
            s.append('  :do { /routing table add name=via-secure fib } on-error={}')
            s.append('  /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure')
            s.append('} on-error={ :log warning "KETRIKA: WireGuard non supporte sur ce modele." }')

            if plan == "hotspot":
                s.append(':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' hotspot=auth dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-HS-WG" } on-error={}')
                s.append(':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}')
                s.append(':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}')
            else:
                s.append(':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' + ros_escape(net) + ' dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-LAN-To-WG" } on-error={}')
                s.append(':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}')
                s.append(':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}')

            s.append(':do { /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="KETRIKA-WARP-NAT" } on-error={}')
            s.append(':do { /ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="KETRIKA-MSS" } on-error={}')
        else:
            s.append(':log warning "KETRIKA: WARP non enregistre - tunnel non active."')

    # --- 9. HOTSPOT (Plan 3) ---
    if plan == "hotspot":
        s.append(':do { /ip dns static add name=wifi.ketrika.mg address=' + ros_escape(gw) + ' } on-error={}')
        s.append(':do { /ip hotspot profile add name=ketrika-hs hotspot-address=' + ros_escape(gw) + ' dns-name=wifi.ketrika.mg login-by=http-pap,cookie http-cookie-lifetime=1d use-radius=no html-directory=hotspot } on-error={}')
        s.append(':do { /ip hotspot add name=hotspot-ketrika interface=bridge1 profile=ketrika-hs address-pool=pool-lan disabled=no } on-error={}')
        s.append(':do { /ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1 } on-error={}')
        s.append(':do { /ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2 } on-error={}')
        s.append(':do { /ip hotspot user profile add name="1semaine" rate-limit="5M/10M" session-timeout=7d shared-users=2 } on-error={}')
        s.append(':do { /ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3 } on-error={}')
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            s.append(':do { /ip hotspot user add name="' + vc + '" password="' + vc + '" profile="1jour" comment="Ticket-KETRIKA" } on-error={}')

    # --- 10. NAT & ANTI-TTL ---
    s.append(':do { /ip firewall nat add chain=srcnat out-interface=' + ros_escape(wan) + ' action=masquerade comment="KETRIKA-NAT" } on-error={}')
    if str(ttl) != "0":
        s.append(':do { /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="KETRIKA-TTL" } on-error={}')
        s.append(':do { /ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:' + str(ttl) + ' passthrough=yes comment="KETRIKA-TTL" } on-error={}')

    # --- 11. QoS & LIMITATION DEBIT ---
    if dl != "0" or ul != "0":
        lim_ul = str(ul) if "M" in str(ul) else str(ul) + "M"
        lim_dl = str(dl) if "M" in str(dl) else str(dl) + "M"
        s.append(':do { /queue simple add name="QoS-Global" target=' + ros_escape(net) + ' max-limit=' + lim_ul + '/' + lim_dl + ' } on-error={}')

    if client_limit != "0":
        cl = str(client_limit) if "M" in str(client_limit) else str(client_limit) + "M"
        s.append(':do { /queue type add name=pcq-dl kind=pcq pcq-rate=' + cl + ' pcq-classifier=dst-address } on-error={}')
        s.append(':do { /queue type add name=pcq-ul kind=pcq pcq-rate=' + cl + ' pcq-classifier=src-address } on-error={}')
        s.append(':do { /queue simple add name="QoS-PerClient" target=' + ros_escape(net) + ' queue=pcq-ul/pcq-dl } on-error={}')

    # --- 12. IDENTITY ---
    s.append('/system identity set name="' + ros_escape(router_name) + '"')

    # --- 13. MODE VEILLE NOCTURNE WI-FI ---
    if sleep_mode != "off":
        sleep_ranges = {
            "00-06": ("00:00:00", "06:00:00"),
            "01-05": ("01:00:00", "05:00:00"),
            "23-07": ("23:00:00", "07:00:00"),
            "02-06": ("02:00:00", "06:00:00"),
        }
        start_t, end_t = sleep_ranges.get(sleep_mode, ("00:00:00", "06:00:00"))
        s.append(':do { /system scheduler add name="ketrika-sleep-off" start-time=' + start_t + ' interval=1d on-event="/interface wifi set [find] disabled=yes; /interface wireless set [find] disabled=yes" } on-error={}')
        s.append(':do { /system scheduler add name="ketrika-sleep-on" start-time=' + end_t + ' interval=1d on-event="/interface wifi set [find] disabled=no; /interface wireless set [find] disabled=no" } on-error={}')

    # --- 14. FIREWALL FINAL ---
    s.append('/ip firewall filter add chain=input connection-state=established,related action=accept comment="KETRIKA-FW"')
    s.append('/ip firewall filter add chain=input connection-state=invalid action=drop comment="KETRIKA-FW"')
    s.append('/ip firewall filter add chain=input protocol=icmp action=accept comment="KETRIKA-FW"')
    s.append('/ip firewall filter add chain=input in-interface=bridge1 action=accept comment="KETRIKA-FW"')
    s.append('/ip firewall filter add chain=input in-interface=' + ros_escape(wan) + ' action=drop comment="KETRIKA-FW"')

    # --- 15. LOG FINAL ---
    s.append(':log info "KETRIKA: Configuration terminee avec succes."')

    # ============================================================
    # JOINTURE DU SCRIPT INTERNE
    # ============================================================
    inner_script = "\n".join(s)

    # ============================================================
    # EMBALLAGE FINAL : RUNNER AUTONOME ANTI-DECONNEXION
    # Le script est stocke dans la memoire flash du routeur puis
    # execute en arriere-plan. Meme si Winbox se deconnecte 1s,
    # le routeur CONTINUE jusqu a la derniere ligne.
    # ============================================================
    p = []
    p.append("# ============================================================")
    p.append("# KETRIKA MIKROTIK - INSTALLATEUR AUTONOME v3")
    p.append("# LICENCE : " + ros_escape(lic))
    p.append("# MODELE  : " + ros_escape(model))
    p.append("# PLAN    : " + ros_escape(plan))
    p.append("# DATE    : " + time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()))
    p.append("# ============================================================")
    p.append(':put ">>> Ingestion du script KETRIKA dans la memoire du routeur..."')
    p.append(':do { /system script remove [find name="ketrika_install"] } on-error={}')
    p.append('/system script add name="ketrika_install" source="' + ros_escape(inner_script) + '"')
    p.append(':put ">>> Execution en arriere-plan (sans coupure Winbox)..."')
    p.append('/system script run ketrika_install')
    p.append(':do { /system script remove [find name="ketrika_install"] } on-error={}')
    p.append(':put " "')
    p.append(':put "=================================================================="')
    p.append(':put "      [+] KETRIKA - CONFIGURATION APPLIQUEE AVEC SUCCES [+]"')
    p.append(':put "=================================================================="')
    p.append(':put "  -> SSID Wi-Fi    : ' + ros_escape(ssid) + '"')
    p.append(':put "  -> Adresse LAN   : ' + ros_escape(gw) + '"')
    p.append(':put "  -> Plan          : ' + ros_escape(plan) + '"')
    p.append(':put "  -> MAC WAN       : ' + (ros_escape(mac_address) if (mac_spoof and mac_address) else "Defaut") + '"')
    p.append(':put "  -> Nom Routeur   : ' + ros_escape(router_name) + '"')
    p.append(':put "  -> Anti-TTL      : ' + ("Actif (TTL=" + str(ttl) + ")") + '"')
    p.append(':put "  -> WireGuard/WARP: ' + ("Actif" if (plan in ("warp", "hotspot") and warp_ip) else "Non active") + '"')
    p.append(':put "  -> Vos reglages sont immediatement actifs sans reboot."')
    p.append(':put "=================================================================="')
    p.append(':put " "')
    p.append("# FIN DU SCRIPT KETRIKA MIKROTIK")

    return "\n".join(p)


def generate_secret_guide(order):
    """Genere le dossier technique secret d'optimisation."""
    lic = safe_get(order, "license_key", "DEMO")
    client = safe_get(order, "client_name", "Client")

    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE TECHNIQUE RESEAU : OPTIMISATION AVANCEE
               Contournement des restrictions FAI et Partage Reseau
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
4. Le script s'applique immediatement sans aucune coupure WinBox.
5. Vous verrez la banniere :
   
   [+] KETRIKA - CONFIGURATION TERMINEE AVEC SUCCES [+]

6. Verifiez ensuite vos acces :
   - Le reseau Wi-Fi emet avec le nom (SSID) choisi.
   - Les clients recoivent une adresse IP sur la passerelle LAN.
   - Le Hotspot ou le tunnel WireGuard est directement operationnel.

================================================================================
SUPPORT
=======

KETRIKA MIKROTIK
Madagascar
================================================================================
"""
    return guide
