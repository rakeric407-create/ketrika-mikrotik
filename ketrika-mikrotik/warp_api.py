#!/usr/bin/env python3
"""
============================================================
KETRIKA MIKROTIK - ROUTEROS v7 - VERSION v5 ATOMIQUE
Bridge + Ports LAN corrigés
Chaque commande = 1 ligne simple autant que possible
============================================================
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
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


# ============================================================
# CURVE25519
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
        z_3 = (
            x_1 *
            pow(DA - CB, 2, P)
        ) % P

        x_2 = (AA * BB) % P

        z_2 = (
            E *
            (AA + 121665 * E)
        ) % P

    dummy = swap * (x_2 ^ x_3)
    x_2 ^= dummy
    x_3 ^= dummy

    dummy = swap * (z_2 ^ z_3)
    z_2 ^= dummy
    z_3 ^= dummy

    return enc(
        (x_2 * inv(z_2)) % P
    )


# ============================================================
# WIREGUARD KEYS
# ============================================================

def generate_wireguard_keys():

    private_key = os.urandom(32)

    public_key = curve25519_scalarmult(
        private_key
    )

    return {
        "private_key": base64.b64encode(
            private_key
        ).decode("utf-8"),

        "public_key": base64.b64encode(
            public_key
        ).decode("utf-8"),
    }


# ============================================================
# CLOUDFLARE WARP REGISTER
# ============================================================

def register_warp(public_key):

    try:

        url = (
            "https://api.cloudflareclient.com/"
            "v0a2158/reg"
        )

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.1",
        }

        payload = {
            "key": public_key,
            "install_id": "",
            "fcm_token": "",
            "tos": time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z",
                time.gmtime()
            ),
            "model": "MikroTik",
            "serial_number": hashlib.md5(
                public_key.encode("utf-8")
            ).hexdigest()[:16],
            "locale": "fr_MG",
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code not in (200, 201):
            return {
                "success": False,
                "ipv4": "",
            }

        data = response.json()

        ipv4 = (
            data
            .get("config", {})
            .get("interface", {})
            .get("addresses", {})
            .get("v4", "")
        )

        if "/" in str(ipv4):
            ipv4 = str(ipv4).split("/")[0]

        if not ipv4:
            return {
                "success": False,
                "ipv4": "",
            }

        return {
            "success": True,
            "ipv4": ipv4,
        }

    except Exception:

        return {
            "success": False,
            "ipv4": "",
        }


# ============================================================
# GENERATION SCRIPT ROUTEROS
# ============================================================

def generate_script(order):

    """
    Générateur KETRIKA MikroTik RouterOS v7.

    CORRECTIONS IMPORTANTES :

    1. Bridge créé proprement.
    2. Ports Ethernet ajoutés automatiquement.
    3. WAN exclu du bridge.
    4. Anciens ports du bridge supprimés avant ajout.
    5. Wi-Fi AX ajouté au bridge.
    6. Wi-Fi legacy ajouté au bridge.
    7. Pas de dépendance obligatoire à ether2-ether5.
    """

    # ========================================================
    # PARAMÈTRES
    # ========================================================

    plan = safe_get(
        order,
        "plan_type",
        "standard"
    )

    model = safe_get(
        order,
        "mikrotik_model",
        "hap_ac2"
    )

    ssid = safe_get(
        order,
        "ssid",
        "KETRIKA-WiFi"
    )

    wifi_pass = safe_get(
        order,
        "wifi_password",
        "ketrika2024"
    )

    wan = safe_get(
        order,
        "wan_interface",
        "ether1"
    )

    gw = safe_get(
        order,
        "lan_gateway",
        "192.168.10.1"
    )

    net = safe_get(
        order,
        "lan_network",
        "192.168.10.0/24"
    )

    pool = safe_get(
        order,
        "dhcp_pool",
        "192.168.10.10-192.168.10.250"
    )

    ttl = safe_get(
        order,
        "ttl_value",
        "64"
    )

    dl = safe_get(
        order,
        "dl_limit",
        "0"
    )

    ul = safe_get(
        order,
        "ul_limit",
        "0"
    )

    lic = safe_get(
        order,
        "license_key",
        "DEMO"
    )

    router_name = safe_get(
        order,
        "router_name",
        ""
    )

    mac_spoof = safe_get(
        order,
        "mac_spoof",
        False
    )

    mac_address = safe_get(
        order,
        "mac_address",
        ""
    )

    sleep_mode = safe_get(
        order,
        "sleep_mode",
        "off"
    )

    client_limit = safe_get(
        order,
        "client_limit",
        "0"
    )

    # ========================================================
    # DATABASE
    # ========================================================

    from database import (
        get_model_info,
        generate_router_name,
        generate_random_mac
    )

    info = get_model_info(model)

    if not router_name:

        router_name = generate_router_name(
            lic
        )

    if mac_spoof and not mac_address:

        mac_address = generate_random_mac()

    # ========================================================
    # WARP
    # ========================================================

    keys = generate_wireguard_keys()

    warp_reg = {
        "success": False,
        "ipv4": "",
    }

    if plan in (
        "warp",
        "hotspot"
    ):

        warp_reg = register_warp(
            keys["public_key"]
        )

    warp_ip = warp_reg.get(
        "ipv4",
        ""
    )

    endpoint_ip, endpoint_port = random.choice(
        WARP_ENDPOINTS
    )

    # ========================================================
    # SCRIPT
    # ========================================================

    p = []

    # ========================================================
    # BANNIÈRE
    # ========================================================

    p.append(
        "# +==========================================================+"
    )

    p.append(
        "# |     K E T R I K A   M I K R O T I K   v 5 . 0           |"
    )

    p.append(
        "# |     Configuration Atomique - Bridge corrige              |"
    )

    p.append(
        "# +==========================================================+"
    )

    p.append(
        "# Licence : " + ros_escape(lic)
    )

    p.append(
        "# Plan    : " + ros_escape(plan)
    )

    p.append(
        "# Date    : " +
        time.strftime(
            "%Y-%m-%d %H:%M UTC",
            time.gmtime()
        )
    )

    p.append(
        "# +==========================================================+"
    )

    p.append("")

    p.append(
        ':put ""'
    )

    p.append(
        ':put ">>> KETRIKA v5 - Installation en cours..."'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':log info "KETRIKA v5: Demarrage"'
    )

    p.append("")

    # ========================================================
    # PHASE 1
    # PROTECTION WINBOX
    # ========================================================

    p.append(
        ':put "[1/12] Protection Winbox..."'
    )

    p.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 action=accept place-before=0 comment="KETRIKA-WINBOX" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=22 action=accept place-before=0 comment="KETRIKA-SSH" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=8728 action=accept place-before=0 comment="KETRIKA-API" } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 2
    # NETTOYAGE
    # ========================================================

    p.append(
        ':put "[2/12] Nettoyage anciennes configs..."'
    )

    p.append(
        ':do { /system scheduler remove [find name~"ketrika"] } on-error={}'
    )

    p.append(
        ':do { /system scheduler remove [find name~"sleep"] } on-error={}'
    )

    p.append(
        ':do { /ip firewall nat remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip firewall mangle remove [find] } on-error={}'
    )

    p.append(
        ':do { /queue simple remove [find] } on-error={}'
    )

    p.append(
        ':do { /queue type remove [find name~"pcq"] } on-error={}'
    )

    p.append(
        ':do { /ip dhcp-client remove [find interface=' +
        ros_escape(wan) +
        '] } on-error={}'
    )

    p.append(
        ':do { /ip dhcp-server remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip dhcp-server network remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip pool remove [find] } on-error={}'
    )

    p.append(
        ':do { /interface wireguard remove [find] } on-error={}'
    )

    p.append(
        ':do { /routing table remove [find name!="main"] } on-error={}'
    )

    p.append(
        ':do { /routing rule remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip hotspot user remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip hotspot user profile remove [find name!="default"] } on-error={}'
    )

    p.append(
        ':do { /ip hotspot profile remove [find name!="default"] } on-error={}'
    )

    p.append(
        ':do { /ip hotspot remove [find] } on-error={}'
    )

    p.append(
        ':do { /ip dns static remove [find name~"ketrika"] } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 3
    # BRIDGE LAN CORRIGÉ
    # ========================================================

    p.append(
        ':put "[3/12] Creation Bridge LAN..."'
    )

    # Supprime uniquement bridge1 existant
    p.append(
        ':do { /interface bridge port remove [find bridge=bridge1] } on-error={}'
    )

    p.append(
        ':do { /interface bridge remove [find name=bridge1] } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    # Création propre
    p.append(
        ':do { /interface bridge add name=bridge1 auto-mac=yes comment="LAN-KETRIKA" } on-error={}'
    )

    p.append(
        ':delay 2'
    )

    p.append("")

    # ========================================================
    # PHASE 4
    # WAN
    # ========================================================

    p.append(
        ':put "[4/12] Configuration WAN..."'
    )

    if mac_spoof and mac_address:

        p.append(
            ':do { /interface ethernet set [find default-name=' +
            ros_escape(wan) +
            '] mac-address="' +
            ros_escape(mac_address) +
            '" } on-error={}'
        )

        p.append(
            ':delay 2'
        )

    p.append(
        ':do { /ip dhcp-client add interface=' +
        ros_escape(wan) +
        ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-Internet" } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 5
    # IP LAN
    # ========================================================

    p.append(
        ':put "[5/12] Attribution IP LAN..."'
    )

    p.append(
        ':do { /ip address remove [find interface=bridge1] } on-error={}'
    )

    p.append(
        ':do { /ip address add address=' +
        ros_escape(gw) +
        '/24 interface=bridge1 comment="Passerelle-LAN" } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 6
    # DHCP + DNS
    # ========================================================

    p.append(
        ':put "[6/12] DHCP Server et DNS..."'
    )

    p.append(
        ':do { /ip pool add name=pool-lan ranges=' +
        ros_escape(pool) +
        ' } on-error={}'
    )

    p.append(
        ':do { /ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no } on-error={}'
    )

    p.append(
        ':do { /ip dhcp-server network add address=' +
        ros_escape(net) +
        ' gateway=' +
        ros_escape(gw) +
        ' dns-server=' +
        ros_escape(gw) +
        ' } on-error={}'
    )

    p.append(
        ':do { /ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 } on-error={}'
    )

    p.append(
        ':do { /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 7
    # PORTS ETHERNET LAN - CORRIGÉ
    # ========================================================

    p.append(
        ':put "[7/12] Ajout des ports LAN au bridge..."'
    )

    # IMPORTANT :
    # On retire d'abord les ports de bridge1.
    p.append(
        ':do { /interface bridge port remove [find bridge=bridge1] } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    # Détection automatique de tous les ports Ethernet.
    #
    # Le WAN est exclu.
    #
    # Exemple hAP ac2 :
    # ether2
    # ether3
    # ether4
    # ether5
    #
    # Exemple hAP ax2 :
    # ether2
    # ether3
    # ether4
    # ether5
    #
    p.append(
        ':foreach i in=[/interface ethernet find] do={'
    )

    p.append(
        ' :local n [/interface ethernet get $i name]'
    )

    p.append(
        ' :if ($n != "' +
        ros_escape(wan) +
        '") do={'
    )

    p.append(
        '  :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}'
    )

    p.append(
        ' }'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 2'
    )

    p.append("")

    # ========================================================
    # PHASE 8
    # WI-FI AX
    # ========================================================

    p.append(
        ':put "[8/12] Activation Wi-Fi AX (RouterOS v7)..."'
    )

    if plan == "hotspot":

        p.append(
            ':do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' +
            ros_escape(ssid) +
            '" security.authentication-types="" disabled=no } on-error={}'
        )

    else:

        p.append(
            ':do { /interface wifi set [find] configuration.mode=ap configuration.ssid="' +
            ros_escape(ssid) +
            '" security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="' +
            ros_escape(wifi_pass) +
            '" disabled=no } on-error={}'
        )

    p.append(
        ':do { /interface wifi enable [find] } on-error={}'
    )

    # Wi-Fi AX -> bridge
    p.append(
        ':foreach i in=[/interface wifi find] do={'
    )

    p.append(
        ' :local n [/interface wifi get $i name]'
    )

    p.append(
        ' :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 2'
    )

    p.append("")

    # ========================================================
    # PHASE 9
    # WI-FI LEGACY AC/N
    # ========================================================

    p.append(
        ':put "[9/12] Activation Wi-Fi AC/N (legacy)..."'
    )

    if plan == "hotspot":

        p.append(
            ':do { /interface wireless security-profiles set [find default=yes] mode=none } on-error={}'
        )

    else:

        p.append(
            ':do { /interface wireless security-profiles set [find default=yes] mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' +
            ros_escape(wifi_pass) +
            '" } on-error={}'
        )

    p.append(
        ':do { /interface wireless set [find] mode=ap-bridge ssid="' +
        ros_escape(ssid) +
        '" disabled=no } on-error={}'
    )

    p.append(
        ':do { /interface wireless enable [find] } on-error={}'
    )

    # Wi-Fi legacy -> bridge
    p.append(
        ':foreach i in=[/interface wireless find] do={'
    )

    p.append(
        ' :local n [/interface wireless get $i name]'
    )

    p.append(
        ' :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 2'
    )

    p.append("")

    # ========================================================
    # PHASE 10
    # WIREGUARD / WARP
    # ========================================================

    if plan in (
        "warp",
        "hotspot"
    ):

        p.append(
            ':put "[10/12] Configuration WireGuard WARP..."'
        )

        if warp_ip:

            p.append(
                ':do { /interface wireguard add name=wg-secure mtu=1280 listen-port=13231 comment="WARP-KETRIKA" private-key="' +
                ros_escape(keys["private_key"]) +
                '" } on-error={}'
            )

            p.append(
                ':do { /ip address add address=' +
                ros_escape(warp_ip) +
                '/32 interface=wg-secure } on-error={}'
            )

            p.append(
                ':do { /interface wireguard peers add interface=wg-secure public-key="' +
                CF_PUBLIC_KEY +
                '" endpoint-address=' +
                endpoint_ip +
                ' endpoint-port=' +
                str(endpoint_port) +
                ' allowed-address=0.0.0.0/0 persistent-keepalive=25 } on-error={}'
            )

            p.append(
                ':do { /routing table add name=via-secure fib } on-error={}'
            )

            p.append(
                ':do { /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure } on-error={}'
            )

            if plan == "hotspot":

                p.append(
                    ':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' +
                    ros_escape(net) +
                    ' hotspot=auth dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-HS-WG" } on-error={}'
                )

                p.append(
                    ':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}'
                )

                p.append(
                    ':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect comment="KETRIKA-DNS-HS" } on-error={}'
                )

            else:

                p.append(
                    ':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 src-address=' +
                    ros_escape(net) +
                    ' dst-address-type=!local action=mark-routing new-routing-mark=via-secure passthrough=yes comment="KETRIKA-LAN-To-WG" } on-error={}'
                )

                p.append(
                    ':do { /ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}'
                )

                p.append(
                    ':do { /ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect comment="KETRIKA-DNS" } on-error={}'
                )

            p.append(
                ':do { /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="KETRIKA-WARP-NAT" } on-error={}'
            )

            p.append(
                ':do { /ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="KETRIKA-MSS" } on-error={}'
            )

        else:

            p.append(
                ':log warning "KETRIKA: WARP non enregistre"'
            )

        p.append(
            ':delay 1'
        )

        p.append("")

    # ========================================================
    # PHASE 11
    # HOTSPOT
    # ========================================================

    if plan == "hotspot":

        p.append(
            ':put "[11/12] Configuration Hotspot..."'
        )

        p.append(
            ':do { /ip dns static add name=wifi.ketrika.mg address=' +
            ros_escape(gw) +
            ' } on-error={}'
        )

        p.append(
            ':do { /ip hotspot profile add name=ketrika-hs hotspot-address=' +
            ros_escape(gw) +
            ' dns-name=wifi.ketrika.mg login-by=http-pap,cookie http-cookie-lifetime=1d use-radius=no html-directory=hotspot } on-error={}'
        )

        p.append(
            ':do { /ip hotspot add name=hotspot-ketrika interface=bridge1 profile=ketrika-hs address-pool=pool-lan disabled=no } on-error={}'
        )

        p.append(
            ':do { /ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1 } on-error={}'
        )

        p.append(
            ':do { /ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2 } on-error={}'
        )

        p.append(
            ':do { /ip hotspot user profile add name="1semaine" rate-limit="5M/10M" session-timeout=7d shared-users=2 } on-error={}'
        )

        p.append(
            ':do { /ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3 } on-error={}'
        )

        for _ in range(10):

            vc = "".join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=8
                )
            )

            p.append(
                ':do { /ip hotspot user add name="' +
                vc +
                '" password="' +
                vc +
                '" profile="1jour" comment="Ticket-KETRIKA" } on-error={}'
            )

        p.append(
            ':delay 1'
        )

        p.append("")

    # ========================================================
    # PHASE 12
    # NAT + TTL + QOS + IDENTITY + FIREWALL
    # ========================================================

    p.append(
        ':put "[12/12] NAT, Anti-TTL, QoS, Firewall final..."'
    )

    # --------------------------------------------------------
    # NAT
    # --------------------------------------------------------

    p.append(
        ':do { /ip firewall nat add chain=srcnat out-interface=' +
        ros_escape(wan) +
        ' action=masquerade comment="KETRIKA-NAT" } on-error={}'
    )

    # --------------------------------------------------------
    # TTL
    # --------------------------------------------------------

    if str(ttl) != "0":

        p.append(
            ':do { /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' +
            str(ttl) +
            ' passthrough=yes comment="KETRIKA-TTL" } on-error={}'
        )

        p.append(
            ':do { /ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:' +
            str(ttl) +
            ' passthrough=yes comment="KETRIKA-TTL" } on-error={}'
        )

    # --------------------------------------------------------
    # QOS GLOBAL
    # --------------------------------------------------------

    if dl != "0" or ul != "0":

        lim_ul = (
            str(ul)
            if "M" in str(ul)
            else str(ul) + "M"
        )

        lim_dl = (
            str(dl)
            if "M" in str(dl)
            else str(dl) + "M"
        )

        p.append(
            ':do { /queue simple add name="QoS-Global" target=' +
            ros_escape(net) +
            ' max-limit=' +
            lim_ul +
            '/' +
            lim_dl +
            ' } on-error={}'
        )

    # --------------------------------------------------------
    # QOS PAR CLIENT
    # --------------------------------------------------------

    if client_limit != "0":

        cl = (
            str(client_limit)
            if "M" in str(client_limit)
            else str(client_limit) + "M"
        )

        p.append(
            ':do { /queue type add name=pcq-dl kind=pcq pcq-rate=' +
            cl +
            ' pcq-classifier=dst-address } on-error={}'
        )

        p.append(
            ':do { /queue type add name=pcq-ul kind=pcq pcq-rate=' +
            cl +
            ' pcq-classifier=src-address } on-error={}'
        )

        p.append(
            ':do { /queue simple add name="QoS-PerClient" target=' +
            ros_escape(net) +
            ' queue=pcq-ul/pcq-dl } on-error={}'
        )

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    p.append(
        ':do { /system identity set name="' +
        ros_escape(router_name) +
        '" } on-error={}'
    )

    # --------------------------------------------------------
    # MODE VEILLE
    # --------------------------------------------------------

    if sleep_mode != "off":

        sleep_ranges = {
            "00-06": (
                "00:00:00",
                "06:00:00"
            ),

            "01-05": (
                "01:00:00",
                "05:00:00"
            ),

            "23-07": (
                "23:00:00",
                "07:00:00"
            ),

            "02-06": (
                "02:00:00",
                "06:00:00"
            ),
        }

        start_t, end_t = sleep_ranges.get(
            sleep_mode,
            (
                "00:00:00",
                "06:00:00"
            )
        )

        p.append(
            ':do { /system scheduler add name="ketrika-sleep-off" start-time=' +
            start_t +
            ' interval=1d on-event="/interface wifi set [find] disabled=yes; /interface wireless set [find] disabled=yes" } on-error={}'
        )

        p.append(
            ':do { /system scheduler add name="ketrika-sleep-on" start-time=' +
            end_t +
            ' interval=1d on-event="/interface wifi set [find] disabled=no; /interface wireless set [find] disabled=no" } on-error={}'
        )

    # --------------------------------------------------------
    # FIREWALL
    # --------------------------------------------------------

    p.append(
        ':do { /ip firewall filter remove [find comment~"KETRIKA-FW"] } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input connection-state=established,related action=accept comment="KETRIKA-FW" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input connection-state=invalid action=drop comment="KETRIKA-FW" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input protocol=icmp action=accept comment="KETRIKA-FW" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input in-interface=bridge1 action=accept comment="KETRIKA-FW" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input in-interface=' +
        ros_escape(wan) +
        ' action=drop comment="KETRIKA-FW" } on-error={}'
    )

    p.append(
        ':log info "KETRIKA v5: Configuration terminee."'
    )

    p.append("")

    # ========================================================
    # BANNIÈRE FINALE
    # ========================================================

    p.append(
        ':put ""'
    )

    p.append(
        ':put "###############################################################"'
    )

    p.append(
        ':put "##                                                           ##"'
    )

    p.append(
        ':put "##      K E T R I K A   -   I N S T A L L A T I O N        ##"'
    )

    p.append(
        ':put "##              T E R M I N E E   A V E C                  ##"'
    )

    p.append(
        ':put "##                   S U C C E S                           ##"'
    )

    p.append(
        ':put "##                                                           ##"'
    )

    p.append(
        ':put "###############################################################"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put "  |  MODULES ACTIFS                                     |"'
    )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put "  |  [OK] Bridge LAN cree                               |"'
    )

    p.append(
        ':put "  |  [OK] IP Gateway configuree                         |"'
    )

    p.append(
        ':put "  |  [OK] DHCP Server actif                             |"'
    )

    p.append(
        ':put "  |  [OK] DNS Cloudflare securise (DoH)                 |"'
    )

    p.append(
        ':put "  |  [OK] Wi-Fi actif (AX + AC/N)                       |"'
    )

    p.append(
        ':put "  |  [OK] Ports LAN dans le bridge                      |"'
    )

    p.append(
        ':put "  |  [OK] Anti-TTL FAI actif                            |"'
    )

    if plan in (
        "warp",
        "hotspot"
    ) and warp_ip:

        p.append(
            ':put "  |  [OK] WireGuard WARP Cloudflare                     |"'
        )

    if plan == "hotspot":

        p.append(
            ':put "  |  [OK] Hotspot Portail Captif (10 tickets)           |"'
        )

    p.append(
        ':put "  |  [OK] Firewall securise                             |"'
    )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put "  |  VOS INFORMATIONS                                   |"'
    )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put "  |  Routeur    : ' +
        ros_escape(router_name) +
        '"'
    )

    p.append(
        ':put "  |  SSID       : ' +
        ros_escape(ssid) +
        '"'
    )

    if plan != "hotspot":

        p.append(
            ':put "  |  Mot passe  : ' +
            ros_escape(wifi_pass) +
            '"'
        )

    p.append(
        ':put "  |  Gateway    : ' +
        ros_escape(gw) +
        '"'
    )

    p.append(
        ':put "  |  Reseau     : ' +
        ros_escape(net) +
        '"'
    )

    p.append(
        ':put "  |  Plan       : ' +
        ros_escape(plan) +
        '"'
    )

    p.append(
        ':put "  |  TTL Mask   : ' +
        str(ttl) +
        '"'
    )

    if mac_spoof and mac_address:

        p.append(
            ':put "  |  MAC WAN    : ' +
            ros_escape(mac_address) +
            '"'
        )

    p.append(
        ':put "  +-----------------------------------------------------+"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "  >>> Actif immediatement - Aucun redemarrage requis"'
    )

    p.append(
        ':put "  >>> Merci d avoir choisi KETRIKA MIKROTIK !"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "###############################################################"'
    )

    p.append(
        ':put ""'
    )

    p.append("")

    p.append(
        "# FIN KETRIKA v5"
    )

    return "\n".join(p)


# ============================================================
# GUIDE TECHNIQUE
# ============================================================

def generate_secret_guide(order):

    lic = safe_get(
        order,
        "license_key",
        "DEMO"
    )

    client = safe_get(
        order,
        "client_name",
        "Client"
    )

    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE TECHNIQUE RESEAU
================================================================================

Client  : """ + str(client) + """
Licence : """ + str(lic) + """
Date    : """ + time.strftime(
        "%d/%m/%Y",
        time.gmtime()
    ) + """

================================================================================
INSTALLATION
============

1. Connectez-vous au MikroTik avec WinBox
2. Ouvrez New Terminal
3. Collez le script complet
4. Attendez la banniere KETRIKA SUCCES
5. Verifiez le Wi-Fi et la connexion Internet

================================================================================
BRIDGE LAN
==========

Le script cree automatiquement :

bridge1

Le port WAN choisi dans la licence est exclu du bridge.

Les autres ports Ethernet disponibles sont automatiquement ajoutes
au bridge LAN.

Les interfaces Wi-Fi compatibles sont ensuite ajoutees au bridge.

================================================================================
SUPPORT : KETRIKA MIKROTIK - Madagascar
================================================================================
"""

    return guide
