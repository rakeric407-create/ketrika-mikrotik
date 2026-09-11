# ============================================================
# KETRIKA MIKROTIK - warp_api.py
# V6.1 - NO-DISCONNECT
# ============================================================
#
# OBJECTIF :
#   Générer un script RouterOS v7 qui évite les opérations
#   susceptibles de couper la session WinBox pendant le collage.
#
# IMPORTANT :
#   - Aucun changement de MAC WAN
#   - Aucun reboot
#   - Aucun remove global
#   - Aucun remplacement forcé du bridge
#   - Aucun remplacement de l'IP LAN existante
#   - Aucun remplacement du DHCP existant
#   - Aucun remplacement du NAT existant
#   - Aucun remplacement du firewall existant
#
# ============================================================

import os
import random
import base64
import time
import hashlib
import requests


# ============================================================
# CLOUDFLARE WARP
# ============================================================

CF_PUBLIC_KEY = (
    "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
)

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
        if isinstance(obj, dict):
            value = obj.get(key, default)
        else:
            value = getattr(obj, key, default)

        return default if value is None else value

    except Exception:
        return default


def ros_escape(value):
    """
    Echappe une valeur destinée à une chaîne RouterOS.
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
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "oui",
    )


# ============================================================
# X25519 / CURVE25519
# ============================================================

def curve25519_scalarmult(scalar):
    """
    X25519 minimal implementation utilisée uniquement
    pour générer la paire de clés WireGuard.
    """

    P = 2 ** 255 - 19

    def encode_int(value):
        return (
            value % P
        ).to_bytes(
            32,
            "little"
        )

    def decode_int(data):
        return int.from_bytes(
            data,
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

    k_int = decode_int(k)

    x1 = 9
    x2 = 1
    z2 = 0
    x3 = 9
    z3 = 1

    swap = 0

    for t in range(
        254,
        -1,
        -1
    ):

        kt = (
            k_int >> t
        ) & 1

        swap ^= kt

        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2

        swap = kt

        a = (
            x2 + z2
        ) % P

        aa = (
            a * a
        ) % P

        b = (
            x2 - z2
        ) % P

        bb = (
            b * b
        ) % P

        e = (
            aa - bb
        ) % P

        c = (
            x3 + z3
        ) % P

        d = (
            x3 - z3
        ) % P

        da = (
            d * a
        ) % P

        cb = (
            c * b
        ) % P

        x3 = (
            (da + cb) *
            (da + cb)
        ) % P

        z3 = (
            x1 *
            (da - cb) *
            (da - cb)
        ) % P

        x2 = (
            aa * bb
        ) % P

        z2 = (
            e *
            (aa + 121665 * e)
        ) % P

    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2

    result = (
        x2 *
        inv(z2)
    ) % P

    return encode_int(
        result
    )


# ============================================================
# GENERATE WIREGUARD KEYS
# ============================================================

def generate_wireguard_keys():

    private_key = os.urandom(
        32
    )

    public_key = curve25519_scalarmult(
        private_key
    )

    return {
        "private_key": base64.b64encode(
            private_key
        ).decode(
            "ascii"
        ),
        "public_key": base64.b64encode(
            public_key
        ).decode(
            "ascii"
        ),
    }


# ============================================================
# REGISTER WARP
# ============================================================

def register_warp(public_key):

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
        "serial_number": hashlib.sha256(
            public_key.encode(
                "utf-8"
            )
        ).hexdigest()[:16],
        "locale": "fr_MG",
    }

    try:

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.status_code not in (
            200,
            201
        ):
            return {
                "success": False,
                "ipv4": "",
                "data": {},
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
                "/",
                1
            )[0]

        return {
            "success": bool(ipv4),
            "ipv4": ipv4,
            "data": data,
        }

    except Exception:
        return {
            "success": False,
            "ipv4": "",
            "data": {},
        }


# ============================================================
# ROUTEROS SAFE HEADER
# ============================================================

def _header(script, text):
    script.append("")
    script.append(
        ':put "=================================================="'
    )
    script.append(
        ':put "' + ros_escape(text) + '"'
    )
    script.append(
        ':put "=================================================="'
    )
    script.append("")


# ============================================================
# GENERATE SCRIPT
# ============================================================

def generate_script(order):

    # --------------------------------------------------------
    # PARAMETRES
    # --------------------------------------------------------

    plan_type = safe_get(
        order,
        "plan_type",
        "standard"
    )

    mikrotik_model = safe_get(
        order,
        "mikrotik_model",
        "hap_ac2"
    )

    ssid = safe_get(
        order,
        "ssid",
        "KETRIKA-WiFi"
    )

    wifi_password = safe_get(
        order,
        "wifi_password",
        "Ketrika@2026"
    )

    wan_interface = safe_get(
        order,
        "wan_interface",
        "ether1"
    )

    lan_gateway = safe_get(
        order,
        "lan_gateway",
        "192.168.88.1"
    )

    lan_network = safe_get(
        order,
        "lan_network",
        "192.168.88.0/24"
    )

    dhcp_pool = safe_get(
        order,
        "dhcp_pool",
        "192.168.88.10-192.168.88.250"
    )

    ttl_value = safe_get(
        order,
        "ttl_value",
        "64"
    )

    dl_limit = safe_get(
        order,
        "dl_limit",
        "0"
    )

    ul_limit = safe_get(
        order,
        "ul_limit",
        "0"
    )

    license_key = safe_get(
        order,
        "license_key",
        "DEMO"
    )

    router_name = safe_get(
        order,
        "router_name",
        "KETRIKA"
    )

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

    # --------------------------------------------------------
    # DATABASE - COMPATIBILITE
    # --------------------------------------------------------

    try:

        from database import (
            get_model_info,
            generate_router_name,
            generate_random_mac
        )

    except Exception:

        get_model_info = None
        generate_router_name = None
        generate_random_mac = None

    # --------------------------------------------------------
    # NOM ROUTEUR
    # --------------------------------------------------------

    if not router_name:

        if generate_router_name:

            try:
                router_name = generate_router_name(
                    license_key
                )

            except Exception:
                router_name = "KETRIKA"

        else:
            router_name = "KETRIKA"

    # --------------------------------------------------------
    # MAC
    # --------------------------------------------------------
    #
    # V6 NO-DISCONNECT :
    #
    # ON NE CHANGE PAS LE MAC WAN.
    #
    # Même si mac_spoof=True.
    #
    # La variable reste lue pour compatibilité avec
    # l'ancienne interface.
    # --------------------------------------------------------

    if mac_spoof and not mac_address:

        if generate_random_mac:

            try:
                mac_address = generate_random_mac()
            except Exception:
                mac_address = ""

    # --------------------------------------------------------
    # WARP
    # --------------------------------------------------------

    warp_private = ""
    warp_public = ""
    warp_ipv4 = ""

    warp_ok = False

    if plan_type in (
        "warp",
        "hotspot"
    ):

        keys = generate_wireguard_keys()

        warp_private = keys[
            "private_key"
        ]

        warp_public = keys[
            "public_key"
        ]

        warp_result = register_warp(
            warp_public
        )

        if warp_result.get(
            "success",
            False
        ):

            warp_ok = True

            warp_ipv4 = warp_result.get(
                "ipv4",
                ""
            )

    endpoint_ip, endpoint_port = random.choice(
        WARP_ENDPOINTS
    )

    # ========================================================
    # SCRIPT ROUTEROS
    # ========================================================

    script = []

    # ========================================================
    # HEADER
    # ========================================================

    script.append(
        "# ============================================================"
    )

    script.append(
        "# KETRIKA MIKROTIK V6.1 - NO-DISCONNECT"
    )

    script.append(
        "# ============================================================"
    )

    script.append(
        "# Licence : " +
        ros_escape(license_key)
    )

    script.append(
        "# Plan    : " +
        ros_escape(plan_type)
    )

    script.append(
        "# Model   : " +
        ros_escape(mikrotik_model)
    )

    script.append(
        "# WAN     : " +
        ros_escape(wan_interface)
    )

    script.append(
        "# ============================================================"
    )

    script.append("")

    script.append(
        ':put "KETRIKA V6.1 - NO-DISCONNECT"'
    )

    script.append(
        ':put "Debut de configuration..."'
    )

    script.append(
        ':log info "KETRIKA V6.1 START"'
    )

    # ========================================================
    # 1 - WINBOX
    # ========================================================

    _header(
        script,
        "1/10 - PROTECTION WINBOX"
    )

    # Accepter WinBox.
    #
    # IMPORTANT :
    # Aucun remove.
    # Aucun changement de port.
    #

    script.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 connection-state=new action=accept place-before=0 comment="KETRIKA-V61-WINBOX" } on-error={}'
    )

    script.append(
        ':do { /ip firewall filter add chain=input protocol=tcp dst-port=22 connection-state=new action=accept place-before=0 comment="KETRIKA-V61-SSH" } on-error={}'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 2 - DETECTION BRIDGE
    # ========================================================

    _header(
        script,
        "2/10 - DETECTION DU BRIDGE EXISTANT"
    )

    #
    # ON NE SUPPRIME PAS bridge1.
    #
    # On utilise :
    #
    # 1. bridge1 s'il existe
    # 2. sinon le premier bridge existant
    # 3. sinon création de bridge1
    #
    # La variable globale KETRIKA_BRIDGE reste disponible
    # pour le reste du script.
    #

    script.append(
        ':global KETRIKA_BRIDGE'
    )

    script.append(
        ':local kBridge1 [/interface bridge find name="bridge1"]'
    )

    script.append(
        ':if ([:len $kBridge1] > 0) do={'
    )

    script.append(
        ' :set KETRIKA_BRIDGE "bridge1"'
    )

    script.append(
        '} else={'
    )

    script.append(
        ' :local kAllBridges [/interface bridge find]'
    )

    script.append(
        ' :if ([:len $kAllBridges] > 0) do={'
    )

    script.append(
        '  :set KETRIKA_BRIDGE [/interface bridge get [:pick $kAllBridges 0] name]'
    )

    script.append(
        ' } else={'
    )

    script.append(
        '  :do { /interface bridge add name="bridge1" auto-mac=yes comment="KETRIKA-V61" } on-error={}'
    )

    script.append(
        '  :set KETRIKA_BRIDGE "bridge1"'
    )

    script.append(
        ' }'
    )

    script.append(
        '}'
    )

    script.append(
        ':put ("Bridge utilise : " . $KETRIKA_BRIDGE)'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 3 - PORTS ETHERNET
    # ========================================================

    _header(
        script,
        "3/10 - VERIFICATION DES PORTS"
    )

    #
    # IMPORTANT :
    #
    # Aucun port existant n'est retiré.
    #
    # Si le port appartient déjà à un bridge :
    # on le laisse exactement comme il est.
    #
    # Si le port n'appartient à aucun bridge :
    # on peut l'ajouter.
    #

    script.append(
        ':foreach eth in=[/interface ethernet find] do={'
    )

    script.append(
        ' :local ethName [/interface ethernet get $eth name]'
    )

    script.append(
        ' :if ($ethName != "' +
        ros_escape(wan_interface) +
        '") do={'
    )

    script.append(
        '  :local existingPort [/interface bridge port find interface=$ethName]'
    )

    script.append(
        '  :if ([:len $existingPort] = 0) do={'
    )

    script.append(
        '   :do { /interface bridge port add bridge=$KETRIKA_BRIDGE interface=$ethName } on-error={}'
    )

    script.append(
        '  }'
    )

    script.append(
        ' }'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 4 - WIFI AX
    # ========================================================

    _header(
        script,
        "4/10 - WIFI AX / WIFI 6"
    )

    #
    # Configuration AX.
    #
    # Si RouterOS n'a pas /interface wifi,
    # on-error empêche l'arrêt du script.
    #

    script.append(
        ':do { /interface wifi set [find] disabled=no } on-error={}'
    )

    script.append(
        ':do { /interface wifi set [find] configuration.mode=ap } on-error={}'
    )

    script.append(
        ':do { /interface wifi set [find] configuration.ssid="' +
        ros_escape(ssid) +
        '" } on-error={}'
    )

    #
    # Sécurité.
    #
    # On évite de toucher à des paramètres qui pourraient
    # provoquer une longue attente DFS.
    #

    script.append(
        ':do { /interface wifi set [find] security.authentication-types=wpa2-psk } on-error={}'
    )

    script.append(
        ':do { /interface wifi set [find] security.passphrase="' +
        ros_escape(wifi_password) +
        '" } on-error={}'
    )

    #
    # Ajouter Wi-Fi seulement s'il n'est pas déjà dans
    # un bridge.
    #

    script.append(
        ':foreach wifiIf in=[/interface wifi find] do={'
    )

    script.append(
        ' :local wifiName [/interface wifi get $wifiIf name]'
    )

    script.append(
        ' :local wifiPort [/interface bridge port find interface=$wifiName]'
    )

    script.append(
        ' :if ([:len $wifiPort] = 0) do={'
    )

    script.append(
        '  :do { /interface bridge port add bridge=$KETRIKA_BRIDGE interface=$wifiName } on-error={}'
    )

    script.append(
        ' }'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 2s'
    )

    # ========================================================
    # 5 - WIFI LEGACY
    # ========================================================

    _header(
        script,
        "5/10 - WIFI AC / N"
    )

    script.append(
        ':do { /interface wireless set [find] disabled=no } on-error={}'
    )

    script.append(
        ':do { /interface wireless set [find] mode=ap-bridge } on-error={}'
    )

    script.append(
        ':do { /interface wireless set [find] ssid="' +
        ros_escape(ssid) +
        '" } on-error={}'
    )

    #
    # Security profile default.
    #

    script.append(
        ':do { /interface wireless security-profiles set [find default=yes] mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' +
        ros_escape(wifi_password) +
        '" } on-error={}'
    )

    #
    # Bridge Wi-Fi legacy.
    #

    script.append(
        ':foreach wifiOld in=[/interface wireless find] do={'
    )

    script.append(
        ' :local oldName [/interface wireless get $wifiOld name]'
    )

    script.append(
        ' :local oldPort [/interface bridge port find interface=$oldName]'
    )

    script.append(
        ' :if ([:len $oldPort] = 0) do={'
    )

    script.append(
        '  :do { /interface bridge port add bridge=$KETRIKA_BRIDGE interface=$oldName } on-error={}'
    )

    script.append(
        ' }'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 2s'
    )

    # ========================================================
    # 6 - IP / DHCP
    # ========================================================

    _header(
        script,
        "6/10 - IP / DHCP SANS SUPPRESSION"
    )

    #
    # IMPORTANT :
    #
    # On ne supprime aucune IP.
    #
    # Si le bridge possède déjà une IP :
    # on la conserve.
    #
    # Si le bridge n'a aucune IP :
    # on ajoute celle demandée.
    #

    script.append(
        ':local bridgeAddress [/ip address find interface=$KETRIKA_BRIDGE disabled=no]'
    )

    script.append(
        ':if ([:len $bridgeAddress] = 0) do={'
    )

    script.append(
        ' :do { /ip address add address="' +
        ros_escape(lan_gateway) +
        '/24" interface=$KETRIKA_BRIDGE comment="KETRIKA-V61-LAN" } on-error={}'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 1s'
    )

    #
    # DNS.
    #
    # Modifier DNS ne coupe normalement pas WinBox.
    #

    script.append(
        ':do { /ip dns set allow-remote-requests=yes } on-error={}'
    )

    script.append(
        ':do { /ip dns set servers=1.1.1.1,1.0.0.1 } on-error={}'
    )

    #
    # Pool seulement s'il n'existe pas.
    #

    script.append(
        ':if ([:len [/ip pool find name="ketrika-pool"]] = 0) do={'
    )

    script.append(
        ' :do { /ip pool add name="ketrika-pool" ranges="' +
        ros_escape(dhcp_pool) +
        '" } on-error={}'
    )

    script.append(
        '}'
    )

    #
    # DHCP :
    # ne jamais créer un second DHCP sur le même bridge.
    #

    script.append(
        ':local existingDHCP [/ip dhcp-server find interface=$KETRIKA_BRIDGE disabled=no]'
    )

    script.append(
        ':if ([:len $existingDHCP] = 0) do={'
    )

    script.append(
        ' :do { /ip dhcp-server add name="KETRIKA-DHCP" interface=$KETRIKA_BRIDGE address-pool="ketrika-pool" lease-time=1d disabled=no } on-error={}'
    )

    script.append(
        '}'
    )

    #
    # DHCP network seulement si elle n'existe pas.
    #

    script.append(
        ':if ([:len [/ip dhcp-server network find address="' +
        ros_escape(lan_network) +
        '"]] = 0) do={'
    )

    script.append(
        ' :do { /ip dhcp-server network add address="' +
        ros_escape(lan_network) +
        '" gateway="' +
        ros_escape(lan_gateway) +
        '" dns-server="' +
        ros_escape(lan_gateway) +
        '" comment="KETRIKA-V61" } on-error={}'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 7 - WAN
    # ========================================================

    _header(
        script,
        "7/10 - WAN SANS CHANGEMENT MAC"
    )

    #
    # NE JAMAIS FAIRE :
    #
    # /interface ethernet set ether1 mac-address=...
    #
    # dans la version NO-DISCONNECT.
    #

    script.append(
        ':put "MAC WAN : NON MODIFIE - protection WinBox"'
    )

    #
    # DHCP client WAN :
    # uniquement s'il n'existe pas.
    #

    script.append(
        ':local wanDhcp [/ip dhcp-client find interface="' +
        ros_escape(wan_interface) +
        '"]'
    )

    script.append(
        ':if ([:len $wanDhcp] = 0) do={'
    )

    script.append(
        ' :do { /ip dhcp-client add interface="' +
        ros_escape(wan_interface) +
        '" add-default-route=yes use-peer-dns=no disabled=no comment="KETRIKA-V61-WAN" } on-error={}'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 8 - NAT
    # ========================================================

    _header(
        script,
        "8/10 - NAT SANS SUPPRESSION"
    )

    #
    # On ne supprime aucun NAT existant.
    #

    script.append(
        ':if ([:len [/ip firewall nat find comment="KETRIKA-V61-NAT"]] = 0) do={'
    )

    script.append(
        ' :do { /ip firewall nat add chain=srcnat out-interface="' +
        ros_escape(wan_interface) +
        '" action=masquerade comment="KETRIKA-V61-NAT" } on-error={}'
    )

    script.append(
        '}'
    )

    script.append(
        ':delay 1s'
    )

    # ========================================================
    # 9 - WARP
    # ========================================================

    _header(
        script,
        "9/10 - WARP"
    )

    if plan_type in (
        "warp",
        "hotspot"
    ):

        if warp_ok and warp_ipv4:

            #
            # WireGuard.
            #

            script.append(
                ':if ([:len [/interface wireguard find name="ketrika-warp"]] = 0) do={'
            )

            script.append(
                ' :do { /interface wireguard add name="ketrika-warp" mtu=1280 private-key="' +
                ros_escape(warp_private) +
                '" comment="KETRIKA-V61-WARP" } on-error={}'
            )

            script.append(
                '}'
            )

            #
            # IP WARP.
            #

            script.append(
                ':if ([:len [/ip address find interface="ketrika-warp"]] = 0) do={'
            )

            script.append(
                ' :do { /ip address add address="' +
                ros_escape(warp_ipv4) +
                '/32" interface="ketrika-warp" comment="KETRIKA-V61-WARP-IP" } on-error={}'
            )

            script.append(
                '}'
            )

            #
            # Peer.
            #

            script.append(
                ':if ([:len [/interface wireguard peers find interface="ketrika-warp"]] = 0) do={'
            )

            script.append(
                ' :do { /interface wireguard peers add interface="ketrika-warp" public-key="' +
                CF_PUBLIC_KEY +
                '" endpoint-address="' +
                endpoint_ip +
                '" endpoint-port=' +
                str(endpoint_port) +
                ' allowed-address=0.0.0.0/0 persistent-keepalive=25 } on-error={}'
            )

            script.append(
                '}'
            )

            #
            # NAT WARP.
            #

            script.append(
                ':if ([:len [/ip firewall nat find comment="KETRIKA-V61-WARP-NAT"]] = 0) do={'
            )

            script.append(
                ' :do { /ip firewall nat add chain=srcnat out-interface="ketrika-warp" action=masquerade comment="KETRIKA-V61-WARP-NAT" } on-error={}'
            )

            script.append(
                '}'
            )

            #
            # MSS.
            #

            script.append(
                ':if ([:len [/ip firewall mangle find comment="KETRIKA-V61-WARP-MSS"]] = 0) do={'
            )

            script.append(
                ' :do { /ip firewall mangle add chain=forward out-interface="ketrika-warp" protocol=tcp tcp-flags=syn action=change-mss new-mss=1280 passthrough=yes comment="KETRIKA-V61-WARP-MSS" } on-error={}'
            )

            script.append(
                '}'
            )

            #
            # IMPORTANT :
            #
            # PAS DE MARK ROUTING GLOBAL.
            #
            # On ne force PAS toutes les connexions vers WARP.
            #
            # C'est volontaire :
            # un mark-routing mal placé peut faire sortir les
            # réponses WinBox par WARP et provoquer une coupure.
            #

            script.append(
                ':put "WARP : interface configuree, routage global NON force"'
            )

        else:

            script.append(
                ':put "WARP : enregistrement API echoue - installation continue"'
            )

            script.append(
                ':log warning "KETRIKA-V61 : WARP API indisponible"'
            )

    else:

        script.append(
            ':put "WARP : non demande par ce plan"'
        )

    # ========================================================
    # 10 - FINAL
    # ========================================================

    _header(
        script,
        "10/10 - FINALISATION"
    )

    #
    # TTL
    #
    # On ajoute une règle seulement si ttl est valide.
    #

    try:
        ttl_int = int(
            str(ttl_value)
        )
    except Exception:
        ttl_int = 0

    if 1 <= ttl_int <= 255:

        script.append(
            ':if ([:len [/ip firewall mangle find comment="KETRIKA-V61-TTL"]] = 0) do={'
        )

        script.append(
            ' :do { /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' +
            str(ttl_int) +
            ' passthrough=yes comment="KETRIKA-V61-TTL" } on-error={}'
        )

        script.append(
            '}'
        )

    # ========================================================
    # QOS
    # ========================================================

    if str(dl_limit).strip() not in (
        "",
        "0",
        "0M"
    ) or str(ul_limit).strip() not in (
        "",
        "0",
        "0M"
    ):

        download = str(
            dl_limit
        ).strip()

        upload = str(
            ul_limit
        ).strip()

        if download and not any(
            x in download.upper()
            for x in (
                "K",
                "M",
                "G"
            )
        ):
            download += "M"

        if upload and not any(
            x in upload.upper()
            for x in (
                "K",
                "M",
                "G"
            )
        ):
            upload += "M"

        if not upload:
            upload = "0"

        if not download:
            download = "0"

        #
        # Une seule queue KETRIKA.
        #
        # Pas de suppression des anciennes queues.
        #

        script.append(
            ':if ([:len [/queue simple find name="KETRIKA-V61-QOS"]] = 0) do={'
        )

        script.append(
            ' :do { /queue simple add name="KETRIKA-V61-QOS" target="' +
            ros_escape(lan_network) +
            '" max-limit="' +
            ros_escape(upload) +
            '/' +
            ros_escape(download) +
            '" comment="KETRIKA-V61" } on-error={}'
        )

        script.append(
            '}'
        )

    # ========================================================
    # IDENTITY
    # ========================================================

    script.append(
        ':do { /system identity set name="' +
        ros_escape(router_name) +
        '" } on-error={}'
    )

    # ========================================================
    # SLEEP
    # ========================================================
    #
    # On NE crée pas de scheduler par défaut.
    #
    # Si activé, on crée uniquement les schedulers manquants.
    #

    if str(sleep_mode).lower() not in (
        "",
        "off",
        "none",
        "disabled",
        "0"
    ):

        sleep_start = "00:00:00"
        sleep_end = "06:00:00"

        mode = str(
            sleep_mode
        ).lower()

        if mode == "01-05":
            sleep_start = "01:00:00"
            sleep_end = "05:00:00"

        elif mode == "02-06":
            sleep_start = "02:00:00"
            sleep_end = "06:00:00"

        elif mode == "23-07":
            sleep_start = "23:00:00"
            sleep_end = "07:00:00"

        script.append(
            ':if ([:len [/system scheduler find name="KETRIKA-V61-SLEEP-OFF"]] = 0) do={'
        )

        script.append(
            ' :do { /system scheduler add name="KETRIKA-V61-SLEEP-OFF" start-time=' +
            sleep_start +
            ' interval=1d on-event="/interface wifi set [find] disabled=yes; /interface wireless set [find] disabled=yes" comment="KETRIKA-V61" } on-error={}'
        )

        script.append(
            '}'
        )

        script.append(
            ':if ([:len [/system scheduler find name="KETRIKA-V61-SLEEP-ON"]] = 0) do={'
        )

        script.append(
            ' :do { /system scheduler add name="KETRIKA-V61-SLEEP-ON" start-time=' +
            sleep_end +
            ' interval=1d on-event="/interface wifi set [find] disabled=no; /interface wireless set [find] disabled=no" comment="KETRIKA-V61" } on-error={}'
        )

        script.append(
            '}'
        )

    # ========================================================
    # FINAL FIREWALL SAFE
    # ========================================================

    #
    # ESTABLISHED / RELATED
    #

    script.append(
        ':if ([:len [/ip firewall filter find comment="KETRIKA-V61-ESTABLISHED"]] = 0) do={'
    )

    script.append(
        ' :do { /ip firewall filter add chain=input connection-state=established,related action=accept place-before=0 comment="KETRIKA-V61-ESTABLISHED" } on-error={}'
    )

    script.append(
        '}'
    )

    #
    # NE PAS ajouter un DROP WAN agressif.
    #
    # Cela pourrait couper WinBox si l'utilisateur est connecté
    # d'une manière différente de celle prévue.
    #

    # ========================================================
    # FIN
    # ========================================================

    script.append(
        ':log info "KETRIKA V6.1 : FIN"'
    )

    script.append(
        ':delay 1s'
    )

    script.append(
        ':put ""'
    )

    script.append(
        ':put "############################################################"'
    )

    script.append(
        ':put "# KETRIKA MIKROTIK V6.1 - TERMINE                  #"'
    )

    script.append(
        ':put "#                                                    #"'
    )

    script.append(
        ':put "# WINBOX : PROTEGE                                  #"'
    )

    script.append(
        ':put "# BRIDGE : CONSERVE                                 #"'
    )

    script.append(
        ':put "# DHCP   : CONSERVE                                 #"'
    )

    script.append(
        ':put "# NAT    : CONSERVE                                 #"'
    )

    script.append(
        ':put "# MAC WAN: NON MODIFIE                              #"'
    )

    script.append(
        ':put "# REBOOT : AUCUN                                   #"'
    )

    script.append(
        ':put "############################################################"'
    )

    script.append(
        ':put ""'
    )

    script.append(
        ':put "Installation KETRIKA terminee."'
    )

    script.append(
        ':put "Ne redemarrez pas le routeur automatiquement."'
    )

    script.append(
        ':put ""'
    )

    script.append(
        "# ================= FIN KETRIKA V6.1 ================="
    )

    return "\n".join(
        script
    )


# ============================================================
# GUIDE D'INSTALLATION
# ============================================================

def generate_secret_guide(order):

    license_key = safe_get(
        order,
        "license_key",
        "DEMO"
    )

    return """
============================================================
KETRIKA MIKROTIK V6.1 - NO-DISCONNECT
============================================================

Licence :
""" + str(
        license_key
    ) + """

INSTALLATION :

1. Connectez-vous avec WinBox.
2. Ouvrez Terminal.
3. Collez tout le script.
4. Ne cliquez pas sur Reboot.
5. Attendez le message :

   Installation KETRIKA terminee.

PRINCIPES V6.1 :

- aucun remove global
- aucun reboot
- aucun changement MAC WAN
- aucun remplacement du bridge existant
- aucun retrait de port existant
- aucun remplacement du DHCP existant
- aucun remplacement du NAT existant
- aucun routage WARP global
- protection WinBox avant configuration

IMPORTANT :

Cette version privilégie la stabilité de WinBox.

Si une ancienne configuration existe déjà,
elle est conservée plutôt que supprimée.

============================================================
"""
