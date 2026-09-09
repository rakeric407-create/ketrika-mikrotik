#!/usr/bin/env python3
"""
KETRIKA MIKROTIK - Moteur de génération de scripts RouterOS v7
Version Anti-Déconnexion + Multi-Modèles + Options Avancées
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
    Générateur principal de scripts RouterOS v7.
    GARANTIE : Ne coupe JAMAIS la connexion Winbox pendant l'exécution.
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
    has_5ghz = info.get('has_5ghz', False)

    # Générer MAC et nom si nécessaire
    if not router_name:
        router_name = generate_router_name(lic)
    if mac_spoof and not mac_address:
        mac_address = generate_random_mac()

    # Clés WARP
    keys = generate_wireguard_keys()
    warp_reg = register_warp(keys['public_key'])
    warp_ip = warp_reg['ipv4']
    endpoints = ["162.159.192.1", "162.159.193.1", "188.114.96.1", "188.114.97.1"]
    ports = [500, 853, 4500, 2408]
    endpoint_ip = random.choice(endpoints)
    endpoint_port = random.choice(ports)

    p = []

    # ================================================================
    # PHASE 1 : EN-TÊTE + NETTOYAGE SÉCURISÉ (ne touche PAS aux IP/bridge)
    # ================================================================
    p.append("# ============================================================")
    p.append("# KETRIKA MIKROTIK - CONFIGURATION AUTOMATIQUE ROUTEROS v7")
    p.append("# LICENCE : " + lic)
    p.append("# MODELE  : " + model)
    p.append("# DATE    : " + time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime()))
    p.append("# ============================================================")
    p.append("# IMPORTANT : Ce script ne coupe PAS votre connexion Winbox.")
    p.append("# Le routeur redémarrera automatiquement à la fin.")
    p.append("# ============================================================")
    p.append("")
    p.append("# --- Nettoyage des anciens schedulers KETRIKA ---")
    p.append('/system scheduler remove [find name~"ketrika"]')
    p.append('/system scheduler remove [find name~"br-"]')
    p.append('/system scheduler remove [find name~"reboot"]')
    p.append('/system scheduler remove [find name~"sleep"]')
    p.append("")
    p.append("# --- Nettoyage sécurisé (ne supprime PAS les IP ni le bridge) ---")
    p.append("/ip firewall filter remove [find]")
    p.append("/ip firewall nat remove [find]")
    p.append("/ip firewall mangle remove [find]")
    p.append("/queue simple remove [find]")
    p.append("/ip dhcp-server remove [find]")
    p.append("/ip dhcp-server network remove [find]")
    p.append("/ip pool remove [find]")
    p.append("/ip route remove [find where dst-address=0.0.0.0/0]")
    p.append('/ip dns set servers=""')
    p.append("/interface wireguard remove [find]")
    p.append("/routing table remove [find]")
    p.append("/routing rule remove [find]")
    p.append("/ip hotspot remove [find]")
    p.append("/ip hotspot profile remove [find]")
    p.append("/ip hotspot user remove [find]")
    p.append("/ip hotspot user profile remove [find]")

    # ================================================================
    # PHASE 2 : BRIDGE + PORTS (sans destruction)
    # ================================================================
    p.append("")
    p.append("# --- Bridge LAN (créé uniquement s'il n'existe pas) ---")
    p.append(':if ([:len [/interface bridge find name=bridge1]] = 0) do={')
    p.append('  /interface bridge add name=bridge1 comment="LAN-KETRIKA"')
    p.append('}')
    p.append("")
    p.append("# --- Attribution des ports Ethernet au bridge ---")
    p.append(':foreach iface in=[/interface ethernet find] do={')
    p.append('  :local ifname [/interface ethernet get $iface name]')
    p.append('  :if ($ifname != "' + wan + '") do={')
    p.append('    :if ([:len [/interface bridge port find interface=$ifname]] = 0) do={')
    p.append('      /interface bridge port add bridge=bridge1 interface=$ifname')
    p.append('    }')
    p.append('  }')
    p.append('}')

    # ================================================================
    # PHASE 3 : IP + DHCP + DNS
    # ================================================================
    p.append("")
    p.append("# --- Client DHCP WAN ---")
    p.append('/ip dhcp-client add interface=' + wan + ' disabled=no add-default-route=yes use-peer-dns=no comment="WAN-KETRIKA"')
    p.append("")
    p.append("# --- IP Passerelle LAN (ajoutée si inexistante) ---")
    p.append(':if ([:len [/ip address find address~"' + gw.split('.')[0] + '.' + gw.split('.')[1] + '"]] = 0) do={')
    p.append('  /ip address add address=' + gw + '/24 interface=bridge1 comment="LAN-KETRIKA"')
    p.append('}')
    p.append("")
    p.append("# --- Serveur DHCP LAN ---")
    p.append('/ip pool add name=pool-lan ranges=' + pool)
    p.append('/ip dhcp-server add name=dhcp-lan interface=bridge1 address-pool=pool-lan lease-time=1d disabled=no')
    p.append('/ip dhcp-server network add address=' + net + ' gateway=' + gw + ' dns-server=' + gw)
    p.append("")
    p.append("# --- DNS Chiffré Cloudflare DoH ---")
    p.append('/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1 use-doh-server=https://cloudflare-dns.com/dns-query')

    # ================================================================
    # PHASE 4 : WI-FI AUTO-ACTIVATION (multi-modèles)
    # ================================================================
    if wifi_type == 'ax' and wifi_iface:
        p.append("")
        p.append("# --- Wi-Fi 6 (AX) - Activation automatique ---")
        p.append(':if ([:len [/interface wifi find]] > 0) do={')
        p.append('  /interface wifi set [find] configuration.ssid="' + ssid + '" configuration.country=madagascar \\')
        p.append('    security.authentication-types=wpa2-psk,wpa3-psk security.passphrase="' + wifi_pass + '" disabled=no')
        p.append('  :foreach wif in=[/interface wifi find] do={')
        p.append('    :local wname [/interface wifi get $wif name]')
        p.append('    :if ([:len [/interface bridge port find interface=$wname]] = 0) do={')
        p.append('      /interface bridge port add bridge=bridge1 interface=$wname')
        p.append('    }')
        p.append('  }')
        p.append('}')
    elif wifi_type in ['ac', 'n'] and wifi_iface:
        p.append("")
        p.append("# --- Wi-Fi 5/4 (AC/N) - Activation automatique ---")
        p.append(':if ([:len [/interface wireless find]] > 0) do={')
        p.append('  /interface wireless security-profiles set [find default=yes] mode=dynamic-keys \\')
        p.append('    authentication-types=wpa2-psk wpa2-pre-shared-key="' + wifi_pass + '"')
        p.append('  /interface wireless set [find] mode=ap-bridge ssid="' + ssid + '" \\')
        p.append('    frequency=auto security-profile=default disabled=no')
        p.append('  :foreach wif in=[/interface wireless find] do={')
        p.append('    :local wname [/interface wireless get $wif name]')
        p.append('    :if ([:len [/interface bridge port find interface=$wname]] = 0) do={')
        p.append('      /interface bridge port add bridge=bridge1 interface=$wname')
        p.append('    }')
        p.append('  }')
        p.append('}')

    # ================================================================
    # PHASE 5 : VPN WARP (Packs 50K et 80K)
    # ================================================================
    if plan in ['warp', 'hotspot']:
        p.append("")
        p.append("# ============================================================")
        p.append("# --- TUNNEL VPN WIREGUARD CLOUDFLARE WARP ---")
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
        p.append("# --- Routage Avancé v7 ---")
        p.append('/routing table add name=via-secure fib')
        p.append('/routing rule add src-address=' + net + ' action=lookup table=via-secure')
        p.append('/routing rule add dst-address=' + net + ' action=lookup-only-in-table table=main')
        p.append('/ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure')
        p.append("")
        p.append("# --- NAT VPN + Anti-Fuite DNS ---")
        p.append('/ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade')
        p.append('/ip firewall nat add chain=dstnat protocol=udp dst-port=53 in-interface=bridge1 action=redirect')
        p.append('/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 in-interface=bridge1 action=redirect')
        p.append("")
        p.append("# --- MSS Clamping Anti-DPI ---")
        p.append('/ip firewall mangle add chain=forward out-interface=wg-secure protocol=tcp tcp-flags=syn \\')
        p.append('  action=change-mss new-mss=1280 passthrough=yes')

    # ================================================================
    # PHASE 6 : HOTSPOT CAPTIF (Pack 80K uniquement)
    # ================================================================
    if plan == 'hotspot':
        p.append("")
        p.append("# ============================================================")
        p.append("# --- PORTAIL CAPTIF HOTSPOT WIFI ZONE ---")
        p.append("# ============================================================")
        p.append('/ip dns static add name=wifi.ketrika.mg address=' + gw)
        p.append('/ip hotspot profile add name=ketrika-hs hotspot-address=' + gw + ' \\')
        p.append('  dns-name=wifi.ketrika.mg login-by=http-pap,cookie \\')
        p.append('  http-cookie-lifetime=1d use-radius=no')
        p.append('/ip hotspot add name=hotspot-ketrika interface=bridge1 \\')
        p.append('  profile=ketrika-hs address-pool=pool-lan disabled=no')
        p.append("")
        p.append("# --- Profils de vitesse ---")
        p.append('/ip hotspot user profile add name="1heure" rate-limit="2M/5M" session-timeout=1h shared-users=1')
        p.append('/ip hotspot user profile add name="1jour" rate-limit="5M/10M" session-timeout=1d shared-users=2')
        p.append('/ip hotspot user profile add name="1semaine" rate-limit="5M/10M" session-timeout=7d shared-users=2')
        p.append('/ip hotspot user profile add name="1mois" rate-limit="10M/20M" session-timeout=30d shared-users=3')
        p.append("")
        p.append("# --- 10 Vouchers automatiques ---")
        for _ in range(10):
            vc = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            p.append('/ip hotspot user add name="' + vc + '" password="' + vc + '" profile="1jour" comment="Ticket-KETRIKA"')
        p.append("")
        p.append("# --- Pare-feu Anti-Torrent ---")
        p.append('/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6999 action=drop comment="Block-P2P"')
        p.append('/ip firewall filter add chain=forward protocol=udp dst-port=6881-6999 action=drop comment="Block-P2P"')
        p.append('/ip firewall filter add chain=forward protocol=tcp dst-port=411,1214,4662,6346 action=drop comment="Block-P2P-Alt"')

    # ================================================================
    # PHASE 7 : SÉCURITÉ + NAT + TTL + QoS
    # ================================================================
    p.append("")
    p.append("# --- NAT Internet Standard ---")
    p.append('/ip firewall nat add chain=srcnat out-interface=' + wan + ' action=masquerade')

    if str(ttl) != '0':
        p.append("")
        p.append("# --- Masquage TTL Anti-Partage ---")
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
        p.append("# --- Limitation par client individuel ---")
        cl = client_limit if 'M' in str(client_limit) else str(client_limit) + 'M'
        p.append('/queue type add name=pcq-dl kind=pcq pcq-rate=' + cl + ' pcq-classifier=dst-address')
        p.append('/queue type add name=pcq-ul kind=pcq pcq-rate=' + cl + ' pcq-classifier=src-address')
        p.append('/queue simple add name="QoS-PerClient" target=' + net + ' queue=pcq-ul/pcq-dl')

    # ================================================================
    # PHASE 8 : MAC SPOOFING + NOM DU ROUTEUR
    # ================================================================
    if mac_spoof and mac_address:
        p.append("")
        p.append("# --- Changement MAC WAN (Anti-détection FAI) ---")
        p.append('/interface ethernet set ' + wan + ' mac-address=' + mac_address)

    p.append("")
    p.append("# --- Nom du routeur ---")
    p.append('/system identity set name="' + router_name + '"')

    # ================================================================
    # PHASE 9 : MODE VEILLE NOCTURNE
    # ================================================================
    if sleep_mode != 'off':
        p.append("")
        p.append("# --- Mode Veille Nocturne Wi-Fi ---")
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
    # PHASE 10 : FIREWALL DE BASE + REBOOT SÉCURISÉ
    # ================================================================
    p.append("")
    p.append("# --- Firewall de base ---")
    p.append('/ip firewall filter add chain=input connection-state=established,related action=accept')
    p.append('/ip firewall filter add chain=input connection-state=invalid action=drop')
    p.append('/ip firewall filter add chain=input protocol=icmp action=accept')
    p.append('/ip firewall filter add chain=input in-interface=bridge1 action=accept')
    p.append('/ip firewall filter add chain=input in-interface=' + wan + ' action=drop')
    p.append("")
    p.append("# ============================================================")
    p.append("# --- REBOOT SÉCURISÉ (Exécution UNIQUE, sans boucle) ---")
    p.append("# ============================================================")
    p.append('/system scheduler add name="ketrika-reboot-once" interval=0s \\')
    p.append('  on-event=":delay 2s; /system scheduler remove [find name=ketrika-reboot-once]; /system reboot"')
    p.append(':delay 1s')
    p.append('/system scheduler set [find name=ketrika-reboot-once] start-time=[/system clock get time]')
    p.append("")
    p.append("# FIN DU SCRIPT KETRIKA MIKROTIK")

    return "\n".join(p)


def generate_secret_guide(order):
    """
    Génère le contenu du guide secret anti-Starlink pour les packs 50K et 80K.
    Retourne une chaîne de texte formatée.
    """
    lic = safe_get(order, 'license_key', 'DEMO')
    client = safe_get(order, 'client_name', 'Client')

    guide = """
