"""
Agent trading intelligent — avec intégration Seb+
Comprend le langage naturel français pour mettre à jour le portefeuille
Utilise Seb+ (https://assistant-seb.onrender.com) comme moteur IA
"""

import json, re, os, requests

PORTFOLIO_FILE = "portfolio.json"
SEBPLUS_URL    = "https://assistant-seb.onrender.com"

# Mapping noms courants → tickers
NOM_TO_TICKER = {
    "oracle": "ORCL", "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT",
    "google": "GOOG", "alphabet": "GOOG", "meta": "META", "amazon": "AMZN",
    "tesla": "TSLA", "pinterest": "PINS", "stellantis": "STLAM.MI",
    "starbucks": "SBUX", "airbus": "AIR.PA", "thales": "HO.PA",
    "totalenergies": "TTE.PA", "total": "TTE.PA", "sanofi": "SAN.PA",
    "carrefour": "CA.PA", "dassault": "AM.PA", "euronext": "ENX.PA",
    "rheinmetall": "RHM.DE", "bae": "BA.L", "novartis": "NVS",
    "xpo": "XPO", "trigano": "TRI.PA", "leonardo": "LDO.MI",
    "byd": "0992.HK", "gtt": "GTT.PA", "bitcoin": "BTC-EUR", "btc": "BTC-EUR",
    "or": "GLD", "gold": "GLD", "sp500": "SPY", "nasdaq": "QQQ",
    "arteris": "AIP", "aip": "AIP"
}

def load():
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_ticker(text: str) -> str | None:
    """Cherche un ticker dans le texte"""
    text_low = text.lower()
    # Cherche les noms complets
    for nom, ticker in NOM_TO_TICKER.items():
        if nom in text_low:
            return ticker
    # Cherche les tickers directs (majuscules)
    data = load()
    tickers = [p["ticker"] for p in data["positions"]]
    for ticker in tickers:
        if ticker.upper() in text.upper():
            return ticker
    # Cherche par regex (2-5 lettres majuscules)
    matches = re.findall(r'\b([A-Z]{2,5}(?:\.[A-Z]{2})?)\b', text)
    for m in matches:
        if m in tickers:
            return m
    return None

def find_amount(text: str) -> float | None:
    """Extrait un montant en euros"""
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*(?:euros?|€)',
        r'(\d+(?:[.,]\d+)?)\s*(?:eur)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))
    return None

