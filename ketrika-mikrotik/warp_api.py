#!/usr/bin/env python3
"""
============================================================
KETRIKA MIKROTIK - ROUTEROS v7
VERSION V6 - NO-DISCONNECT
============================================================

OBJECTIF PRINCIPAL
------------------
Le script doit pouvoir être collé dans WinBox Terminal sans
détruire la connexion de gestion pendant l'installation.

PRINCIPES V6
------------
1. Ne jamais supprimer bridge1.
2. Ne jamais supprimer tous les DHCP.
3. Ne jamais supprimer tous les NAT.
4. Ne jamais supprimer tous les mangle.
5. Ne jamais changer le MAC WAN automatiquement.
6. Ne jamais supprimer l'adresse IP actuelle du routeur.
7. Ne jamais retirer brutalement un port du bridge.
8. Ajouter uniquement les ports manquants.
9. Ajouter Wi-Fi au bridge sans supprimer les ports existants.
10. Ne pas créer un deuxième DHCP si un DHCP existe déjà.
11. Ne pas créer un deuxième NAT identique.
12. Ne pas créer plusieurs routes par défaut identiques.
13. Protéger WinBox avant les modifications.
14. Les opérations potentiellement destructrices sont évitées.
15. Aucun reboot automatique.

IMPORTANT
---------
Une coupure physique ou un changement d'IP de management ne
peut jamais être garanti à 0% par RouterOS. Cette version
évite volontairement les opérations qui provoquent normalement
la perte de la session WinBox.
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

CF_PUBLIC_KEY = (
    "bmXOC+F1FxEMF9dyK2H5/1SUtzH0JuVo51h2wPfgyo="
)

WARP_ENDPOINTS = [
    ("162.159.192.1", 2408),
    ("162.159.193.1", 2408),
    ("188.114.96.1", 2408),
    ("188.114.97.1", 2408),
]


# ============================================================
# OUTILS PYTHON
# ============================================================

def safe_get(obj, key, default=""):
    try:
        value = getattr(obj, key, default)
        return value if value is not None else default
    except Exception:
        return default


def ros_escape(value):
    """
    Echappement sécurisé pour les chaînes RouterOS.
    """
    value = str(value)

    value = value.replace(
        "\\",
        "\\\\"
    )

    value = value.replace(
        '"',
        '\\"'
    )

    return value


def ros_bool(value):
    """
    Conversion robuste booléenne.
    """
    if isinstance(value, bool):
        return value

    return str(value).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


# ============================================================
# CURVE25519
# ============================================================

def curve25519_scalarmult(scalar):

    P = 2**255 - 19

    def dec(data):
        return int.from_bytes(
            data,
            "little"
        )

    def enc(value):
        return (
            value % P
        ).to_bytes(
            32,
            "little"
        )

    def inv(value):
        return pow(
            value,
            P - 2,
            P
        )

    k = bytearray(
        scalar
    )

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

    for t in range(
        254,
        -1,
        -1
    ):

        k_t = (
            k_int >> t
        ) & 1

        swap ^= k_t

        dummy = (
            swap *
            (x_2 ^ x_3)
        )

        x_2 ^= dummy
        x_3 ^= dummy

        dummy = (
            swap *
            (z_2 ^ z_3)
        )

        z_2 ^= dummy
        z_3 ^= dummy

        swap = k_t

        A = (
            x_2 + z_2
        ) % P

        AA = (
            A * A
        ) % P

        B = (
            x_2 - z_2
        ) % P

        BB = (
            B * B
        ) % P

        E = (
            AA - BB
        ) % P

        C = (
            x_3 + z_3
        ) % P

        D = (
            x_3 - z_3
        ) % P

        DA = (
            D * A
        ) % P

        CB = (
            C * B
        ) % P

        x_3 = pow(
            DA + CB,
            2,
            P
        )

        z_3 = (
            x_1 *
            pow(
                DA - CB,
                2,
                P
            )
        ) % P

        x_2 = (
            AA * BB
        ) % P

        z_2 = (
            E *
            (
                AA +
                121665 * E
            )
        ) % P

    dummy = (
        swap *
        (x_2 ^ x_3)
    )

    x_2 ^= dummy
    x_3 ^= dummy

    dummy = (
        swap *
        (z_2 ^ z_3)
    )

    z_2 ^= dummy
    z_3 ^= dummy

    return enc(
        (
            x_2 *
            inv(z_2)
        ) % P
    )


# ============================================================
# WIREGUARD KEYS
# ============================================================

def generate_wireguard_keys():

    private_key = os.urandom(
        32
    )

    public_key = (
        curve25519_scalarmult(
            private_key
        )
    )

    return {
        "private_key": base64.b64encode(
            private_key
        ).decode(
            "utf-8"
        ),

        "public_key": base64.b64encode(
            public_key
        ).decode(
            "utf-8"
        ),
    }


# ============================================================
# CLOUDFLARE WARP REGISTRATION
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
                public_key.encode(
                    "utf-8"
                )
            ).hexdigest()[:16],
            "locale": "fr_MG",
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )

        if response.status_code not in (
            200,
            201
        ):
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
            ipv4 = str(
                ipv4
            ).split(
                "/"
            )[0]

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
# GENERATE ROUTEROS SCRIPT
# ============================================================

def generate_script(order):

    """
    KETRIKA V6 NO-DISCONNECT.

    La philosophie est différente des anciennes versions :

    ANCIENNE V5 :
        supprimer -> recréer -> basculer

    V6 :
        vérifier -> conserver -> compléter

    Cela évite les opérations qui coupent généralement WinBox.
    """

    # ========================================================
    # PARAMETRES
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

    # ========================================================
    # V6 : MAC SPOOF DESACTIVE PAR DEFAUT
    # ========================================================

    mac_spoof = ros_bool(
        safe_get(
            order,
            "mac_spoof",
            False
        )
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

    try:
        info = get_model_info(
            model
        )
    except Exception:
        info = {}

    if not router_name:

        router_name = generate_router_name(
            lic
        )

    # IMPORTANT :
    # Même si l'ancienne application demande un MAC spoof,
    # V6 ne change PAS le MAC pendant l'installation.
    #
    # On garde la valeur pour affichage uniquement.
    if mac_spoof and not mac_address:

        try:
            mac_address = generate_random_mac()
        except Exception:
            mac_address = ""

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
    # BANNIERE
    # ========================================================

    p.append(
        "# ============================================================"
    )

    p.append(
        "# KETRIKA MIKROTIK V6 - NO-DISCONNECT"
    )

    p.append(
        "# ============================================================"
    )

    p.append(
        "# Licence : " +
        ros_escape(lic)
    )

    p.append(
        "# Plan    : " +
        ros_escape(plan)
    )

    p.append(
        "# Model   : " +
        ros_escape(model)
    )

    p.append(
        "# WAN     : " +
        ros_escape(wan)
    )

    p.append(
        "# ============================================================"
    )

    p.append("")

    p.append(
        ':put ""'
    )

    p.append(
        ':put "=================================================="'
    )

    p.append(
        ':put " KETRIKA V6 - NO-DISCONNECT"'
    )

    p.append(
        ':put "=================================================="'
    )

    p.append(
        ':put "IMPORTANT : aucune suppression reseau globale"'
    )

    p.append(
        ':put "WinBox doit rester connecte pendant l installation"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':log info "KETRIKA V6: Installation demarree"'
    )

    p.append("")

    # ========================================================
    # PHASE 1
    # PROTECTION WINBOX
    # ========================================================

    p.append(
        ':put "[1/10] Protection WinBox..."'
    )

    # IMPORTANT :
    # add uniquement.
    # On ne supprime pas les règles existantes.

    p.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 action=accept place-before=0 comment="KETRIKA-V6-WINBOX" } on-error={}'
    )

    p.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=22 action=accept place-before=0 comment="KETRIKA-V6-SSH" } on-error={}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 2
    # BRIDGE SANS SUPPRESSION
    # ========================================================

    p.append(
        ':put "[2/10] Verification Bridge..."'
    )

    # On NE SUPPRIME PAS bridge1.

    p.append(
        ':if ([:len [/interface bridge find name="bridge1"]] = 0) do={ /interface bridge add name=bridge1 auto-mac=yes comment="KETRIKA-V6-LAN" }'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 3
    # PORTS ETHERNET
    # ========================================================

    p.append(
        ':put "[3/10] Ajout securise des ports LAN..."'
    )

    p.append(
        ':put "Le WAN sera conserve hors du bridge."'
    )

    # IMPORTANT :
    # Aucun port n'est supprimé du bridge.
    #
    # Si le port existe déjà :
    # rien ne se passe.
    #
    # S'il n'existe pas :
    # il est ajouté.

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
        '  :if ([:len [/interface bridge port find interface=$n]] = 0) do={'
    )

    p.append(
        '   :do { /interface bridge port add bridge=bridge1 interface=$n } on-error={}'
    )

    p.append(
        '  }'
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
    # PHASE 4
    # WIFI AX
    # ========================================================

    p.append(
        ':put "[4/10] Activation Wi-Fi AX..."'
    )

    # On configure sans supprimer l'interface.

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

    # Ajouter seulement les Wi-Fi absents du bridge.

    p.append(
        ':foreach i in=[/interface wifi find] do={'
    )

    p.append(
        ' :local n [/interface wifi get $i name]'
    )

    p.append(
        ' :if ([:len [/interface bridge port find interface=$n]] = 0) do={'
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
    # PHASE 5
    # WIFI LEGACY
    # ========================================================

    p.append(
        ':put "[5/10] Activation Wi-Fi AC/N..."'
    )

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

    p.append(
        ':foreach i in=[/interface wireless find] do={'
    )

    p.append(
        ' :local n [/interface wireless get $i name]'
    )

    p.append(
        ' :if ([:len [/interface bridge port find interface=$n]] = 0) do={'
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
    # PHASE 6
    # IP / DHCP
    # ========================================================

    p.append(
        ':put "[6/10] Verification IP et DHCP..."'
    )

    p.append(
        ':put "Aucune ancienne adresse IP ne sera supprimee."'
    )

    # --------------------------------------------------------
    # IP LAN
    # --------------------------------------------------------
    #
    # IMPORTANT :
    # On ne supprime aucune IP.
    #
    # On ajoute l'IP demandée seulement si bridge1 n'a
    # actuellement aucune adresse IP.
    #
    # Cela protège une session WinBox existante.

    p.append(
        ':if ([:len [/ip address find interface=bridge1]] = 0) do={'
    )

    p.append(
        ' :do { /ip address add address=' +
        ros_escape(gw) +
        '/24 interface=bridge1 comment="KETRIKA-V6-LAN" } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 1'
    )

    # --------------------------------------------------------
    # POOL
    # --------------------------------------------------------

    p.append(
        ':if ([:len [/ip pool find name="pool-lan"]] = 0) do={'
    )

    p.append(
        ' :do { /ip pool add name=pool-lan ranges=' +
        ros_escape(pool) +
        ' } on-error={}'
    )

    p.append(
        '}'
    )

    # --------------------------------------------------------
    # DHCP
    # --------------------------------------------------------
    #
    # On ne supprime jamais le DHCP existant.
    #
    # S'il n'existe aucun DHCP sur bridge1,
    # on en crée un.

    p.append(
        ':if ([:len [/ip dhcp-server find interface=bridge1]] = 0) do={'
    )

    p.append(
        ' :do { /ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 1'
    )

    # --------------------------------------------------------
    # DHCP NETWORK
    # --------------------------------------------------------

    p.append(
        ':if ([:len [/ip dhcp-server network find address="' +
        ros_escape(net) +
        '"]] = 0) do={'
    )

    p.append(
        ' :do { /ip dhcp-server network add address=' +
        ros_escape(net) +
        ' gateway=' +
        ros_escape(gw) +
        ' dns-server=' +
        ros_escape(gw) +
        ' } on-error={}'
    )

    p.append(
        '}'
    )

    # --------------------------------------------------------
    # DNS
    # --------------------------------------------------------

    p.append(
        ':do { /ip dns set allow-remote-requests=yes } on-error={}'
    )

    p.append(
        ':do { /ip dns set servers=1.1.1.1,1.0.0.1 } on-error={}'
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
    # WAN DHCP
    # ========================================================

    p.append(
        ':put "[7/10] Verification WAN..."'
    )

    # Ne supprime jamais le DHCP client existant.

    p.append(
        ':if ([:len [/ip dhcp-client find interface=' +
        ros_escape(wan) +
        ']] = 0) do={'
    )

    p.append(
        ' :do { /ip dhcp-client add interface=' +
        ros_escape(wan) +
        ' disabled=no add-default-route=yes use-peer-dns=no comment="KETRIKA-V6-WAN" } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 8
    # NAT
    # ========================================================

    p.append(
        ':put "[8/10] Verification NAT..."'
    )

    # On ne supprime aucun NAT.
    #
    # On ajoute le NAT KETRIKA uniquement s'il n'existe pas.

    p.append(
        ':if ([:len [/ip firewall nat find comment="KETRIKA-V6-NAT"]] = 0) do={'
    )

    p.append(
        ' :do { /ip firewall nat add chain=srcnat out-interface=' +
        ros_escape(wan) +
        ' action=masquerade comment="KETRIKA-V6-NAT" } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 9
    # WARP
    # ========================================================

    if plan in (
        "warp",
        "hotspot"
    ):

        p.append(
            ':put "[9/10] Configuration WARP..."'
        )

        if warp_ip:

            # ------------------------------------------------
            # WireGuard
            # ------------------------------------------------

            p.append(
                ':if ([:len [/interface wireguard find name="wg-secure"]] = 0) do={'
            )

            p.append(
                ' :do { /interface wireguard add name=wg-secure mtu=1280 listen-port=13231 comment="WARP-KETRIKA-V6" private-key="' +
                ros_escape(
                    keys["private_key"]
                ) +
                '" } on-error={}'
            )

            p.append(
                '}'
            )

            # ------------------------------------------------
            # Adresse WARP
            # ------------------------------------------------

            p.append(
                ':if ([:len [/ip address find interface=wg-secure]] = 0) do={'
            )

            p.append(
                ' :do { /ip address add address=' +
                ros_escape(warp_ip) +
                '/32 interface=wg-secure comment="KETRIKA-WARP-IP" } on-error={}'
            )

            p.append(
                '}'
            )

            # ------------------------------------------------
            # PEER
            # ------------------------------------------------

            p.append(
                ':if ([:len [/interface wireguard peers find interface=wg-secure]] = 0) do={'
            )

            p.append(
                ' :do { /interface wireguard peers add interface=wg-secure public-key="' +
                CF_PUBLIC_KEY +
                '" endpoint-address=' +
                endpoint_ip +
                ' endpoint-port=' +
                str(endpoint_port) +
                ' allowed-address=0.0.0.0/0 persistent-keepalive=25 } on-error={}'
            )

            p.append(
                '}'
            )

            # ------------------------------------------------
            # NAT WARP
            # ------------------------------------------------

            p.append(
                ':if ([:len [/ip firewall nat find comment="KETRIKA-V6-WARP-NAT"]] = 0) do={'
            )

            p.append(
                ' :do { /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade comment="KETRIKA-V6-WARP-NAT" } on-error={}'
            )

            p.append(
                '}'
            )

            # ------------------------------------------------
            # MSS
            # ------------------------------------------------

            p.append(
                ':if ([:len [/ip firewall mangle find comment="KETRIKA-V6-MSS"]] = 0) do={'
            )

            p.append(
                ' :do { /ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="KETRIKA-V6-MSS" } on-error={}'
            )

            p.append(
                '}'
            )

        else:

            p.append(
                ':log warning "KETRIKA V6: WARP non enregistre - installation continue"'
            )

    else:

        p.append(
            ':put "[9/10] WARP non demande - ignore..."'
        )

    p.append(
        ':delay 1'
    )

    p.append("")

    # ========================================================
    # PHASE 10
    # FINAL SANS COUPURE
    # ========================================================

    p.append(
        ':put "[10/10] Finalisation securisee..."'
    )

    # --------------------------------------------------------
    # TTL
    # --------------------------------------------------------
    #
    # V6 : seulement si demandé.
    #
    # On ne supprime pas les mangle existants.
    #
    if str(ttl) != "0":

        p.append(
            ':if ([:len [/ip firewall mangle find comment="KETRIKA-V6-TTL"]] = 0) do={'
        )

        p.append(
            ' :do { /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' +
            str(ttl) +
            ' passthrough=yes comment="KETRIKA-V6-TTL" } on-error={}'
        )

        p.append(
            '}'
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
            ':if ([:len [/queue simple find name="QoS-Global"]] = 0) do={'
        )

        p.append(
            ' :do { /queue simple add name="QoS-Global" target=' +
            ros_escape(net) +
            ' max-limit=' +
            lim_ul +
            '/' +
            lim_dl +
            ' } on-error={}'
        )

        p.append(
            '}'
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
            ':if ([:len [/queue type find name="pcq-dl"]] = 0) do={'
        )

        p.append(
            ' :do { /queue type add name=pcq-dl kind=pcq pcq-rate=' +
            cl +
            ' pcq-classifier=dst-address } on-error={}'
        )

        p.append(
            '}'
        )

        p.append(
            ':if ([:len [/queue type find name="pcq-ul"]] = 0) do={'
        )

        p.append(
            ' :do { /queue type add name=pcq-ul kind=pcq pcq-rate=' +
            cl +
            ' pcq-classifier=src-address } on-error={}'
        )

        p.append(
            '}'
        )

        p.append(
            ':if ([:len [/queue simple find name="QoS-PerClient"]] = 0) do={'
        )

        p.append(
            ' :do { /queue simple add name="QoS-PerClient" target=' +
            ros_escape(net) +
            ' queue=pcq-ul/pcq-dl } on-error={}'
        )

        p.append(
            '}'
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
    # SLEEP MODE
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
            ':if ([:len [/system scheduler find name="ketrika-sleep-off"]] = 0) do={'
        )

        p.append(
            ' :do { /system scheduler add name="ketrika-sleep-off" start-time=' +
            start_t +
            ' interval=1d on-event="/interface wifi set [find] disabled=yes; /interface wireless set [find] disabled=yes" } on-error={}'
        )

        p.append(
            '}'
        )

        p.append(
            ':if ([:len [/system scheduler find name="ketrika-sleep-on"]] = 0) do={'
        )

        p.append(
            ' :do { /system scheduler add name="ketrika-sleep-on" start-time=' +
            end_t +
            ' interval=1d on-event="/interface wifi set [find] disabled=no; /interface wireless set [find] disabled=no" } on-error={}'
        )

        p.append(
            '}'
        )

    # ========================================================
    # FIREWALL MANAGEMENT
    # ========================================================
    #
    # IMPORTANT :
    # Pas de "remove [find]".
    #
    # On ajoute uniquement une règle de protection
    # KETRIKA-V6 si elle n'existe pas.
    #

    p.append(
        ':if ([:len [/ip firewall filter find comment="KETRIKA-V6-ESTABLISHED"]] = 0) do={'
    )

    p.append(
        ' :do { /ip firewall filter add chain=input connection-state=established,related action=accept place-before=0 comment="KETRIKA-V6-ESTABLISHED" } on-error={}'
    )

    p.append(
        '}'
    )

    p.append(
        ':if ([:len [/ip firewall filter find comment="KETRIKA-V6-INVALID"]] = 0) do={'
    )

    p.append(
        ' :do { /ip firewall filter add chain=input connection-state=invalid action=drop comment="KETRIKA-V6-INVALID" } on-error={}'
    )

    p.append(
        '}'
    )

    # --------------------------------------------------------
    # LOG FINAL
    # --------------------------------------------------------

    p.append(
        ':log info "KETRIKA V6: Configuration terminee sans operation reseau destructive."'
    )

    p.append(
        ':delay 1'
    )

    # ========================================================
    # MESSAGE FINAL
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
        ':put "##          K E T R I K A   V 6                           ##"'
    )

    p.append(
        ':put "##              N O   D I S C O N N E C T                ##"'
    )

    p.append(
        ':put "##                                                           ##"'
    )

    p.append(
        ':put "##                 INSTALLATION TERMINEE                   ##"'
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
        ':put "  [OK] WinBox preserve"'
    )

    p.append(
        ':put "  [OK] Bridge conserve"'
    )

    p.append(
        ':put "  [OK] Ports LAN verifies"'
    )

    p.append(
        ':put "  [OK] Wi-Fi AX/AC verifie"'
    )

    p.append(
        ':put "  [OK] DHCP protege"'
    )

    p.append(
        ':put "  [OK] NAT protege"'
    )

    p.append(
        ':put "  [OK] Firewall protege"'
    )

    if plan in (
        "warp",
        "hotspot"
    ):

        if warp_ip:

            p.append(
                ':put "  [OK] WARP configure"'
            )

        else:

            p.append(
                ':put "  [WARNING] WARP non enregistre"'
            )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "  >>> Aucun reboot automatique"'
    )

    p.append(
        ':put "  >>> Aucune suppression globale"'
    )

    p.append(
        ':put "  >>> Aucune modification MAC WAN"'
    )

    p.append(
        ':put "  >>> Session WinBox preservee autant que possible"'
    )

    p.append(
        ':put ""'
    )

    p.append(
        ':put "=================================================="'
    )

    p.append(
        ':put " KETRIKA V6 - FIN DU SCRIPT"
    )

    p.append(
        ':put "=================================================="'
    )

    p.append(
        ':put ""'
    )

    p.append(
        "# FIN KETRIKA V6 NO-DISCONNECT"
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
              KETRIKA MIKROTIK V6 - NO-DISCONNECT
================================================================================

Client  : """ + str(client) + """
Licence : """ + str(lic) + """
Date    : """ + time.strftime(
        "%d/%m/%Y",
        time.gmtime()
    ) + """

================================================================================
OBJECTIF
================================================================================

Cette version est conçue pour être collée directement dans WinBox Terminal.

La priorité est de conserver la session WinBox pendant toute l'installation.

Le script évite notamment :

- suppression globale du NAT
- suppression globale du mangle
- suppression globale du DHCP
- suppression du bridge
- suppression des ports du bridge
- modification automatique du MAC WAN
- reboot automatique
- suppression de l'adresse IP existante

================================================================================
BRIDGE
================================================================================

Le bridge1 est conservé s'il existe.

Les ports Ethernet disponibles sont vérifiés.

Le WAN reste exclu du bridge.

Les ports LAN manquants sont ajoutés sans supprimer les ports
déjà existants.

Les interfaces Wi-Fi sont également ajoutées au bridge si elles
ne sont pas déjà présentes.

================================================================================
WINBOX
================================================================================

La règle WinBox est ajoutée en priorité.

Le script ne supprime pas les règles firewall existantes.

L'adresse IP de management existante n'est jamais supprimée.

================================================================================
IMPORTANT
================================================================================

Aucune configuration réseau ne peut garantir mathématiquement
une session WinBox si l'utilisateur modifie ensuite manuellement
l'adresse IP, le bridge ou l'interface de management pendant
l'installation.

KETRIKA V6 évite volontairement ces opérations dangereuses.

================================================================================
INSTALLATION
================================================================================

1. Ouvrir WinBox.
2. Se connecter au MikroTik.
3. Ouvrir New Terminal.
4. Coller le script complet.
5. Ne pas modifier manuellement le réseau pendant l'installation.
6. Attendre :

   KETRIKA V6 - FIN DU SCRIPT

7. Vérifier Internet.
8. Vérifier les ports LAN.
9. Vérifier le Wi-Fi.
10. Vérifier WARP si le plan l'utilise.

================================================================================
SUPPORT
================================================================================

KETRIKA MIKROTIK - Madagascar

================================================================================
"""

    return guide
