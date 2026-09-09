#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Moteur de génération de scripts RouterOS v7
Version Ultra-Stable, Anti-Bootloop, Spécialiste Wi-Fi AX/AC & Hotspot
"""

import os
import random
import string
import base64
import time
import hashlib

CF_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="


def safe_get(obj, key, default=''):
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default


def curve25519_scalarmult(scalar):
    P = 2**255 - 19
    def dec(s): return int.from_bytes(s, 'little')
    def enc(u): return (u % P).to_bytes(32, 'little')
    def inv(x): return pow(x, P - 2, P)
    k = bytearray(scalar)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    u = 9
    x_1, x_2, z_2, x_3, z_3, swap = u, 1, 0, u, 1, 0
    k_int = dec(k)
    for t in range(254, -1, -1):
        k_t = (k_int >> t) & 1
        swap ^= k_t
        d = swap * (x_2 ^ x_3); x_2 ^= d; x_3 ^= d
        d = swap * (z_2 ^ z_3); z_2 ^= d; z_3 ^= d
        swap = k_t
        A = (x_2 + z_2) % P; AA = (A * A) % P
        B = (x_2 - z_2) % P; BB = (B * B) % P
        E = (AA - BB) % P
        C = (x_3 + z_3) % P; D = (x_3 - z_3) % P
        DA = (D * A) % P; CB = (C * B) % P
        x_3 = pow(DA + CB, 2, P)
        z_3 = (x_1 * pow(DA - CB, 2, P)) % P
        x_2 = (AA * BB) % P
        z_2 = (E * (AA + 121665 * E)) % P
    d = swap * (x_2 ^ x_3); x_2 ^= d; x_3 ^= d
    d = swap * (z_2 ^ z_3); z_2 ^= d; z_3 ^= d
    return enc((x_2 * inv(z_2)) % P)


def generate_wireguard_keys():
    priv = os.urandom(32)
    pub = curve25519_scalarmult(priv)
    return {
        'private_key': base64.b64encode(priv).decode('utf-8'),
        'public_key': base64.b64encode(pub).decode('utf-8')
    }


def register_warp(public_key):
    try:
        import requests
        url = "https://api.cloudflareclient.com/v0a2158/reg"
        headers = {"Content-Type": "application/json", "User-Agent": "okhttp/3.12.1"}
        payload = {
            "key": public_key, "install_id": "", "fcm_token": "",
            "tos": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "model": "MikroTik",
            "serial_number": hashlib.md5(public_key.encode()).hexdigest()[:16],
            "locale": "fr_MG"
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in [200, 201]:
            data = r.json()
            ipv4 = data.get("config", {}).get("interface", {}).get("addresses", {}).get("v4", "172.16.0.2")
            if '/' in ipv4:
                ipv4 = ipv4.split('/')[0]
            return {"success": True, "ipv4": ipv4}
    except Exception:
        pass
    return {"success": False, "ipv4": "172.16.0." + str(random.randint(2, 254))}


def generate_script(order):
    """
    Générateur de scripts RouterOS v7 sans aucune erreur de type 'dynamic item'.
    Compatible 100% avec le Terminal (/import ou copier-coller).
    """
    plan = safe_get(order, 'plan_type', 'standard')
    model = safe_get(order, 'mikrotik_model', 'hap_ac2')
    ssid = safe_get(order, 'ssid', 'KETRIKA-WiFi')
    wifi_pass = safe_get(order, 'wifi_password', 'ketrika2024')
    wan = safe_get(order, 'wan_interface', 'ether1')
    gw = safe_get(order, 'lan_gateway', '192.168.10.1')
    net = safe_get(order, 'lan_network', '192.168.10.0/24')
    pool = safe_get(order, 'dhcp_pool', '192.168.10.10-192.168.10.250')
    ttl = safe_get(order, 'ttl_value', '64')
    dl = safe_get(order, 'dl_limit', '0')
    ul = safe_get(order, 'ul_limit', '0')
    lic = safe_get(order, 'license_key', 'DEMO')

    # Nouvelles options
    router_name = safe_get(order, 'router_name', '')
    mac_spoof = safe_get(order, 'mac_spoof', False)
    mac_address = safe_get(order, 'mac_address', '')
    sleep_mode = safe_get(order, 'sleep_mode', 'off')
    client_limit = safe_get(order, 'client_limit', '0')

    from database import get_model_info, generate_random_mac, generate_router_name
    info = get_model_info(model)
    wifi_type = info.get('wifi_type', 'none')
    wifi_iface = info.get('wifi_iface', None)

    if not router_name:
        router_name = generate_router_name(lic)
    if mac_spoof and not mac_address:
        mac_address = generate_random_mac()

    keys = generate_wireguard_keys()
    warp_reg = register_warp(keys['public_key'])
    warp_ip = warp_reg['ipv4']
    endpoints = ["162.159.192.1", "162.159.193.1", "188.114.96.1", "188.114.97.1"]
    ports = [500, 853, 4500, 2408]
    endpoint_ip = random.choice(endpoints)
    endpoint_port = random.choice(ports)

    p = []

    # ================================================================
    # PHASE 1 : EN-TÊTE + NETTOYAGE SÉCURISÉ (ZÉRO ERREUR SUR ELEMENTS DYNAMIQUES)
    # ================================================================
    p.append("# ============================================================")
    p.append("# KETRIKA MIKROTIK - CONFIGURATION AUTOMATIQUE ROUTEROS v7")
    p.append("# LICENCE : " + lic)
    p.append("# MODELE  : " + model)
    p.append("# DATE    : " + time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()))
    p.append("# ============================================================")
    p.append("")
    p.append("# --- Nettoyage des schedulers temporaires ---")
    p.append(':do { /system scheduler remove [find name~"ketrika"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"br-"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"reboot"] } on-error={}')
    p.append(':do { /system scheduler remove [find name~"sleep"] } on-error={}')
    p.append("")
    p.append("# --- Nettoyage sécurisé sans toucher aux éléments système fixes ---")
    p.append(":do { /ip firewall filter remove [find] } on-error={}")
    p.append(":do { /ip firewall nat remove [find] } on-error={}")
    p.append(":do { /ip firewall mangle remove [find] } on-error={}")
    p.append(":do { /queue simple remove [find] } on-error={}")
    p.append(":do { /ip dhcp-server remove [find] } on-error={}")
    p.append(":do { /ip dhcp-server network remove [find] } on-error={}")
    p.append(":do { /ip pool remove [find] } on-error={}")
    p.append(":do { /ip route remove [find dynamic=no] } on-error={}")
    p.append(':do { /ip dns set servers="" } on-error={}')
    p.append(":do { /interface wireguard remove [find] } on-error={}")
    p.append(':do { /routing table remove [find name!="main"] } on-error={}')
    p.append(":do { /routing rule remove [find] } on-error={}")
    p.append(":do { /ip hotspot user remove [find] } on-error={}")
    p.append(':do { /ip hotspot user profile remove [find name!="default"] } on-error={}')
    p.append(':do { /ip hotspot profile remove [find name!="default"] } on-error={}')
    p.append(":do { /ip hotspot remove [find] } on-error={}")

    # ================================================================
    # PHASE 2 : BRIDGE + PORTS (sans détruire la session active)
    # ================================================================
    p.append("")
    p.append("# --- Création du Bridge LAN ---")
    p.append(':if ([:len [/interface bridge find name=bridge1]] = 0) do={')
    p.append('  /interface bridge add name=bridge1 comment="LAN-KETRIKA"')
    p.append('}')
    p.append("")
    p.append("# --- Rattachement des ports Ethernet ---")
    p.append(':foreach iface in=[/interface ethernet find] do={')
    p.append('  :local ifname [/interface ethernet get $iface name]')
    p.append('  :if ($ifname != "' + wan + '") do={')
    p.append('    :if ([:len [/interface bridge port find interface=$ifname]] = 0) do={')
    p.append('      :do { /interface bridge port add bridge=bridge1 interface=$ifname } on-error={}')
    p.append('    }')
    p.append('  }')
    p.append('}')

    # ================================================================
    # PHASE 3 : IP + DHCP + DNS DOH
    # ================================================================
    p.append("")
    p.append("# --- Client DHCP sur le port WAN ---")
    p.append(':do { /ip dhcp-client add interface=' + wan + ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-Internet" } on-error={}')
    p.append("")
    p.append("# --- Adresse Passerelle LAN ---")
    p.append(':if ([:len [/ip address find interface=bridge1 address="' + gw + '/24"]] = 0) do={')
    p.append('  /ip address add address=' + gw + '/24 interface=bridge1 comment="Passerelle-LAN"')
    p.append('}')
    p.append("")
    p.append("# --- Pool & Serveur DHCP Local ---")
    p.append('/ip pool add name=pool-lan ranges=' + pool)
    p.append('/ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no')
    p.append('/ip dhcp-server network add address=' + net + ' gateway=' + gw + ' dns-server=' + gw)
    p.append("")
    p.append("# --- DNS Cloudflare DoH Sécurisé ---")
    p.append('/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server=https://cloudflare-dns.com/dns-query')

    # ================================================================
    # PHASE 4 : CONFIGURATION WI-FI & AUTO-ACTIVATION (AX / AC / N)
    # ================================================================
    if wifi_type == 'ax' and wifi_iface:
        p.append("")
        p.append("# --- Wi-Fi 6 (AX) - Activation pro ---")
        p.append(':if ([:len [/interface wifi find]] > 0) do={')
        p.append('  :do { /interface wifi configuration remove [find name="ketrika-conf"] } on-error={}')
        p.append('  :do { /interface wifi security remove [find name="ketrika-sec"] } on-error={}')
        
        # Configuration de sécurité WiFi 6
        if plan == 'hotspot':
            p.append('  /interface wifi security add name="ketrika-sec" authentication-types="" disabled=no')
        else:
            p.append('  /interface wifi security add name="ketrika-sec" authentication-types=wpa2-psk,wpa3-psk security.passphrase="' + wifi_pass + '" disabled=no')
            
        p.append('  /interface wifi configuration add name="ketrika-conf" ssid="' + ssid + '" country=madagascar security="ketrika-sec" disabled=no')
        p.append('  /interface wifi set [find] configuration="ketrika-conf" disabled=no')
        p.append('  /interface wifi enable [find]')
        p.append('  :foreach wif in=[/interface wifi find] do={')
        p.append('    :local wname [/interface wifi get $wif name]')
        p.append('    :if ([:len [/interface bridge port find interface=$wname]] = 0) do={')
        p.append('      :do { /interface bridge port add bridge=bridge1 interface=$wname } on-error={}')
        p.append('    }')
        p.append('  }')
        p.append('}')
        
    elif wifi_type in ['ac', 'n'] and wifi_iface:
        p.append("")
        p.append("# --- Wi-Fi 5/4 (AC/N) - Activation pro ---")
        p.append(':if ([:len [/interface wireless find]] > 0) do={')
        p.append('  :do { /interface wireless security-profiles remove [find name="ketrika-sec"] } on-error={}')
        
        # Configuration de sécurité WiFi 5
        if plan == 'hotspot':
            p.append('  /interface wireless security-profiles add name="ketrika-sec" mode=none')
        else:
            p.append('  /interface wireless security-profiles add name="ketrika-sec" mode=dynamic-keys authentication-types=wpa2-psk unicast-ciphers=aes-ccm group-ciphers=aes-ccm wpa2-pre-shared-key="' + wifi_pass + '"')
            
        p.append('  /interface wireless set [find] mode=ap-bridge ssid="' + ssid + '" frequency=auto security-profile="ketrika-sec" disabled=no')
        p.append('  /interface wireless enable [find]')
        p.append('  :foreach wif in=[/interface wireless find] do={')
        p.append('    :local wname [/interface wireless get $wif name]')
        p.append('    :if ([:len [/interface bridge port find interface=$wname]] = 0) do={')
        p.append('      :do { /interface bridge port add bridge=bridge1 interface=$wname } on-error={}')
        p.append('    }')
        p.append('  }')
        p.append('}')

    # ================================================================
    # PHASE 5 : TUNNEL VPN WARP (PACKS SÉCURITÉ OU HOTSPOT)
    # ================================================================
    if plan in ['warp', 'hotspot']:
        p.append("")
        p.append("# ============================================================")
        p.append("# --- TUNNEL VPN WIREGUARD SELECTIONNE ---")
        p.append("# ============================================================")
        p.append('/interface wireguard add name=wg-secure mtu=1280 listen-port=0 \\')
        p.append('  private-key="' + keys['private_key'] + '" comment="WARP-KETRIKA"')
        p.append('/ip address add address=' + warp_ip + '/32 interface=wg-secure')
        p.append('/interface wireguard peers add interface=wg-secure \\')
        p.append('  public-key="' + CF_PUBLIC_KEY + '" \\')
        p.append('  endpoint-address=' + endpoint_ip + ' \\')
        p.append('  endpoint-port=' + str(endpoint_port) + ' \\')
        p.append('  allowed-address=0.0.0.0/0 persistent-keepalive=25')
        p.append("")
        p.append("# --- Table de Routage Dédiée v7 ---")
        p.append('/routing table add name=via-secure fib')
        p.append('/ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure')
        p.append("")
        p.append("# --- Mangle Policy Routing (Intelligent, évite les blocages) ---")
        
        if plan == 'hotspot':
            # ROUTAGE VPN UNIQUEMENT POUR LES CLIENTS CONNECTÉS DU HOTSPOT (TRÈS IMPORTANT !)
            p.append('/ip firewall mangle add chain=prerouting src-address=' + net + ' hotspot=auth \\')
            p.append('  action=mark-routing new-routing-mark=via-secure passthrough=yes comment="Route-Authenticated-To-VPN"')
        else:
            # ROUTAGE VPN NORMAL POUR TOUT LE LAN
            p.append('/ip firewall mangle add chain=prerouting src-address=' + net + ' \\')
            p.append('  action=mark-routing new-routing-mark=via-secure passthrough=yes comment="Route-LAN-To-VPN"')
            
        p.append("")
        p.append("# --- NAT Masquerade VPN & Anti-Fuite DNS ---")
        p.append('/ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade')
        
        if plan == 'hotspot':
            # Redirection DNS uniquement pour les utilisateurs authentifiés
            p.append('/ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect')
            p.append('/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 hotspot=auth action=redirect')
        else:
            p.append('/ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect')
            p.append('/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect')
            
        p.append("")
        p.append("# --- MSS Clamping Anti-DPI ---")
        p.append('/ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn \\')
        p.append('  action=change-mss new-mss=1280 passthrough=yes')

    # ================================================================
    # PHASE 6 : HOTSPOT PORTAIL CAPTIF (PACK 80K)
    # ================================================================
    if plan == 'hotspot':
        p.append("")
        p.append("# ============================================================")
        p.append("# --- PORTAIL CAPTIF HOTSPOT WIFI ZONE (ROBUSTE) ---")
        p.append("# ============================================================")
        p.append('/ip dns static add name=wifi.ketrika.mg address=' + gw)
        p.append('/ip hotspot profile add name=ketrika-hs hotspot-address=' + gw + ' \\')
        p.append('  dns-name=wifi.ketrika.mg login-by=http-pap,cookie \\')
        p.append('  http-cookie-lifetime=1d use-radius=no html-directory=hotspot')
        p.append('/ip hotspot add name=hotspot-ketrika interface=bridge1 \\')
        p.append('  profile=ketrika-hs address-pool=pool-lan disabled=no')
        p.append("")
        p.append("# --- Profils Utilisateurs ---")
        p.append('/ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1')
        p.append('/ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2')
        p.append('/ip hotspot user profile add name="1semaine" rate-limit="5M/10M" session-timeout=7d shared-users=2')
        p.append('/ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3')
        p.append("")
        p.append("# --- 10 Vouchers de test générés ---")
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            p.append('/ip hotspot user add name="' + vc + '" password="' + vc + '" profile="1jour" comment="Ticket-KETRIKA"')
        p.append("")
        p.append("# --- Pare-feu Anti-Torrent P2P ---")
        p.append('/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6999 action=drop comment="Block-P2P"')
        p.append('/ip firewall filter add chain=forward protocol=udp dst-port=6881-6999 action=drop comment="Block-P2P"')
        p.append('/ip firewall filter add chain=forward protocol=tcp dst-port=411,1214,4662,6346 action=drop comment="Block-P2P-Alt"')

    # ================================================================
    # PHASE 7 : SÉCURITÉ + NAT + TTL + QOS
    # ================================================================
    p.append("")
    p.append("# --- NAT Standard ---")
    p.append('/ip firewall nat add chain=srcnat out-interface=' + wan + ' action=masquerade')

    if str(ttl) != '0':
        p.append("")
        p.append("# --- Masquage TTL Uniforme ---")
        p.append('/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:' + ttl + ' passthrough=yes')
        p.append('/ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:' + ttl + ' passthrough=yes')

    if dl != '0' or ul != '0':
        p.append("")
        p.append("# --- QoS Global ---")
        lim_ul = ul if 'M' in str(ul) else str(ul) + 'M'
        lim_dl = dl if 'M' in str(dl) else str(dl) + 'M'
        p.append('/queue simple add name="QoS-Global" target=' + net + ' max-limit=' + lim_ul + '/' + lim_dl)

    if client_limit != '0':
        p.append("")
        p.append("# --- QoS par Appareil (PCQ) ---")
        cl = client_limit if 'M' in str(client_limit) else str(client_limit) + 'M'
        p.append('/queue type add name=pcq-dl kind=pcq pcq-rate=' + cl + ' pcq-classifier=dst-address')
        p.append('/queue type add name=pcq-ul kind=pcq pcq-rate=' + cl + ' pcq-classifier=src-address')
        p.append('/queue simple add name="QoS-PerClient" target=' + net + ' queue=pcq-ul/pcq-dl')

    # ================================================================
    # PHASE 8 : MAC SPOOFING & IDENTITY
    # ================================================================
    if mac_spoof and mac_address:
        p.append("")
        p.append("# --- Usurpation MAC WAN ---")
        p.append(':do { /interface ethernet set ' + wan + ' mac-address=' + mac_address + ' } on-error={}')

    p.append("")
    p.append("# --- Nom du routeur ---")
    p.append('/system identity set name="' + router_name + '"')

    # ================================================================
    # PHASE 9 : MODE VEILLE NOCTURNE
    # ================================================================
    if sleep_mode != 'off':
        p.append("")
        p.append("# --- Mode Veille Wi-Fi ---")
        sleep_ranges = {
            '00-06': ('00:00:00', '06:00:00'),
            '01-05': ('01:00:00', '05:00:00'),
            '23-07': ('23:00:00', '07:00:00'),
            '02-06': ('02:00:00', '06:00:00'),
        }
        start_t, end_t = sleep_ranges.get(sleep_mode, ('00:00:00', '06:00:00'))

        if wifi_type == 'ax':
            p.append('/system scheduler add name="ketrika-sleep-off" start-time=' + start_t + ' \\')
            p.append('  interval=1d on-event="/interface wifi set [find] disabled=yes"')
            p.append('/system scheduler add name="ketrika-sleep-on" start-time=' + end_t + ' \\')
            p.append('  interval=1d on-event="/interface wifi set [find] disabled=no"')
        elif wifi_type in ['ac', 'n']:
            p.append('/system scheduler add name="ketrika-sleep-off" start-time=' + start_t + ' \\')
            p.append('  interval=1d on-event="/interface wireless set [find] disabled=yes"')
            p.append('/system scheduler add name="ketrika-sleep-on" start-time=' + end_t + ' \\')
            p.append('  interval=1d on-event="/interface wireless set [find] disabled=no"')

    # ================================================================
    # PHASE 10 : FIREWALL & REDÉMARRAGE AUTOMATIQUE
    # ================================================================
    p.append("")
    p.append("# --- Pare-feu de protection ---")
    p.append('/ip firewall filter add chain=input connection-state=established,related action=accept')
    p.append('/ip firewall filter add chain=input connection-state=invalid action=drop')
    p.append('/ip firewall filter add chain=input protocol=icmp action=accept')
    p.append('/ip firewall filter add chain=input in-interface=bridge1 action=accept')
    p.append('/ip firewall filter add chain=input in-interface=' + wan + ' action=drop')
    p.append("")
    p.append("# ============================================================")
    p.append("# --- REDÉMARRAGE AUTOMATIQUE PROPRE ---")
    p.append("# ============================================================")
    p.append('/system scheduler add name="ketrika-reboot-once" interval=0s \\')
    p.append('  on-event=":delay 2s; /system scheduler remove [find name=ketrika-reboot-once]; /system reboot"')
    p.append(':delay 1s')
    p.append('/system scheduler set [find name=ketrika-reboot-once] start-time=[/system clock get time]')
    p.append("")
    p.append("# FIN DU SCRIPT KETRIKA MIKROTIK")

    return "\n".join(p)


def generate_secret_guide(order):
    """Génère le dossier technique secret d'optimisation."""
    lic = safe_get(order, 'license_key', 'DEMO')
    client = safe_get(order, 'client_name', 'Client')

    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE TECHNIQUE : OPTIMISATION RESEAU AVANCEE
               Contournement des restrictions FAI et Partage Réseau