def find_price(text: str) -> float | None:
    """Extrait un prix"""
    patterns = [
        r'[àa@]\s*(\d+(?:[.,]\d+)?)\s*(?:\$|dollars?|usd|€|euros?)?',
        r'(?:prix|price|cours)\s*(?:de|d\'|:)?\s*(\d+(?:[.,]\d+)?)',
        r'(\d+(?:[.,]\d+)?)\s*(?:\$|dollars?|usd)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))
    return None

def find_units(text: str) -> float | None:
    """Extrait un nombre d'unités"""
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*(?:actions?|titres?|parts?|unités?|btc|eth)',
        r'(?:acheté?|achat|vendu?)\s+(\d+(?:[.,]\d+)?)',
        r'(\d+(?:[.,]\d+)?)\s+(?:actions?|titres?)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", "."))
    return None

def detect_intent(text: str) -> str:
    """Détecte l'intention de la commande"""
    text_low = text.lower()

    # Patterns de vente — nécessitent un sujet direct (pas "si je coupe", "dois-je couper")
    vente_patterns = [
        r"\bj[''e]\s*ai\s*(vendu|fermé|clôturé|sorti|coupé|supprimé)\b",
        r"\b(vends|ferme|supprime|clôture)\s+\w",
        r"\b(sortir|couper)\s+(?:de\s+)?\w{2,}",
    ]
    achat_mots = ["acheté", "achète", "achat", "renforce", "renforcé", "ajouté", "ajoute", "investi", "pris position"]

    for p in vente_patterns:
        if re.search(p, text_low):
            return "vendre"
    for m in achat_mots:
        if m in text_low:
            return "acheter"
    return "inconnu"

def test_sebplus_auth(password: str) -> bool:
    """Vérifie si le mot de passe Seb+ est valide"""
    try:
        res = requests.post(
            f"{SEBPLUS_URL}/api/auth",
            headers={"Content-Type": "application/json"},
            json={"password": password},
            timeout=10
        )
        return res.ok
    except Exception:
        return False

def build_portfolio_context() -> str:
    """Construit un résumé du portefeuille pour injecter dans le contexte Seb+"""
    try:
        data = load()
        positions = data.get("positions", [])
        lines = [f"Voici le portefeuille d'investissement actuel de l'utilisateur ({len(positions)} positions) :"]
        for p in positions:
            lines.append(f"- {p['ticker']} ({p['name']}) : {p['units']} unités, prix d'achat {p['buy_price']} {p['currency']}, type {p['type']}")
        lines.append("\nTu peux répondre à toutes les questions sur ce portefeuille (performance, diversification, conseils, etc.).")
        return "\n".join(lines)
    except Exception:
        return ""

def call_sebplus(password: str, messages: list, inject_portfolio: bool = True) -> str | None:
    """
    Appelle l'API Seb+ et retourne la réponse IA.
    messages = [{"role": "user"/"assistant", "content": "..."}, ...]
    Retourne None si Seb+ est indisponible ou si le mot de passe est faux.
    """
    try:
        full_messages = list(messages)
        if inject_portfolio:
            ctx = build_portfolio_context()
            if ctx:
                full_messages = [
                    {"role": "user",      "content": ctx},
                    {"role": "assistant", "content": "Bien noté, j'ai accès à ton portefeuille. Comment puis-je t'aider ?"}
                ] + full_messages

        res = requests.post(
            f"{SEBPLUS_URL}/api/chat",
            headers={
                "Content-Type": "application/json",
                "x-password": password
            },
            json={"messages": full_messages},
            timeout=30
        )
        if res.ok:
            data = res.json()
            return data.get("text") or data.get("response") or data.get("content") or ""
        return None
    except Exception:
        return None

def get_current_price(ticker: str) -> float | None:
    """Récupère le prix actuel pour estimer les unités"""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        return info.get("last_price")
    except:
        return None

def process_command(user_message: str) -> tuple[str, bool]:
    """
    Traite une commande en langage naturel
    Retourne (réponse, modifié)
    """
    data   = load()
    intent = detect_intent(user_message)
    ticker = find_ticker(user_message)

    # ── VENTE / FERMETURE ────────────────────────────────────────────────────
    if intent == "vendre":
        if not ticker:
            return "❓ Je n'ai pas trouvé quelle position tu veux fermer. Précise le ticker ou le nom (ex: 'J'ai vendu PINS')", False

        avant = len(data["positions"])
        nom   = next((p["name"] for p in data["positions"] if p["ticker"] == ticker), ticker)
        data["positions"] = [p for p in data["positions"] if p["ticker"] != ticker]

        if len(data["positions"]) < avant:
            save(data)
            return f"✅ **{ticker}** ({nom}) supprimé du portefeuille.\n\nPosition fermée avec succès !", True
        else:
            return f"⚠️ Je ne trouve pas **{ticker}** dans ton portefeuille. Vérifie le nom.", False

    # ── ACHAT / RENFORCEMENT ─────────────────────────────────────────────────
    elif intent == "acheter":
        if not ticker:
            return "❓ Je n'ai pas trouvé quel actif tu as acheté. Précise le nom ou ticker.", False

        price   = find_price(user_message)
        units   = find_units(user_message)
        amount  = find_amount(user_message)

        # Si montant en euros mais pas de prix ni d'unités → chercher prix actuel
        if amount and not price and not units:
            price = get_current_price(ticker)
            if price:
                units = round(amount / price, 6)

        # Si montant + prix → calculer les unités
        if amount and price and not units:
            units = round(amount / price, 6)

        if not units or not price:
            manque = []
            if not price: manque.append("le prix d'achat")
            if not units: manque.append("le nombre d'unités ou le montant")
            return f"❓ Il me manque {' et '.join(manque)} pour mettre à jour **{ticker}**.\n\nExemple : *'J'ai acheté 5 NVDA à 210$'* ou *'J'ai investi 100€ dans NVDA à 210$'*", False

        # Chercher si position existe déjà
        existant = next((p for p in data["positions"] if p["ticker"] == ticker), None)

        if existant:
            # Calcul nouveau prix moyen
            old_units = existant["units"]
            old_price = existant["buy_price"]
            new_total = old_units + units
            new_avg   = round(((old_units * old_price) + (units * price)) / new_total, 4)

            existant["units"]     = round(new_total, 8)
            existant["buy_price"] = new_avg
            save(data)

            return (f"✅ **{ticker}** renforcé !\n\n"
                    f"• Ajout : {units} unités @ {price}\n"
                    f"• Nouveau total : {round(new_total, 6)} unités\n"
                    f"• Nouveau prix moyen : {new_avg} ← calculé automatiquement"), True
        else:
            # Nouvelle position
            nom      = ticker
            currency = "EUR" if any(x in ticker for x in [".PA", ".MI", ".DE", ".L", "-EUR"]) else "USD"
            typ      = "Crypto" if "BTC" in ticker or "ETH" in ticker else "ETF" if ticker in ["GLD","SPY","QQQ"] else "Action"

            data["positions"].append({
                "ticker": ticker, "name": nom,
                "units": round(units, 8), "buy_price": price,
                "currency": currency, "type": typ
            })
            save(data)
            return (f"✅ **{ticker}** ajouté au portefeuille !\n\n"
                    f"• {round(units, 6)} unités @ {price} {currency}\n"
                    f"• Type : {typ}"), True

    # ── COMMANDE NON RECONNUE ────────────────────────────────────────────────
    else:
        # Peut-être une question sur le portfolio
        if any(m in user_message.lower() for m in ["combien", "valeur", "gain", "perte", "total", "portefeuille"]):
            positions = data["positions"]
            return (f"📊 Tu as **{len(positions)} positions** dans ton portefeuille.\n\n"
                    f"Pour voir les détails et les prix en temps réel, va sur l'onglet **📊 Dashboard**.\n\n"
                    f"**Commandes disponibles :**\n"
                    f"• *'J'ai vendu NVDA'* → supprime la position\n"
                    f"• *'J'ai acheté 5 AAPL à 200$'* → ajoute la position\n"
                    f"• *'J'ai investi 100€ dans BTC'* → calcule les unités auto"), False

        return (f"🤔 Je n'ai pas compris ta commande.\n\n"
                f"**Exemples :**\n"
                f"• *'J'ai vendu PINS'*\n"
                f"• *'J'ai acheté 5 actions NVDA à 210 dollars'*\n"
                f"• *'J'ai investi 100€ dans Oracle à 226$'*\n"
                f"• *'Ferme Stellantis'*\n"
                f"• *'J'ai renforcé Bitcoin avec 50€'*"), False
