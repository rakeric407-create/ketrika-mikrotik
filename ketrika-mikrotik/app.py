# ============================================
# NOUVEAU THÈME CLAIR - Remplace l'ancien BASE_CSS
# ============================================
BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    background: #f0f2f5;
    color: #333;
}

/* NAVBAR */
nav {
    background: #ffffff;
    padding: 15px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #e0e0e0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
nav .logo {
    color: #00875a;
    font-size: 22px;
    font-weight: bold;
    text-decoration: none;
}
nav .logo span { color: #0066cc; }
nav .links a {
    color: #555;
    text-decoration: none;
    margin-left: 20px;
    font-size: 14px;
    font-weight: 500;
}
nav .links a:hover { color: #00875a; }

/* CONTAINER */
.container { max-width: 1100px; margin: auto; padding: 30px 20px; }

/* FLASH */
.flash { padding: 12px 20px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; }
.flash.success { background: #e6f9ee; border: 1px solid #00875a; color: #006644; }
.flash.error { background: #fde8e8; border: 1px solid #cc3333; color: #991111; }
.flash.warning { background: #fff8e1; border: 1px solid #cc8800; color: #886600; }

/* BOUTONS */
.btn {
    padding: 12px 30px; border: none; border-radius: 8px;
    font-size: 15px; font-weight: bold; cursor: pointer;
    text-decoration: none; display: inline-block;
    transition: all 0.2s;
}
.btn-primary { background: #00875a; color: #fff; }
.btn-primary:hover { background: #006644; }
.btn-blue { background: #0066cc; color: #fff; }
.btn-blue:hover { background: #004c99; }
.btn-orange { background: #e65c00; color: #fff; }
.btn-orange:hover { background: #cc5200; }
.btn-danger { background: #cc3333; color: #fff; }

/* CARTES */
.card {
    background: #ffffff;
    border-radius: 12px;
    padding: 25px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* FORMULAIRES */
label { display: block; margin: 8px 0 4px; color: #555; font-size: 13px; font-weight: 500; }
input, select {
    width: 100%; padding: 10px; border: 1px solid #ccc;
    border-radius: 6px; background: #fff; color: #333;
    font-size: 14px; margin-bottom: 5px;
}
input:focus, select:focus {
    border-color: #00875a; outline: none;
    box-shadow: 0 0 0 3px rgba(0,135,90,0.1);
}

/* LAYOUT */
.row { display: flex; gap: 15px; flex-wrap: wrap; }
.row > div { flex: 1; min-width: 220px; }
.check { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.check input { width: auto; }

/* FOOTER */
footer {
    text-align: center; padding: 30px;
    color: #999; border-top: 1px solid #e0e0e0;
    margin-top: 50px; background: #fff;
}
"""
