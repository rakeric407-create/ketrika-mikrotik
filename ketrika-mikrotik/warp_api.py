# warp_api.py - KETRIKA MIKROTIK Script Generator
import secrets


def format_limit(value):
    if value in ('nolimit', '0', ''):
        return '0'
    return value


def generate_full_script(order):
    from database import MIKROTIK_MODELS

    info = MIKROTIK_MODELS.get(order.mikrotik_model, {'ports': 5, 'wifi': True, 'wifi5g': False})
    ports = info['ports']
    wifi = info['wifi']
    wifi5g = info.get('wifi5g', False)
    wan = order.wan_interface
    gw = order.lan_gateway
    net = order.lan_network
    pool = order.dhcp_pool
    ttl = order.ttl_value
    dl = format_limit(order.dl_limit)
    ul = format_limit(order.ul_limit)

    lan_ports = [f"ether{i}" for i in range(2, ports + 1)]

    bp = ""
    for p in lan_ports:
        bp += f":do {{ /interface bridge port add bridge=bridge1 interface={p} }} on-error={{}}\n"
    if wifi:
        bp += ":do { /interface bridge port add bridge=bridge1 interface=wlan1 } on-error={}\n"
    if wifi5g:
        bp += ":do { /interface bridge port add bridge=bridge1 interface=wlan2 } on-error={}\n"

    wcfg = ""
    if wifi:
        wcfg += f"""
:do {{
    /interface wifi set wlan1 configuration.mode=ap configuration.ssid="{order.ssid}" \\
        security.authentication-types=wpa2-psk security.passphrase="{order.wifi_password}" \\
        channel.frequency=2412 channel.width=20/40mhz-Ce disabled=no
}} on-error={{ :log warning "WiFi 2.4G skip" }}
"""
    if wifi5g:
        wcfg += f"""
:do {{
    /interface wifi set wlan2 configuration.mode=ap configuration.ssid="{order.ssid}-5G" \\
        security.authentication-types=wpa2-psk security.passphrase="{order.wifi_password}" \\
        channel.frequency=5180 channel.width=20/40/80mhz-Ceee disabled=no
}} on-error={{ :log warning "WiFi 5G skip" }}
"""

    if dl == '0':
        rl = """
# === BANDE PASSANTE : ILLIMITEE ===
:log info "KETRIKA: No bandwidth limit applied"
"""
    else:
        rl = f"""
# === BANDE PASSANTE PAR CLIENT ===
:do {{
    /queue type add kind=pcq name=pcq-dl-ketrika pcq-classifier=dst-address pcq-rate={dl}
    /queue type add kind=pcq name=pcq-ul-ketrika pcq-classifier=src-address pcq-rate={ul}
    /queue simple add name="KETRIKA-Limit" target={net} \\
        queue=pcq-ul-ketrika/pcq-dl-ketrika comment="[KETRIKA] Bandwidth"
}} on-error={{ :log warning "Queue exists" }}
"""

    warp = ""
    if order.plan_type in ('warp', 'hotspot'):
        warp = f"""
# =============================================
# TUNNEL SECURISE CLOUDFLARE (Bypass DPI)
# =============================================
:do {{
    /interface wireguard add listen-port=13231 mtu=1420 name=wg-secure \\
        comment="[KETRIKA] Tunnel"
    /ip address add address=10.0.0.2/24 interface=wg-secure network=10.0.0.0
    /ip firewall mangle add chain=prerouting in-interface=bridge1 \\
        dst-address=!{net} action=mark-routing new-routing-mark=via-secure \\
        passthrough=yes comment="[KETRIKA] Mark tunnel"
    /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade \\
        comment="[KETRIKA] NAT tunnel"
    /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes
}} on-error={{ :log warning "WARP config skip" }}
"""

    hotspot = ""
    if order.plan_type == 'hotspot':
        rl_hs = f"rate-limit={ul}/{dl}" if dl != '0' else ""
        hotspot = f"""
# =============================================
# HOTSPOT WIFI ZONE
# =============================================
:do {{
    /ip hotspot profile add dns-name="wifi.ketrika.mg" \\
        hotspot-address={gw} login-by=http-chap,http-pap name=hsprof-ketrika
    /ip hotspot add address-pool=pool-lan disabled=no interface=bridge1 \\
        name=hotspot-ketrika profile=hsprof-ketrika
    /ip hotspot user profile add name=1heure {rl_hs} shared-users=1 session-timeout=1h
    /ip hotspot user profile add name=1jour {rl_hs} shared-users=2 session-timeout=1d
    /ip hotspot user profile add name=1semaine {rl_hs} shared-users=3 session-timeout=7d
    /ip hotspot user profile add name=1mois {rl_hs} shared-users=3 session-timeout=30d
    /ip hotspot user add name=admin password=admin123 profile=1mois
}} on-error={{ :log warning "Hotspot skip" }}
"""
        if order.pppoe_enabled:
            rl_ppp = f"rate-limit={ul}/{dl}" if dl != '0' else ""
            hotspot += f"""
# PPPoE SERVER
:do {{
    /ip pool add name=pool-pppoe ranges=192.168.99.10-192.168.99.250
    /ppp profile add dns-server=1.1.1.1,8.8.8.8 local-address=192.168.99.1 \\
        name=pppoe-ketrika {rl_ppp} remote-address=pool-pppoe
    /interface pppoe-server server add default-profile=pppoe-ketrika disabled=no \\
        interface=bridge1 one-session-per-host=yes service-name=KETRIKA
    /ppp secret add name=client1 password=pass123 profile=pppoe-ketrika service=pppoe
}} on-error={{ :log warning "PPPoE skip" }}
"""
        if order.voucher_enabled:
            hotspot += "\n/ip hotspot user\n"
            for _ in range(10):
                c = secrets.token_hex(4).upper()
                hotspot += f'add name=V-{c} password={c} profile=1heure comment="Voucher 1H"\n'

    rsc = f"""# =============================================
# KETRIKA MIKROTIK - Configuration Automatique
# Plan : {order.plan_type.upper()}
# Modele : {order.mikrotik_model} ({ports} ports)
# Licence : {order.license_key}
# Compatible RouterOS v7 - Safe Mode
# =============================================

:log info "KETRIKA: Demarrage configuration..."
:delay 2s

# === 1. BRIDGE ===
:do {{
    /interface bridge add name=bridge1 protocol-mode=none comment="KETRIKA LAN"
}} on-error={{ :log info "Bridge exists" }}
:delay 1s

# === 2. PORTS ===
{bp}
:delay 1s

# === 3. IP LAN ===
:do {{
    /ip address add address={gw}/24 interface=bridge1 comment="KETRIKA GW"
}} on-error={{ :log info "IP exists" }}

# === 4. DHCP WAN ===
:do {{
    /ip dhcp-client add interface={wan} disabled=no add-default-route=yes \\
        use-peer-dns=no comment="KETRIKA WAN"
}} on-error={{ :log info "DHCP WAN exists" }}
:delay 2s

# === 5. DHCP LAN ===
:do {{
    /ip pool add name=pool-lan ranges={pool}
    /ip dhcp-server add address-pool=pool-lan interface=bridge1 name=dhcp-lan disabled=no
    /ip dhcp-server network add address={net} gateway={gw} \\
        dns-server=1.1.1.1,8.8.8.8 netmask=24
}} on-error={{ :log info "DHCP LAN exists" }}

# === 6. DNS ===
/ip dns set allow-remote-requests=yes servers=1.1.1.1,1.0.0.1,8.8.8.8

# === 7. NAT ===
:do {{
    /ip firewall nat add chain=srcnat out-interface={wan} action=masquerade \\
        comment="[KETRIKA] NAT"
}} on-error={{ :log info "NAT exists" }}

# === 8. WIFI ===
{wcfg}
:delay 1s

# === 9. OPTIMISATION & BYPASS RESEAU ===
:do {{
    /ip firewall mangle add chain=postrouting out-interface={wan} action=change-ttl \\
        new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL OUT"
    /ip firewall mangle add chain=prerouting in-interface={wan} action=change-ttl \\
        new-ttl=set:{ttl} passthrough=no comment="[KETRIKA] TTL IN"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp tcp-flags=syn \\
        action=change-mss new-mss=clamp-to-pmtu passthrough=yes comment="[KETRIKA] MSS"
    /ip firewall mangle add chain=forward out-interface={wan} protocol=tcp \\
        action=change-mss new-mss=1360 passthrough=yes comment="[KETRIKA] MSS Norm"
    /ip firewall filter add chain=forward out-interface={wan} protocol=icmp action=drop \\
        comment="[KETRIKA] ICMP Filter"
    /ip firewall filter add chain=output out-interface={wan} protocol=icmp action=drop \\
        comment="[KETRIKA] ICMP Out"
    /ip firewall filter add chain=input connection-state=established,related action=accept
    /ip firewall filter add chain=input connection-state=invalid action=drop
    /ip firewall filter add chain=forward connection-state=established,related action=accept
    /ip firewall filter add chain=forward connection-state=invalid action=drop
    /ip firewall filter add chain=forward in-interface=bridge1 out-interface={wan} action=accept
}} on-error={{ :log warning "Firewall skip" }}
{warp}{hotspot}{rl}
# =============================================
:log info "KETRIKA: Configuration terminee !"
:put "======================================"
:put "  KETRIKA CONFIG - DONE"
:put "  Licence: {order.license_key}"
:put "======================================"
"""
    return rsc