================================================================================
         KETRIKA MIKROTIK - GUIDE SECRET : OPTIMISATION RESEAU AVANCEE
                    Contournement des restrictions FAI / Starlink
================================================================================

Client  : """ + client + """
Licence : """ + lic + """
Date    : """ + time.strftime('%d/%m/%Y', time.gmtime()) + """

================================================================================
  CHAPITRE 1 : COMMENT STARLINK ET LES FAI DETECTENT LE PARTAGE DE CONNEXION
================================================================================

Quand vous partagez votre connexion internet (Starlink, 4G, 5G, fibre) via un
routeur MikroTik, votre fournisseur d'acces utilise 3 methodes principales pour
detecter que plusieurs appareils sont connectes derriere un seul abonnement :

  1. ANALYSE DU TTL (Time To Live)
     --------------------------------
     Chaque paquet reseau contient une valeur TTL qui diminue de 1 a chaque
     passage par un routeur. Votre telephone envoie un TTL de 64. Quand ce
     paquet traverse votre MikroTik, le TTL devient 63. L'operateur voit :
       - Appareil 1 : TTL = 64 (direct)
       - Appareil 2 : TTL = 63 (derriere un routeur)
       - Appareil 3 : TTL = 63 (derriere un routeur)
     Conclusion de l'operateur : "Il y a un routeur, on coupe !"

  2. INSPECTION DPI (Deep Packet Inspection)
     -----------------------------------------
     L'operateur analyse le contenu des paquets pour identifier :
       - Les differents systemes d'exploitation (Windows, Android, iOS)
       - Les differents navigateurs (Chrome, Safari, Firefox)
       - Les signatures uniques de chaque appareil
     Si 5 appareils differents utilisent la meme IP publique = partage detecte.

  3. ANALYSE DES CONNEXIONS SIMULTANEES
     ------------------------------------
     Starlink et les FAI 4G/5G surveillent le nombre de connexions TCP/UDP
     simultanees. Un seul telephone fait ~50 connexions. Si l'operateur voit
     500 connexions simultanees sur une seule IP, il sait qu'il y a partage.

