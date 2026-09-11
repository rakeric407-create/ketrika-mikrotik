import os
import base64
import secrets
import requests

CF_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
WARP_ENDPOINTS = [("162.159.192.1", 2408), ("162.159.193.1", 2408), ("188.114.96.1", 2408), ("188.114.97.1", 2408)]

def curve25519_scalarmult(scalar):
    scalar = bytearray(scalar)
    scalar[0] &= 248
    scalar[31] &= 127
    scalar[31] |= 64
    x1 = 9
    x2, z2 = 1, 0
    x3, z3 = x1, 1
    swap = 0
    for t in reversed(range(255)):
        k_t = (scalar[t >> 3] >> (t & 7)) & 1
        swap ^= k_t
        if swap:
            x2, x3 = x3, x2
            z2, z3 = z3, z2
        swap = k_t
        A = (x2 + z2) % (2**255 - 19)
        AA = (A * A) % (2**255 - 19)
        B = (x2 - z2) % (2**255 - 19)
        BB = (B * B) % (2**255 - 19)
        E = (AA - BB) % (2**255 - 19)
        C = (x3 + z3) % (2**255 - 19)
        D = (x3 - z3) % (2**255 - 19)
        DA = (D * A) % (2**255 - 19)
        CB = (C * B) % (2**255 - 19)
        x3 = ((DA + CB) ** 2) % (2**255 - 19)
        z3 = (x1 * ((DA - CB) ** 2)) % (2**255 - 19)
        x2 = (AA * BB) % (2**255 - 19)
        z2 = (E * (AA + 121665 * E % (2**255 - 19))) % (2**255 - 19)
    if swap:
        x2, x3 = x3, x2
        z2, z3 = z3, z2
    return (x2 * pow(z2, 2**255 - 21, 2**255 - 19)) % (2**255 - 19)

def generate_wireguard_keys():
    private_key = secrets.token_bytes(32)
    public_key_int = curve25519_scalarmult(private_key)
    public_key = public_key_int.to_bytes(32, "little")
    return {
        "private_key": base64.b64encode(private_key).decode(),
        "public_key": base64.b64encode(public_key).decode()
    }

def register_warp(public_key):
    headers = {"User-Agent": "okhttp/3.12.1"}
    data = {"key": public_key}
    try:
        r = requests.post("https://api.cloudflareclient.com/v0a2158/reg", headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            j = r.json()
            return {"success": True, "ipv4": j.get("config", {}).get("client_id", "172.16.0.2")}
        else:
            return {"success": False, "ipv4": ""}
    except Exception:
        return {"success": False, "ipv4": ""}

def safe_get(obj, key, default=""):
    try:
        return getattr(obj, key, default) or default
    except Exception:
        return default

def ros_escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')

def generate_script(order):
    from database import get_model_info, generate_router_name, generate_random_mac
    lines = []
    lines.append(':do { /ip firewall filter add chain=input protocol=tcp dst-port=8291 action=accept comment="Winbox" } on-error={}')
    lines.append(':do { /ip dhcp-server remove [find] } on-error={}')
    lines.append(':do { /ip firewall filter remove [find] } on-error={}')
    lines.append(':do { /interface wireguard remove [find] } on-error={}')
    lines.append(':do { /ip hotspot remove [find] } on-error={}')
    lines.append(':do { /ip dns static remove [find comment="ketrika"] } on-error={}')
    lines.append(':do { /interface bridge add name=bridge1 } on-error={}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=ether2 } on-error={}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=ether3 } on-error={}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=ether4 } on-error={}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=ether5 } on-error={}')
    lines.append(f':do {{ /ip address add address={ros_escape(order.lan_gateway)}/24 interface=bridge1 }} on-error={{}}')
    lines.append(f':do {{ /ip pool add name=dhcp_pool ranges={ros_escape(order.dhcp_pool)} }} on-error={{}}')
    lines.append(f':do {{ /ip dhcp-server add name=dhcp1 interface=bridge1 address-pool=dhcp_pool }} on-error={{}}')
    lines.append(f':do {{ /ip dhcp-server network add address={ros_escape(order.lan_network)} gateway={ros_escape(order.lan_gateway)} }} on-error={{}}')
    lines.append(':do { /ip dns set use-doh-server=https://cloudflare-dns.com/dns-query verify-doh-cert=yes servers=1.1.1.1,1.0.0.1 } on-error={}')
    if order.mac_spoof and order.mac_address:
        lines.append(f':do {{ /interface ethernet set {ros_escape(order.wan_interface)} mac-address={ros_escape(order.mac_address)} }} on-error={{}}')
    lines.append(f':do {{ /ip dhcp-client add interface={ros_escape(order.wan_interface)} disabled=no }} on-error={{}}')
    lines.append(f':do {{ /interface wifi add name=wifi1 ssid={ros_escape(order.ssid)} password={ros_escape(order.wifi_password)} }} on-error={{}}')
    lines.append(f':do {{ /interface wireless add name=wlan1 ssid={ros_escape(order.ssid)} password={ros_escape(order.wifi_password)} }} on-error={{}}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=wifi1 } on-error={}')
    lines.append(':do { /interface bridge port add bridge=bridge1 interface=wlan1 } on-error={}')
    if order.plan_type in ["warp", "hotspot"]:
        lines.append(':do { /interface wireguard add name=wg-secure listen-port=13231 mtu=1280 } on-error={}')
        lines.append(f':do {{ /interface wireguard peers add interface=wg-secure public-key={CF_PUBLIC_KEY} endpoint-address=162.159.192.1 endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25s }} on-error={{}}')
        lines.append(':do { /ip route add dst-address=0.0.0.0/0 gateway=wg-secure routing-table=via-secure } on-error={}')
        lines.append(':do { /ip firewall mangle add chain=prerouting in-interface=bridge1 dst-address=!192.168.0.0/16 action=mark-routing new-routing-mark=via-secure } on-error={}')
        lines.append(':do { /ip firewall nat add chain=srcnat out-interface=wg-secure action=masquerade } on-error={}')
    lines.append(f':do {{ /ip firewall mangle add chain=prerouting action=change-ttl new-ttl=set:{ros_escape(order.ttl_value)} }} on-error={{}}')
    lines.append(f':do {{ /ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:{ros_escape(order.ttl_value)} }} on-error={{}}')
    if order.dl_limit and order.ul_limit:
        lines.append(f':do {{ /queue simple add name="QoS" target={ros_escape(order.lan_network)} max-limit={ros_escape(order.ul_limit)}/{ros_escape(order.dl_limit)} }} on-error={{}}')
    lines.append(f':do {{ /system identity set name={ros_escape(order.router_name)} }} on-error={{}}')
    if order.sleep_mode and order.sleep_mode != "off":
        lines.append(f':do {{ /system scheduler add name="sleep" start-time={ros_escape(order.sleep_mode.split("-")[0])}:00 interval=1d on-event="/interface disable wifi1;/interface disable wlan1" }} on-error={{}}')
    lines.append(':do { /ip firewall filter add chain=input connection-state=established action=accept } on-error={}')
    lines.append(':do { /ip firewall filter add chain=input connection-state=invalid action=drop } on-error={}')
    lines.append(':
