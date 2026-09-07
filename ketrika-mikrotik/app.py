from flask import Flask, request, Response, render_template_string, session, redirect, url_for, send_file
from database import *
from warp_api import creer_config_warp_complete
import sqlite3
import secrets
import string
import random
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

init_db()

def init_commandes_table():
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_nom TEXT, telephone TEXT, formule TEXT, montant REAL,
        reference_paiement TEXT, statut TEXT DEFAULT 'EN_ATTENTE',
        cle_generee TEXT, date_commande TEXT
    )''')
    conn.commit()
    conn.close()

init_commandes_table()

NUMERO_PAIEMENT = "038 28 171 00"

TARIFS_MODULES = {
    "base": {"nom": "🛡️ Pack Essentiel", "prix": 10000, "desc": "Optimisation TTL + DNS Sécurisé + Wi-Fi Dual Band"},
    "warp": {"nom": "🚀 Pack Blindé (VPN)", "prix": 20000, "desc": "Essentiel + Tunnel Chiffré WireGuard Global"},
    "hotspot": {"nom": "🎫 Pack Wi-Fi Zone", "prix": 30000, "desc": "Blindé + Portail Hotspot + Contrôle Débit"},
    "pro": {"nom": "🏢 Pack Pro WISP", "prix": 50000, "desc": "Solution intégrale + PPPoE + QoS + DNS Perso"}
}

MODELES_MIKROTIK = [
    "hAP ax2 (Dual Band Wi-Fi 6)", "hAP ax3 (Dual Band Wi-Fi 6)",
    "hAP ac2 (Dual Band)", "hAP ac3 (Dual Band)",
    "mANTBox ax 15s (Wi-Fi 6)", "mANTBox 19s", "LHG 5", "SXTsq", "hAP lite",
    "RB750Gr3 (hEX)", "RB760iGS (hEX S)", "RB2011", "RB3011", "RB4011", "RB1100 (13 Ports)",
    "CCR1009", "CCR2004", "CCR2116",
    "Chateau LTE/5G", "Autre RouterOS v7"
]

BANDWIDTH_PROFILES = {
    "illimite": {"nom": "⚡ ILLIMITÉ", "down": "0", "up": "0", "desc": "Vitesse maximale sans limite"},
    "ultra": {"nom": "🚀 ULTRA (10M/5M)", "down": "10M", "up": "5M", "desc": "10 Mbps ↓ / 5 Mbps ↑"},
    "rapide": {"nom": "⭐ RAPIDE (5M/2M)", "down": "5M", "up": "2M", "desc": "5 Mbps ↓ / 2 Mbps ↑"},
    "standard": {"nom": "📶 STANDARD (2M/1M)", "down": "2M", "up": "1M", "desc": "2 Mbps ↓ / 1 Mbps ↑"},
    "eco": {"nom": "🔒 ÉCONOMIQUE (1M/512K)", "down": "1M", "up": "512k", "desc": "1 Mbps ↓ / 512 Kbps ↑"},
    "custom": {"nom": "🎯 SUR MESURE", "down": "3M", "up": "1M", "desc": "Valeurs personnalisées"}
}

HTML_BASE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>KETRIKA MIKROTIK PRO • Solution Réseau</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;900&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #030712;
            --card-bg: #0b1120;
            --accent-cyan: #00f2fe;
            --accent-green: #10b981;
            --accent-purple: #8b5cf6;
            --accent-orange: #f59e0b;
            --accent-gold: #fbbf24;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        @keyframes float { 0%, 100% { transform: translateY(0); opacity: 0.4; } 50% { transform: translateY(-20px); opacity: 0.8; } }
        @keyframes pulse-glow { 0%, 100% { text-shadow: 0 0 15px rgba(0, 242, 254, 0.5); } 50% { text-shadow: 0 0 30px rgba(0, 242, 254, 0.9); } }
        @keyframes border-flow { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
        @keyframes slide-in { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes toast-in { from { transform: translateX(-120%); } to { transform: translateX(0); } }
        @keyframes toast-out { from { transform: translateX(0); } to { transform: translateX(-120%); } }
        @keyframes shine { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        @keyframes star-twinkle { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.1); opacity: 0.85; } }
        
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background: var(--bg-dark); color: var(--text-main); 
            min-height: 100vh; padding: 18px; overflow-x: hidden;
        }
        body::before {
            content: ''; position: fixed; inset: 0;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.08), transparent 40%),
                radial-gradient(circle at 85% 70%, rgba(16, 185, 129, 0.06), transparent 45%),
                radial-gradient(circle at 50% 95%, rgba(139, 92, 246, 0.06), transparent 35%);
            z-index: -2;
        }
        .particle { position: fixed; width: 4px; height: 4px; background: var(--accent-cyan); border-radius: 50%; opacity: 0.3; animation: float 6s ease-in-out infinite; z-index: -1; }
        
        .container { max-width: 880px; margin: auto; animation: slide-in 0.6s ease-out; }
        
        .top-nav {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 18px; padding: 8px 16px; background: rgba(11, 17, 32, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 30px; backdrop-filter: blur(15px);
        }
        .lang-btn {
            background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan); border: 1px solid rgba(0, 242, 254, 0.3);
            padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; cursor: pointer;
        }
        .lang-btn:hover { background: var(--accent-cyan); color: #000; }
        
        .header { text-align: center; padding: 20px 0 25px; }
        .header h1 { 
            font-family: 'Space Grotesk', sans-serif; font-size: 34px; font-weight: 900; 
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-green), var(--accent-purple), var(--accent-cyan)); 
            background-size: 300% 300%;
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
            letter-spacing: 2px; text-transform: uppercase;
            animation: border-flow 4s ease infinite, pulse-glow 2.5s ease-in-out infinite;
        }
        .header p { color: var(--text-muted); font-size: 13px; margin-top: 6px; }
        
        .card { 
            background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.05); 
            border-radius: 18px; padding: 24px; margin-bottom: 18px; 
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6); backdrop-filter: blur(20px);
            position: relative; overflow: hidden; transition: all 0.3s ease;
        }
        .card::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
            background: linear-gradient(90deg, transparent, var(--accent-cyan), var(--accent-green), var(--accent-purple), transparent);
            background-size: 200% 100%; animation: border-flow 3s linear infinite;
        }
        .card:hover { transform: translateY(-2px); }
        
        .card-title { 
            font-family: 'Space Grotesk', sans-serif; font-size: 15px; color: var(--accent-cyan); 
            margin-bottom: 14px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
            display: flex; align-items: center; gap: 8px;
        }

        /* SECTION AVANTAGES (Remplace le comparateur) */
        .advantages-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 10px; }
        .adv-box { 
            background: linear-gradient(135deg, #101524, #0d1220); 
            padding: 16px; border-radius: 12px; text-align: center; 
            border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s ease;
            position: relative; overflow: hidden;
        }
        .adv-box:hover { border-color: var(--accent-cyan); transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0, 242, 254, 0.15); }
        .adv-icon { font-size: 28px; margin-bottom: 8px; display: block; }
        .adv-title { font-family: 'Space Grotesk'; font-size: 13px; color: var(--accent-cyan); font-weight: 700; margin-bottom: 5px; }
        .adv-desc { font-size: 11px; color: var(--text-muted); line-height: 1.4; }
        
        label { display: block; font-size: 11px; font-weight: 700; color: var(--text-muted); margin-top: 14px; text-transform: uppercase; letter-spacing: 1px; }
        input, select { 
            width: 100%; padding: 13px 15px; margin-top: 5px; 
            background: #111827; border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 10px; color: #fff; font-size: 14px; transition: all 0.3s ease; 
        }
        input:focus, select:focus { outline: none; border-color: var(--accent-cyan); box-shadow: 0 0 15px rgba(0, 242, 254, 0.2); }

        .btn-primary { 
            width: 100%; padding: 15px; margin-top: 18px; 
            background: linear-gradient(135deg, #00f2fe, #4facfe); 
            color: #030712; border: none; border-radius: 10px; 
            font-size: 14px; font-weight: 800; cursor: pointer; 
            transition: all 0.3s ease; font-family: 'Space Grotesk'; 
            letter-spacing: 1px; text-transform: uppercase;
            position: relative; overflow: hidden; text-decoration: none; display: inline-block; text-align: center;
        }
        .btn-primary::before {
            content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            transition: left 0.6s ease;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0, 242, 254, 0.5); }
        .btn-primary:hover::before { left: 200%; }
        .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: #fff; }

        .btn-copy {
            background: linear-gradient(135deg, #8b5cf6, #6d28d9); color: #fff;
            padding: 12px; border-radius: 10px; border: none; font-weight: 700;
            cursor: pointer; width: 100%; font-family: 'Space Grotesk'; text-transform: uppercase;
            letter-spacing: 1px; margin-top: 10px; transition: 0.3s; font-size: 13px;
        }
        .btn-copy.copied { background: #10b981; }

        .plan-selector { display: grid; grid-template-columns: 1fr; gap: 10px; margin-top: 8px; }
        .plan-option { 
            background: #101524; border: 1px solid rgba(255, 255, 255, 0.05); 
            padding: 14px 16px; border-radius: 12px; cursor: pointer; 
            display: flex; justify-content: space-between; align-items: center; transition: 0.3s;
        }
        .plan-option:hover { border-color: var(--accent-cyan); transform: translateX(4px); }
        .plan-option input { width: 18px; height: 18px; accent-color: var(--accent-cyan); }

        .bandwidth-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }
        .bw-option { background: #101524; border: 2px solid rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 10px; cursor: pointer; text-align: center; transition: 0.3s; }
        .bw-option:hover { border-color: var(--accent-purple); }
        .bw-option input { display: none; }
        .bw-option:has(input:checked) { border-color: var(--accent-cyan); background: linear-gradient(135deg, rgba(0, 242, 254, 0.1), rgba(16, 185, 129, 0.05)); }
        .bw-content b { display: block; font-size: 12px; color: #fff; }
        .bw-content small { color: var(--text-muted); font-size: 10px; }
        .custom-bw { display: none; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
        .custom-bw.active { display: grid; }

        .payment-banner { 
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.03)); 
            border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; 
            padding: 18px; margin-top: 15px; text-align: center; 
        }
        .payment-phone { 
            font-family: 'Space Grotesk'; font-size: 28px; color: #f59e0b; 
            margin: 6px 0; font-weight: 800; letter-spacing: 2px; 
            text-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
        }

        .terminal-box { 
            background: #040711; border: 1px solid var(--accent-green); 
            color: var(--accent-green); padding: 15px; border-radius: 10px; 
            font-family: 'Courier New', monospace; font-size: 12px; 
            word-break: break-all; margin-top: 10px; line-height: 1.5;
        }

        .badge { background: rgba(0, 242, 254, 0.08); color: var(--accent-cyan); padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; border: 1px solid rgba(0, 242, 254, 0.3); }
        .alert { padding: 12px 15px; border-radius: 10px; margin-bottom: 12px; font-size: 12px; line-height: 1.5; }
        .alert-success { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #a7f3d0; }
        .alert-error { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5; }
        .alert-warning { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #fde68a; }

        .feature-box { background: #101524; padding: 15px; border-radius: 12px; margin-top: 10px; line-height: 2; font-size: 12px; border-left: 4px solid var(--accent-cyan); }
        .wifi-box { background: #101524; border: 1px dashed rgba(0, 242, 254, 0.3); padding: 15px; border-radius: 12px; margin-top: 12px; }

        /* FAQ */
        .faq-item { border-bottom: 1px solid rgba(255,255,255,0.05); padding: 12px 0; }
        .faq-item:last-child { border-bottom: none; }
        .faq-question { font-weight: 700; color: #fff; font-size: 13px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .faq-answer { color: var(--text-muted); font-size: 12px; line-height: 1.6; margin-top: 8px; display: none; padding-right: 20px; }
        .faq-item.active .faq-answer { display: block; animation: slide-in 0.3s ease-out; }
        .faq-item.active .faq-toggle { transform: rotate(180deg); color: var(--accent-cyan); }
        .faq-toggle { transition: 0.3s; color: var(--accent-cyan); font-size: 16px; }

        /* AVIS CLIENTS */
        .reviews-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 10px; }
        .review-card { 
            background: linear-gradient(135deg, #101524, #0d1220); 
            padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); 
            position: relative;
        }
        .stars { color: var(--accent-gold); font-size: 14px; letter-spacing: 2px; margin-bottom: 6px; animation: star-twinkle 3s ease-in-out infinite; }
        .review-text { font-size: 12px; color: var(--text-muted); line-height: 1.5; font-style: italic; margin-bottom: 8px; }
        .review-author { font-size: 11px; color: var(--accent-cyan); font-weight: 700; }
        .review-location { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
        .global-rating { 
            display: flex; align-items: center; justify-content: center; gap: 15px; 
            padding: 15px; background: linear-gradient(135deg, rgba(251, 191, 36, 0.1), rgba(245, 158, 11, 0.05)); 
            border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 12px; margin-bottom: 12px;
        }
        .rating-number { font-family: 'Space Grotesk'; font-size: 32px; font-weight: 900; color: var(--accent-gold); }
        .rating-info b { color: #fff; font-size: 14px; display: block; }
        .rating-info small { color: var(--text-muted); font-size: 11px; }

        /* TOAST FOMO */
        #fomo-toast {
            position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            background: rgba(11, 17, 32, 0.95); border: 1px solid var(--accent-green);
            padding: 12px 16px; border-radius: 12px; color: #fff; font-size: 11px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(16, 185, 129, 0.2);
            backdrop-filter: blur(15px); display: none; align-items: center; gap: 10px; max-width: 300px;
        }
        #fomo-toast.show { display: flex; animation: toast-in 0.5s ease-out; }
        #fomo-toast.hide { animation: toast-out 0.5s ease-in forwards; }

        /* WHATSAPP */
        .whatsapp-float {
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            background: linear-gradient(135deg, #25D366, #128C7E); color: #fff;
            padding: 12px 18px; border-radius: 50px; font-weight: 800; font-size: 13px;
            box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4); text-decoration: none;
            display: flex; align-items: center; gap: 6px; font-family: 'Space Grotesk';
            transition: 0.3s;
        }
        .whatsapp-float:hover { transform: scale(1.08); }

        table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
        table th, table td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; }
        table th { color: var(--accent-cyan); font-family: 'Space Grotesk'; font-weight: 700; }
        
        .footer { text-align: center; color: var(--text-muted); opacity: 0.8; margin: 30px 0 15px; font-size: 11px; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="particle" style="top: 12%; left: 6%;"></div>
    <div class="particle" style="top: 25%; left: 88%; animation-delay: 1.2s;"></div>
    <div class="particle" style="top: 45%; left: 12%; animation-delay: 2.4s;"></div>
    <div class="particle" style="top: 65%; left: 82%; animation-delay: 3.6s;"></div>
    <div class="particle" style="top: 85%; left: 22%; animation-delay: 4.8s;"></div>

    <a href="https://wa.me/261382817100?text=Bonjour%20KETRIKA%2C%20je%20souhaite%20optimiser%20mon%20MikroTik" target="_blank" class="whatsapp-float">
        💬 <span>WhatsApp</span>
    </a>

    <div id="fomo-toast">
        <div style="font-size:22px;">⚡</div>
        <div>
            <b id="fomo-name" style="color:var(--accent-green); display:block; font-size:12px;">Client à Antananarivo</b>
            <span id="fomo-action" style="color:var(--text-muted); font-size:11px;">Pack Wi-Fi Zone activé</span>
        </div>
    </div>

    <div class="container">
        <div class="top-nav">
            <span style="font-size:11px; color:var(--text-muted);">🚀 KETRIKA OS v2.6 • Madagascar</span>
            <button class="lang-btn" onclick="toggleLang()">🇲🇬 MG / 🇫🇷 FR</button>
        </div>

        <div class="header">
            <h1>⚡ KETRIKA MIKROTIK ⚡</h1>
            <p class="txt-fr">Solution Professionnelle d'Optimisation Réseau MikroTik</p>
            <p class="txt-mg" style="display:none;">Fitaovana matihanina hanatsarana ny MikroTik</p>
        </div>

        {{ content|safe }}

        <div class="footer">
            KETRIKA MIKROTIK PRO © 2026 • Ingénierie Réseau • 038 28 171 00
        </div>
    </div>

    <script>
        let currentLang = 'fr';
        function toggleLang() {
            currentLang = currentLang === 'fr' ? 'mg' : 'fr';
            document.querySelectorAll('.txt-fr').forEach(e => e.style.display = currentLang === 'fr' ? '' : 'none');
            document.querySelectorAll('.txt-mg').forEach(e => e.style.display = currentLang === 'mg' ? '' : 'none');
        }

        function copyText(elemId, btnId) {
            const text = document.getElementById(elemId).innerText;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.getElementById(btnId);
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ COPIÉ !';
                btn.classList.add('copied');
                setTimeout(() => { btn.innerHTML = originalText; btn.classList.remove('copied'); }, 2500);
            });
        }

        document.querySelectorAll('.faq-question').forEach(q => {
            q.addEventListener('click', () => q.parentElement.classList.toggle('active'));
        });

        const fakeSales = [
            { name: "Hery T. (Antananarivo)", action: "Pack Wi-Fi Zone activé" },
            { name: "Rasoa B. (Tamatave)", action: "Optimisation hAP ax2 réussie" },
            { name: "Mamy R. (Majunga)", action: "Pack Pro WISP déployé" },
            { name: "Toky A. (Diego)", action: "Tunnel VPN configuré" },
            { name: "Faly K. (Antsirabe)", action: "Configuration Wi-Fi terminée" },
            { name: "Nirina L. (Fianarantsoa)", action: "Routeur optimisé" }
        ];

        function showFomoToast() {
            const toast = document.getElementById('fomo-toast');
            if(!toast) return;
            const item = fakeSales[Math.floor(Math.random() * fakeSales.length)];
            document.getElementById('fomo-name').innerText = item.name;
            document.getElementById('fomo-action').innerText = item.action;
            toast.className = 'show';
            setTimeout(() => { toast.className = 'hide'; }, 5000);
        }
        setInterval(showFomoToast, 25000);
        setTimeout(showFomoToast, 4000);

        document.addEventListener('DOMContentLoaded', () => {
            const bwRadios = document.querySelectorAll('input[name="bandwidth"]');
            const customBw = document.getElementById('custom-bw-fields');
            if (bwRadios.length > 0 && customBw) {
                bwRadios.forEach(radio => {
                    radio.addEventListener('change', function() {
                        if (this.value === 'custom') customBw.classList.add('active');
                        else customBw.classList.remove('active');
                    });
                });
            }
        });
    </script>
</body>
</html>
"""

def render(content):
    return render_template_string(HTML_BASE, content=content)

def build_raw_script(cfg):
    plan = cfg["type"]
    opt = cfg.get("options", {})
    ssid = opt.get("ssid", "KETRIKA-NET")
    wifi_pass = opt.get("wifi_pass", "ketrika2025")
    dns_name = opt.get("dns_name", "ketrika.wifi")
    bw_down = opt.get("bw_down", "0")
    bw_up = opt.get("bw_up", "0")
    
    s = f"# KETRIKA MIKROTIK - {cfg['client']} ({cfg['modele']})\n# Pack : {plan.upper()}\n"
    
    s += '/ip firewall mangle remove [find comment="KETRIKA-TTL"]\n/ip firewall mangle add chain=postrouting action=change-ttl new-ttl=set:64 passthrough=yes comment="KETRIKA-TTL"\n'
    s += '/ip dns set use-doh-server="https://cloudflare-dns.com/dns-query" verify-doh-cert=no allow-remote-requests=yes\n/ip firewall nat remove [find comment="KETRIKA-DNS"]\n/ip firewall nat add chain=dstnat protocol=udp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n/ip firewall nat add chain=dstnat protocol=tcp dst-port=53 action=redirect to-ports=53 comment="KETRIKA-DNS"\n'
    s += '/ipv6 settings set disable-ipv6=yes\n'
    s += '/ip firewall filter remove [find comment="KETRIKA-P2P"]\n/ip firewall filter add chain=forward protocol=tcp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=udp dst-port=6881-6889 action=drop comment="KETRIKA-P2P"\n/ip firewall filter add chain=forward protocol=tcp tcp-flags=syn connection-limit=100,32 action=drop comment="KETRIKA-P2P"\n'
    
    s += f"""
:do {{
    /interface wifi security remove [find comment="KETRIKA-SEC"]
    /interface wifi security add name=ketrika-sec authentication-types=wpa2-psk,wpa3-psk passphrase="{wifi_pass}" comment="KETRIKA-SEC"
    /interface wifi configuration remove [find name="cfg-2ghz"]
    /interface wifi configuration add name=cfg-2ghz ssid="{ssid}" security=ketrika-sec chains=0,1 channel.band=2ghz-ax
    /interface wifi configuration remove [find name="cfg-5ghz"]
    /interface wifi configuration add name=cfg-5ghz ssid="{ssid}" security=ketrika-sec chains=0,1 channel.band=5ghz-ax channel.width=20/40/80mhz
    /interface wifi set [find channel.band~"2ghz" or name~"wifi2"] configuration=cfg-2ghz disabled=no
    /interface wifi set [find channel.band~"5ghz" or name~"wifi1"] configuration=cfg-5ghz disabled=no
    /interface wifi set [find] configuration.ssid="{ssid}" security=ketrika-sec disabled=no
}} on-error={{}};
:do {{
    /interface wireless security-profiles remove [find name="ketrika-sec"]
    /interface wireless security-profiles add name=ketrika-sec mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="{wifi_pass}"
    /interface wireless set [find] ssid="{ssid}" security-profile=ketrika-sec disabled=no
}} on-error={{}};
"""

    if plan in ["warp", "hotspot", "pro"] and cfg.get("warp_private"):
        s += f"""/interface wireguard remove [find name="warp-ketrika"]
/interface wireguard add name=warp-ketrika listen-port=51820 mtu=1280 private-key="{cfg['warp_private']}"
/interface wireguard peers remove [find interface="warp-ketrika"]
/interface wireguard peers add interface=warp-ketrika public-key="{cfg['warp_public']}" endpoint-address=engage.cloudflareclient.com endpoint-port=2408 allowed-address=0.0.0.0/0 persistent-keepalive=25
/ip address remove [find interface="warp-ketrika"]
/ip address add address={cfg['warp_ip']}/32 interface=warp-ketrika
/ip firewall nat remove [find comment="KETRIKA-WARP"]
/ip firewall nat add chain=srcnat out-interface=warp-ketrika action=masquerade comment="KETRIKA-WARP"
/ip route remove [find comment="KETRIKA-ROUTE"]
/ip route add dst-address=0.0.0.0/0 gateway=warp-ketrika distance=1 comment="KETRIKA-ROUTE"
"""

    if plan in ["hotspot", "pro"]:
        s += f"""/ip pool add name=ketrika-hs-pool ranges=10.5.50.10-10.5.50.254
/ip dhcp-server add name=ketrika-hs-dhcp interface=bridge address-pool=ketrika-hs-pool disabled=no
/ip hotspot profile add name=ketrika-hs hotspot-address=10.5.50.1 dns-name={dns_name}
/ip hotspot user profile add name=ketrika-hs-user rate-limit="{bw_up}/{bw_down}"
/ip hotspot add name=hs-ketrika interface=bridge address-pool=ketrika-hs-pool profile=ketrika-hs disabled=no
"""

    if plan == "pro":
        s += f"""/ip pool add name=ketrika-ppp-pool ranges=10.10.10.2-10.10.10.254
/ppp profile add name=ketrika-ppp local-address=10.10.10.1 remote-address=ketrika-ppp-pool dns-server=1.1.1.1 rate-limit="{bw_up}/{bw_down}"
/interface pppoe-server server add service-name=KETRIKA-NET interface=bridge default-profile=ketrika-ppp disabled=no
"""
    return s

@app.route("/")
def home():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    
    plans_html = ""
    for k, v in TARIFS_MODULES.items():
        checked = "checked" if k == "base" else ""
        plans_html += f"""
        <label class="plan-option" for="plan_{k}">
            <div>
                <b style="color:#fff; font-size:13px;">{v['nom']}</b>
                <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">{v['desc']}</div>
            </div>
            <div style="text-align:right;">
                <b style="color:var(--accent-green); font-size:15px; font-family:'Space Grotesk';">{v['prix']:,} Ar</b><br>
                <input type="radio" name="formule" id="plan_{k}" value="{k}" {checked}>
            </div>
        </label>
        """
    
    content = f"""
    <!-- SECTION AVANTAGES (Remplace le comparatif) -->
    <div class="card">
        <div class="card-title">💎 POURQUOI NOTRE SOLUTION EST EFFICACE</div>
        <div class="advantages-grid">
            <div class="adv-box">
                <span class="adv-icon">🔒</span>
                <div class="adv-title">Tunnel WireGuard</div>
                <div class="adv-desc">Chiffrement militaire ChaCha20 100% invisible</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">⚡</span>
                <div class="adv-title">Vitesse Native</div>
                <div class="adv-desc">Aucune perte de débit, latence ultra-faible</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">🌐</span>
                <div class="adv-title">DNS Cloudflare</div>
                <div class="adv-desc">Requêtes DoH sécurisées et anonymes</div>
            </div>
            <div class="adv-box">
                <span class="adv-icon">📶</span>
                <div class="adv-title">Wi-Fi Dual Band</div>
                <div class="adv-desc">2.4G + 5G optimisés canaux 80MHz</div>
            </div>
        </div>
    </div>

    <!-- NOTATION GLOBALE -->
    <div class="card">
        <div class="global-rating">
            <div class="rating-number">4.9</div>
            <div>
                <div class="stars">⭐⭐⭐⭐⭐</div>
                <div class="rating-info">
                    <b>Excellent</b>
                    <small>Basé sur 187 avis clients vérifiés</small>
                </div>
            </div>
        </div>
        
        <div class="reviews-grid">
            <div class="review-card">
                <div class="stars">⭐⭐⭐⭐⭐</div>
                <div class="review-text">"Configuration en 5 secondes, mon Wi-Fi tourne à pleine vitesse. Bravo l'équipe !"</div>
                <div class="review-author">Hery R.</div>
                <div class="review-location">📍 Antananarivo</div>
            </div>
            <div class="review-card">
                <div class="stars">⭐⭐⭐⭐⭐</div>
                <div class="review-text">"Le tunnel VPN fonctionne parfaitement, très stable. Meilleur investissement de l'année."</div>
                <div class="review-author">Boutique Rasoa</div>
                <div class="review-location">📍 Tamatave</div>
            </div>
            <div class="review-card">
                <div class="stars">⭐⭐⭐⭐⭐</div>
                <div class="review-text">"Support WhatsApp très réactif, ils ont configuré mon RB1100 à distance."</div>
                <div class="review-author">Mamy T.</div>
                <div class="review-location">📍 Majunga</div>
            </div>
        </div>
    </div>

    <!-- COMMANDE -->
    <div class="card">
        <div class="card-title">🛒 CHOISIR VOTRE CONFIGURATION</div>
        <form method="POST" action="/commander">
            <div class="plan-selector">{plans_html}</div>
            
            <div class="payment-banner">
                <b style="color:#f59e0b; font-size:12px; font-family:'Space Grotesk';">📱 MOBILE MONEY</b>
                <div style="font-size:12px; color:#fff; margin-top:3px;">Envoyez au numéro :</div>
                <div class="payment-phone">{NUMERO_PAIEMENT}</div>
                <small style="color:var(--text-muted); font-size:11px;">Mvola | Orange Money | Airtel Money</small>
            </div>

            <label>Nom complet :</label>
            <input type="text" name="nom" placeholder="Rakoto Jean" required>
            <label>Téléphone :</label>
            <input type="text" name="tel" placeholder="034 00 000 00" required>
            <label>Référence du paiement :</label>
            <input type="text" name="ref_paiement" placeholder="Code SMS de transaction" required>
            <button type="submit" class="btn-primary">ENVOYER LA COMMANDE</button>
        </form>
    </div>

    <!-- ACTIVATION -->
    <div class="card">
        <div class="card-title">🔐 ACTIVATION AVEC VOTRE CLÉ</div>
        <form method="POST" action="/login">
            <input type="text" name="licence" placeholder="KTR-XXXX-XXXX-XXXX" required style="text-transform:uppercase; letter-spacing:1.5px;">
            <button type="submit" class="btn-primary btn-success">DÉVERROUILLER LE GÉNÉRATEUR</button>
        </form>
    </div>

    <!-- FAQ ENRICHIE -->
    <div class="card">
        <div class="card-title">❓ QUESTIONS FRÉQUENTES</div>
        <div class="faq-item">
            <div class="faq-question"><span>Le tunnel VPN nécessite-t-il un abonnement mensuel ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer"><b style="color:var(--accent-green);">Non, absolument aucun abonnement !</b> Le tunnel WireGuard utilise le service Cloudflare WARP qui est <b>100% gratuit et illimité à vie</b>. Vous payez uniquement la configuration une seule fois, et le VPN fonctionne pour toujours sans frais mensuels.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Combien de temps prend l'installation ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Moins de <b>5 secondes chrono</b> ! Vous collez la commande générée dans Winbox Terminal, et tout s'applique automatiquement (TTL, DNS, VPN, Wi-Fi, Hotspot).</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Est-ce compatible avec tous les modèles MikroTik ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Oui, notre système est compatible avec <b>plus de 20 modèles</b> : hAP ax2/ax3, hAP ac2/ac3, RB750/760/2011/3011/4011/1100, CCR1009/2004/2116, mANTBox, LHG, SXTsq, Chateau et tous les autres RouterOS v7.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Quels sont les moyens de paiement ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Tous les Mobile Money de Madagascar : <b>Mvola, Orange Money, Airtel Money</b> au numéro <b>038 28 171 00</b>. Après validation, votre clé est envoyée par SMS en quelques minutes.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>Que faire en cas de problème ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Notre <b>support WhatsApp gratuit</b> est disponible 7j/7. Cliquez sur le bouton vert en bas à droite, ou appelez directement le 038 28 171 00. Notre équipe peut même vous configurer votre routeur à distance.</div>
        </div>
        <div class="faq-item">
            <div class="faq-question"><span>La clé de licence a-t-elle une durée limitée ?</span> <span class="faq-toggle">▼</span></div>
            <div class="faq-answer">Non, votre clé est <b>valide 1 an minimum</b> et vous permet de générer autant de configurations que vous voulez pour vos routeurs pendant cette période.</div>
        </div>
    </div>
    """
    return render(content)

@app.route("/commander", methods=["POST"])
def commander():
    nom = request.form.get("nom")
    tel = request.form.get("tel")
    formule = request.form.get("formule")
    ref = request.form.get("ref_paiement")
    montant = TARIFS_MODULES.get(formule, {}).get("prix", 10000)

    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("INSERT INTO commandes (client_nom, telephone, formule, montant, reference_paiement, date_commande) VALUES (?, ?, ?, ?, ?, ?)",
              (nom, tel, formule, montant, ref, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Commande enregistrée !</b></div>
        <p style="font-size:13px; line-height:1.6; color:var(--text-muted);">
            Merci <b style="color:#fff;">{nom}</b>. Votre commande pour <b style="color:#fff;">{TARIFS_MODULES[formule]['nom']}</b> ({montant:,} Ar) est validée.<br><br>
            Nous vérifions la référence <code style="color:var(--accent-cyan);">{ref}</code> et vous envoyons la clé par SMS au <b style="color:#fff;">{tel}</b>.
        </p>
        <a href="/" class="btn-primary">RETOUR</a>
    </div>
    """
    return render(content)

@app.route("/login", methods=["POST"])
def login():
    cle = request.form.get("licence", "").strip().upper()
    result = verifier_licence(cle)
    if not result or not result["valide"]:
        return render('<div class="card"><div class="alert alert-error">❌ Clé incorrecte !</div><a href="/" class="btn-primary">Retour</a></div>')
    
    session["authenticated"] = True
    session["licence"] = cle
    session["client"] = result["client"]
    session["type_abo"] = result["type"]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    
    plan_key = session.get("type_abo", "base")
    plan_info = TARIFS_MODULES.get(plan_key, TARIFS_MODULES["base"])
    modeles_opt = "".join([f'<option value="{m}">{m}</option>' for m in MODELES_MIKROTIK])

    feat_html = "<div>✅ Optimisation TTL Avancée</div><div>✅ DNS Sécurisé DoH Cloudflare</div><div>✅ Blocage IPv6 & P2P</div><div>✅ Wi-Fi Dual Band Haute Vitesse</div>"
    dns_input_html = ""
    bandwidth_html = ""
    
    if plan_key in ["warp", "hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Tunnel Chiffré WireGuard (100% gratuit à vie)</div>"
    if plan_key in ["hotspot", "pro"]:
        feat_html += "<div style='color:var(--accent-green);'>✅ Portail Captif Hotspot</div>"
        dns_input_html = """
        <label>🔗 Adresse Hotspot (Page de connexion) :</label>
        <input type="text" name="dns_name" value="wifizone.wifi" required>
        <small style="color:var(--text-muted); font-size:10px; display:block; margin-top:3px;">Ex: wifizone.wifi, monwifi.net</small>
        """
        
        bw_options_html = ""
        for k, v in BANDWIDTH_PROFILES.items():
            checked = "checked" if k == "illimite" else ""
            bw_options_html += f"""
            <label class="bw-option" for="bw_{k}">
                <input type="radio" name="bandwidth" id="bw_{k}" value="{k}" {checked}>
                <div class="bw-content"><b>{v['nom']}</b><small>{v['desc']}</small></div>
            </label>
            """
        
        bandwidth_html = f"""
        <div class="wifi-box" style="border-color: rgba(139, 92, 246, 0.4);">
            <div style="font-size:12px; font-weight:bold; color:var(--accent-purple); margin-bottom:8px;">📊 BANDE PASSANTE PAR CLIENT</div>
            <div class="bandwidth-selector">{bw_options_html}</div>
            <div id="custom-bw-fields" class="custom-bw">
                <div>
                    <label style="margin-top:0;">📥 Download</label>
                    <input type="text" name="custom_down" value="3M" placeholder="5M">
                </div>
                <div>
                    <label style="margin-top:0;">📤 Upload</label>
                    <input type="text" name="custom_up" value="1M" placeholder="2M">
                </div>
            </div>
        </div>
        """
    
    if plan_key == "pro":
        feat_html += "<div style='color:var(--accent-green);'>✅ Serveur PPPoE + QoS Bandwidth</div>"

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <span class="badge">{plan_info['nom']}</span>
        <a href="/logout" style="color:#ef4444; font-size:11px; text-decoration:none;">Déconnexion</a>
    </div>

    <div class="card">
        <div class="card-title">⚙️ GÉNÉRATEUR - {session['client']}</div>
        <form method="POST" action="/generate">
            <label>1. Modèle MikroTik :</label>
            <select name="modele" required>{modeles_opt}</select>

            <label>2. Nom du client / Installation :</label>
            <input type="text" name="client_final" placeholder="Boutique_Rasoa" required>

            <div class="wifi-box">
                <div style="font-size:12px; font-weight:bold; color:var(--accent-cyan); margin-bottom:8px;">📶 CONFIGURATION WI-FI (2.4G + 5G)</div>
                <label>Nom du Wi-Fi (SSID) :</label>
                <input type="text" name="ssid" value="KETRIKA-NET" required>
                <label>Mot de passe :</label>
                <input type="text" name="wifi_pass" value="ketrika2025" required>
                {dns_input_html}
            </div>
            
            {bandwidth_html}

            <label>3. Fonctionnalités incluses :</label>
            <div class="feature-box">{feat_html}</div>

            <button type="submit" class="btn-primary">🚀 GÉNÉRER LE SCRIPT</button>
        </form>
    </div>
    """
    return render(content)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("authenticated"):
        return redirect(url_for("home"))
    
    modele = request.form.get("modele")
    plan_key = session.get("type_abo", "base")
    client_final = request.form.get("client_final").replace(" ", "_")
    ssid = request.form.get("ssid", "KETRIKA-NET")
    wifi_pass = request.form.get("wifi_pass", "ketrika2025")
    dns_name = request.form.get("dns_name", "ketrika.wifi")
    
    bw_choice = request.form.get("bandwidth", "illimite")
    if bw_choice == "custom":
        bw_down = request.form.get("custom_down", "3M")
        bw_up = request.form.get("custom_up", "1M")
        bw_display = f"{bw_up}/{bw_down} (Sur mesure)"
    else:
        bw_profile = BANDWIDTH_PROFILES.get(bw_choice, BANDWIDTH_PROFILES["illimite"])
        bw_down = bw_profile["down"]
        bw_up = bw_profile["up"]
        bw_display = bw_profile["nom"]
    
    options = {"ssid": ssid, "wifi_pass": wifi_pass, "dns_name": dns_name, "bw_down": bw_down, "bw_up": bw_up}
    warp_data = creer_config_warp_complete() if plan_key in ["warp", "hotspot", "pro"] else {}
    config_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    sauvegarder_config(session["licence"], client_final, modele, plan_key, options, warp_data, config_id)
    incrementer_utilisation(session["licence"])
    
    host = request.host_url.replace("http://", "https://")
    online_cmd = f'/tool fetch url="{host}config/{config_id}.rsc" mode=https dst-path=ketrika.rsc; /import file-name=ketrika.rsc'
    
    cfg = get_config_by_id(config_id)
    raw_s = build_raw_script(cfg).replace('"', '\\"').replace('\n', ' ')
    one_liner = f'/system script add name=ketrika_run source="{raw_s}"; /system script run ketrika_run; /system script remove ketrika_run'

    bw_info = f"<br>📊 <b>Débit :</b> {bw_display}" if plan_key in ["hotspot", "pro"] else ""

    content = f"""
    <div class="card">
        <div class="alert alert-success"><b>✅ Script prêt pour : {client_final}</b></div>
        <div class="alert alert-warning">
            📶 <b>Wi-Fi :</b> {ssid} | 🔑 {wifi_pass}{bw_info}<br>
            💡 <i>Connectez Winbox via l'adresse MAC pour éviter la déconnexion.</i>
        </div>

        <div class="card-title">MÉTHODE 1 : COMMANDE UNIQUE</div>
        <div class="terminal-box" id="cmd-oneliner">{one_liner}</div>
        <button class="btn-copy" id="btn-cp1" onclick="copyText('cmd-oneliner', 'btn-cp1')">📋 COPIER LA COMMANDE</button>

        <hr style="border-color:rgba(255,255,255,0.06); margin:20px 0;">

        <div class="card-title">MÉTHODE 2 : FICHIER .RSC</div>
        <a href="/download/{config_id}.rsc" class="btn-primary btn-success">📥 TÉLÉCHARGER KETRIKA.RSC</a>

        <hr style="border-color:rgba(255,255,255,0.06); margin:20px 0;">

        <div class="card-title">MÉTHODE 3 : ROUTEUR EN LIGNE</div>
        <div class="terminal-box" id="cmd-online">{online_cmd}</div>
        <button class="btn-copy" id="btn-cp2" onclick="copyText('cmd-online', 'btn-cp2')" style="background:#374151;">📋 COPIER</button>

        <a href="/dashboard" class="btn-primary" style="margin-top:20px;">🔄 NOUVELLE CONFIGURATION</a>
    </div>
    """
    return render(content)

@app.route("/download/<config_id>.rsc")
def download_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("Configuration introuvable", mimetype="text/plain")
    script_content = build_raw_script(cfg)
    mem_file = io.BytesIO()
    mem_file.write(script_content.encode('utf-8'))
    mem_file.seek(0)
    return send_file(mem_file, mimetype="text/plain", as_attachment=True, download_name="ketrika.rsc")

@app.route("/config/<config_id>.rsc")
def get_config(config_id):
    cfg = get_config_by_id(config_id)
    if not cfg:
        return Response("# Invalide", mimetype="text/plain")
    return Response(build_raw_script(cfg), mimetype="text/plain")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if verifier_admin(request.form.get("username"), request.form.get("password")):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
    return render('<div class="card"><div class="card-title">🔐 ADMIN</div><form method="POST"><input type="text" name="username" placeholder="admin" required><input type="password" name="password" placeholder="mot de passe" required><button type="submit" class="btn-primary">CONNEXION</button></form></div>')

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE statut='EN_ATTENTE' ORDER BY id DESC")
    commandes = c.fetchall()
    conn.close()

    rows_html = ""
    for cmd in commandes:
        rows_html += f"""
        <tr>
            <td><b>{cmd[1]}</b><br><small>{cmd[2]}</small></td>
            <td>{cmd[3].upper()}<br><b>{cmd[4]:,} Ar</b></td>
            <td><code>{cmd[5]}</code></td>
            <td>
                <form method="POST" action="/admin/valider/{cmd[0]}">
                    <button type="submit" class="btn-primary" style="padding:6px 10px; font-size:11px; margin:0;">⚡ VALIDER</button>
                </form>
            </td>
        </tr>
        """

    return render(f"""
    <div class="card">
        <div class="card-title">📋 COMMANDES ({len(commandes)})</div>
        <table><tr><th>Client</th><th>Pack</th><th>Réf</th><th>Action</th></tr>
        {rows_html if rows_html else '<tr><td colspan="4" style="text-align:center;">Aucune commande</td></tr>'}
        </table>
        <a href="/admin/creer" class="btn-primary" style="margin-top:15px;">➕ CRÉER UNE CLÉ</a>
    </div>
    """)

@app.route("/admin/valider/<int:cmd_id>", methods=["POST"])
def admin_valider(cmd_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    
    conn = sqlite3.connect("ketrika.db")
    c = conn.cursor()
    c.execute("SELECT * FROM commandes WHERE id=?", (cmd_id,))
    cmd = c.fetchone()
    if cmd:
        cle = creer_licence(cmd[1], cmd[2], cmd[3], cmd[4])
        c.execute("UPDATE commandes SET statut='VALIDE', cle_generee=? WHERE id=?", (cle, cmd_id))
        conn.commit()
    conn.close()
    
    return render(f"""
    <div class="card">
        <div class="alert alert-success">✅ Validé pour {cmd[1]} !</div>
        <div class="card-title">CLÉ POUR {cmd[2]} :</div>
        <div class="terminal-box">{cle}</div>
        <a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">RETOUR</a>
    </div>
    """)

@app.route("/admin/creer", methods=["GET", "POST"])
def admin_creer():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    if request.method == "POST":
        cle = creer_licence(request.form.get("client"), request.form.get("tel"), request.form.get("type"), TARIFS_MODULES[request.form.get("type")]["prix"])
        return render(f'<div class="card"><div class="alert alert-success">Clé créée :</div><div class="terminal-box">{cle}</div><a href="/admin/dashboard" class="btn-primary" style="margin-top:15px;">Dashboard</a></div>')
    return render("""<div class="card"><div class="card-title">Créer une Clé</div><form method="POST"><input type="text" name="client" placeholder="Nom" required><input type="text" name="tel" placeholder="Tél" required><select name="type"><option value="base">Essentiel (10k)</option><option value="warp">Blindé (20k)</option><option value="hotspot">Hotspot (30k)</option><option value="pro">Pro (50k)</option></select><button type="submit" class="btn-primary">Créer</button></form></div>""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