================================================================================
  CHAPITRE 2 : COMMENT NOTRE SOLUTION RESOUT CHAQUE PROBLEME
================================================================================

  PROBLEME 1 : Detection TTL
  SOLUTION   : Masquage TTL uniforme
     Notre script force TOUS les paquets sortants a avoir exactement le meme
     TTL (64). L'operateur ne peut plus distinguer les appareils :
       /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64

  PROBLEME 2 : Inspection DPI
  SOLUTION   : Tunnel chiffre Cloudflare WARP (WireGuard)
     Tout votre trafic passe par un tunnel chiffre de bout en bout. L'operateur
     ne voit qu'un seul flux de donnees chiffrees vers les serveurs Cloudflare.
     Il est IMPOSSIBLE pour lui de voir ce qu'il y a a l'interieur :
       /interface wireguard -> Cloudflare WARP -> Internet

  PROBLEME 3 : Connexions simultanees
  SOLUTION   : MSS Clamping + NAT unique
     Le MSS Clamping ajuste la taille des paquets TCP pour eviter la
     fragmentation dans le tunnel. Le NAT masquerade fait apparaitre tous
     vos appareils comme une seule source :
       /ip firewall mangle add chain=forward out-interface=wg-secure \\
         protocol=tcp tcp-flags=syn action=change-mss new-mss=1280

