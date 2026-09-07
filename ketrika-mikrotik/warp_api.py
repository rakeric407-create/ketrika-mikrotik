import requests
import subprocess
import base64
import os

def generer_cles_wireguard():
    """Génère une paire de clés WireGuard"""
    try:
        # Génération avec la commande wg (Linux)
        private_key = subprocess.check_output(['wg', 'genkey']).decode().strip()
        public_key = subprocess.check_output(['wg', 'pubkey'], 
                                             input=private_key.encode()).decode().strip()
        return private_key, public_key
    except:
        # Fallback : génération pure Python
        from nacl.public import PrivateKey
        priv = PrivateKey.generate()
        private_key = base64.b64encode(bytes(priv)).decode()
        public_key = base64.b64encode(bytes(priv.public_key)).decode()
        return private_key, public_key

def enregistrer_warp(public_key):
    """Enregistre un nouveau compte Cloudflare WARP"""
    url = "https://api.cloudflareclient.com/v0a2158/reg"
    headers = {
        "User-Agent": "okhttp/3.12.1",
        "Content-Type": "application/json",
        "CF-Client-Version": "a-6.11-2223"
    }
    data = {
        "key": public_key,
        "install_id": "",
        "fcm_token": "",
        "tos": "2021-07-27T00:00:00.000Z",
        "model": "PC",
        "serial_number": "",
        "locale": "en_US"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "client_ip_v4": result["config"]["interface"]["addresses"]["v4"],
                "client_ip_v6": result["config"]["interface"]["addresses"]["v6"],
                "peer_public_key": result["config"]["peers"][0]["public_key"],
                "endpoint": result["config"]["peers"][0]["endpoint"]["host"],
                "token": result["token"],
                "id": result["id"]
            }
    except Exception as e:
        print(f"Erreur WARP : {e}")
    return {"success": False}

def creer_config_warp_complete():
    """Crée une configuration WARP complète et unique"""
    private_key, public_key = generer_cles_wireguard()
    warp_data = enregistrer_warp(public_key)
    
    if not warp_data["success"]:
        # Configuration de secours
        return {
            "private_key": private_key,
            "public_key": public_key,
            "client_ip": "172.16.0.2",
            "peer_public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
            "endpoint": "engage.cloudflareclient.com:2408"
        }
    
    return {
        "private_key": private_key,
        "public_key": public_key,
        "client_ip": warp_data["client_ip_v4"],
        "peer_public_key": warp_data["peer_public_key"],
        "endpoint": warp_data["endpoint"]
    }