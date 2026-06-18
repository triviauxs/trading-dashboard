"""
Connexion IBKR via Client Portal API (REST local)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prérequis :
  1. Télécharger IBKR Client Portal Gateway :
     https://www.interactivebrokers.com/en/trading/ib-api.php
  2. Dézipper et lancer : gateway/bin/run.bat
  3. Se connecter sur https://localhost:5000
  4. Lancer notre dashboard → connexion automatique
"""

import requests
import urllib3
from config import IBKR_ACCOUNT, IBKR_GATEWAY_URL

# Désactive les warnings SSL du gateway local
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = IBKR_GATEWAY_URL
ACCT = IBKR_ACCOUNT

def _get(endpoint, params=None):
    try:
        r = requests.get(f"{BASE}{endpoint}", params=params, verify=False, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _post(endpoint, data=None):
    try:
        r = requests.post(f"{BASE}{endpoint}", json=data, verify=False, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Statut de la connexion ───────────────────────────────────────────────────
def is_connected():
    """Vérifie si le gateway IBKR est actif"""
    result = _get("/v1/api/iserver/auth/status")
    return result.get("authenticated", False)

# ── Portefeuille ─────────────────────────────────────────────────────────────
def get_portfolio():
    """Récupère toutes les positions IBKR"""
    return _get(f"/v1/api/portfolio/{ACCT}/positions/0")

def get_account_summary():
    """Récupère le résumé du compte (solde, P&L...)"""
    return _get(f"/v1/api/portfolio/{ACCT}/summary")

def get_balance():
    """Retourne le solde disponible en EUR"""
    summary = get_account_summary()
    if "error" in summary:
        return None
    try:
        return summary.get("availablefunds", {}).get("amount", 0)
    except:
        return None

# ── Prix en temps réel ───────────────────────────────────────────────────────
def get_market_data(conids: list):
    """
    Récupère les prix live pour une liste de conids IBKR
    conid = identifiant interne IBKR d'un actif
    """
    conid_str = ",".join(str(c) for c in conids)
    return _get("/v1/api/iserver/marketdata/snapshot",
                params={"conids": conid_str, "fields": "31,83,84,85,86"})

def search_conid(symbol: str):
    """Cherche le conid IBKR d'un ticker"""
    result = _post("/v1/api/iserver/secdef/search", {"symbol": symbol})
    if isinstance(result, list) and result:
        return result[0].get("conid")
    return None

# ── Ordres ───────────────────────────────────────────────────────────────────
def place_order(conid: int, action: str, quantity: float,
                order_type: str = "MKT", price: float = None):
    """
    Passe un ordre sur IBKR
    action     : "BUY" ou "SELL"
    order_type : "MKT" (marché) ou "LMT" (limite)
    price      : obligatoire si order_type = "LMT"
    """
    order = {
        "acctId":    ACCT,
        "conid":     conid,
        "orderType": order_type,
        "side":      action,
        "quantity":  quantity,
        "tif":       "DAY"
    }
    if order_type == "LMT" and price:
        order["price"] = price

    return _post(f"/v1/api/iserver/account/{ACCT}/orders",
                 {"orders": [order]})

def get_orders():
    """Récupère les ordres en cours"""
    return _get("/v1/api/iserver/account/orders")

def cancel_order(order_id: str):
    """Annule un ordre"""
    try:
        r = requests.delete(
            f"{BASE}/v1/api/iserver/account/{ACCT}/order/{order_id}",
            verify=False, timeout=5
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Historique ───────────────────────────────────────────────────────────────
def get_trades():
    """Récupère l'historique des trades exécutés"""
    return _get("/v1/api/iserver/account/trades")