================================================================================
  CHAPITRE 3 : CONSEILS D'UTILISATION AVANCES
================================================================================

  [!] REGLE D'OR : Ne modifiez JAMAIS les regles Firewall Mangle apres
      l'installation. Elles sont la cle de voute de la protection.

  [*] STARLINK :
      - Branchez le cable Ethernet Starlink directement sur le Port 1 (ether1)
        de votre MikroTik.
      - Desactivez le routeur Starlink (mode "bypass" dans l'application
        Starlink) pour eviter le double NAT.
      - Si vous utilisez le routeur Starlink, branchez-le sur ether1 et
        configurez-le en mode "bridge".

  [*] 4G / 5G (Telma, Orange, Airtel) :
      - Si vous utilisez un modem 4G USB, branchez-le sur le port USB du
        MikroTik et configurez l'interface LTE.
      - Si vous utilisez un modem 4G Ethernet, branchez-le sur ether1.

  [*] LIMITATION DE DEBIT PAR CLIENT :
      - Si vous avez choisi la limitation par client, chaque appareil connecte
        au WiFi sera limite individuellement.
      - Pour modifier la limite : Winbox > Queues > Simple > QoS-PerClient

  [*] MODE VEILLE NOCTURNE :
      - Le WiFi se desactive automatiquement pendant les heures de veille.
      - Cela economise de l'energie et reduit les risques de detection
        pendant la nuit quand personne n'utilise la connexion.

  [*] CHANGEMENT MAC :
      - L'adresse MAC de votre interface WAN a ete modifiee pour ressembler
        a un appareil classique (telephone, ordinateur).
      - Cela empeche l'operateur d'identifier votre routeur MikroTik.

