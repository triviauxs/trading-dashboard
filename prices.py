import yfinance as yf
import pandas as pd
from datetime import datetime

# Taux de change vers EUR
FX_PAIRS = {
    "USD": "EURUSD=X",
    "GBp": "GBPEUR=X",
    "HKD": "HKDEUR=X",
    "EUR": None
}

def get_fx_rates():
    """Récupère les taux de change vers EUR"""
    rates = {"EUR": 1.0}
    for currency, ticker in FX_PAIRS.items():
        if ticker:
            try:
                data = yf.Ticker(ticker).fast_info
                rate = data.get("last_price", None)
                if rate:
                    if currency == "USD":
                        rates["USD"] = 1 / rate      # 1 USD = X EUR
                    elif currency == "GBp":
                        rates["GBp"] = rate / 100    # pence vers EUR
                    elif currency == "HKD":
                        rates["HKD"] = 1 / rate
            except:
                # Fallback rates si API indispo
                rates.setdefault("USD", 0.925)
                rates.setdefault("GBp", 0.01165)
                rates.setdefault("HKD", 0.118)
    # Fallback si manquant
    rates.setdefault("USD", 0.925)
    rates.setdefault("GBp", 0.01165)
    rates.setdefault("HKD", 0.118)
    return rates

def get_prices(positions):
    """Récupère les prix actuels pour toutes les positions"""
    tickers = [p["ticker"] for p in positions]
    fx = get_fx_rates()

    results = []
    for pos in positions:
        try:
            ticker_obj = yf.Ticker(pos["ticker"])
            info = ticker_obj.fast_info
            current_price = info.get("last_price", None)

            if current_price is None:
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    current_price = hist["Close"].iloc[-1]

            if current_price:
                currency = pos["currency"]
                rate = fx.get(currency, 1.0)

                current_price_eur = current_price * rate
                buy_price_eur     = pos["buy_price"] * rate

                valeur_nette = current_price_eur * pos["units"]
                investi      = buy_price_eur * pos["units"]
                gp_eur       = valeur_nette - investi
                gp_pct       = ((current_price - pos["buy_price"]) / pos["buy_price"]) * 100

                results.append({
                    "Ticker":        pos["ticker"],
                    "Nom":           pos["name"],
                    "Type":          pos["type"],
                    "Prix Achat":    pos["buy_price"],
                    "Prix Actuel":   round(current_price, 2),
                    "Devise":        currency,
                    "Unités":        pos["units"],
                    "Valeur (€)":    round(valeur_nette, 2),
                    "Investi (€)":   round(investi, 2),
                    "G/P (€)":       round(gp_eur, 2),
                    "G/P (%)":       round(gp_pct, 2),
                    "MAJ":           datetime.now().strftime("%H:%M:%S")
                })
            else:
                results.append({
                    "Ticker":        pos["ticker"],
                    "Nom":           pos["name"],
                    "Type":          pos["type"],
                    "Prix Achat":    pos["buy_price"],
                    "Prix Actuel":   None,
                    "Devise":        pos["currency"],
                    "Unités":        pos["units"],
                    "Valeur (€)":    None,
                    "Investi (€)":   pos["buy_price"] * pos["units"],
                    "G/P (€)":       None,
                    "G/P (%)":       None,
                    "MAJ":           "Erreur"
                })
        except Exception as e:
            results.append({
                "Ticker":        pos["ticker"],
                "Nom":           pos["name"],
                "Type":          pos["type"],
                "Prix Achat":    pos["buy_price"],
                "Prix Actuel":   None,
                "Devise":        pos["currency"],
                "Unités":        pos["units"],
                "Valeur (€)":    None,
                "Investi (€)":   pos["buy_price"] * pos["units"],
                "G/P (€)":       None,
                "G/P (%)":       None,
                "MAJ":           f"Erreur: {str(e)[:30]}"
            })

    return pd.DataFrame(results)