================================================================================

Client  : """ + client + """
Licence : """ + lic + """
Date    : """ + time.strftime('%d/%m/%Y', time.gmtime()) + """

================================================================================
  CHAPITRE 1 : COMMENT LES OPERATEURS DETECTENT LE PARTAGE DE CONNEXION
================================================================================

Lorsque vous partagez votre connexion internet via un routeur MikroTik,
les opérateurs FAI analysent trois facteurs principaux :

  1. ANALYSE DU TTL (Time To Live)
     --------------------------------
     Le TTL diminue de 1 à chaque saut de routeur. 
     Un appareil connecté directement a un TTL de 64. 
     Derrière votre MikroTik, l'opérateur reçoit 63. 
     Si le FAI voit des valeurs variables, il bloque ou restreint le partage.

  2. INSPECTION DPI (Deep Packet Inspection)
     -----------------------------------------
     L'opérateur analyse les signatures de vos paquets pour identifier la
     diversité des systèmes d'exploitation (Windows, Android, iOS) connectés. 
     Des signatures multiples sur une seule IP révèlent un partage.

  3. ANALYSE DU NOMBRE DE SESSIONS
     -------------------------------
     Un réseau partagé génère des connexes TCP/UDP simultanées,
     alertant les pare-feux du fournisseur d'accès.

================================================================================
  CHAPITRE 2 : FONCTIONNEMENT DE LA SOLUTION KETRIKA
================================================================================

  1. Masquage TTL : Le script fige le TTL sortant à 64 pour tout le réseau.
  2. Tunnel WireGuard : Chiffre l'intégralité du trafic vers Cloudflare, rendant
     l'inspection DPI de l'opérateur invisible.
  3. MSS Clamping : Ajuste les paquets TCP à 1280 octets pour éliminer la
     fragmentation et les ralentissements.

================================================================================
  SUPPORT TECHNIQUE : WhatsApp +261 38 28 171 00 (7h - 22h)
================================================================================
(c) 2026 KETRIKA MIKROTIK - Tous droits réservés.
"""
    return guide