================================================================================
  CHAPITRE 4 : EN CAS DE PROBLEME
================================================================================

  1. Le VPN ne se connecte pas :
     -> Redemarrez le routeur (System > Reboot dans Winbox)
     -> Attendez 2 minutes que le tunnel WireGuard se retablisse

  2. Le debit est lent :
     -> Verifiez que le MSS Clamping est actif (IP > Firewall > Mangle)
     -> Verifiez que le MTU du WireGuard est bien 1280

  3. L'operateur a coupe la connexion :
     -> Changez la valeur TTL (essayez 65 ou 128 au lieu de 64)
     -> Activez le changement MAC si ce n'est pas deja fait
     -> Contactez notre support WhatsApp

  4. Le WiFi ne fonctionne pas apres installation :
     -> Verifiez dans Winbox : Interfaces > wifi1 (ou wlan1) > Enabled
     -> Verifiez que l'interface est bien dans le bridge1

================================================================================
  SUPPORT TECHNIQUE KETRIKA MIKROTIK
  WhatsApp : +261 38 28 171 00
  Horaires : 7h - 22h (heure de Madagascar)
================================================================================

Ce document est confidentiel et destine uniquement a l'usage du client.
Toute reproduction ou distribution est interdite.
(c) 2026 KETRIKA MIKROTIK - Tous droits reserves.
"""
    return guide
