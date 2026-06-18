import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import *

# Mémoire des alertes déjà envoyées (évite le spam)
_alertes_envoyees = set()

def send_telegram(message: str):
    """Envoie un message Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code == 200
    except:
        return False

def send_email(subject: str, body: str):
    """Envoie un email via Gmail"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECEIVER
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        return True
    except:
        return False

def check_alerts(df):
    """Vérifie les seuils et envoie des alertes si nécessaire"""
    alertes = []

    for _, row in df.iterrows():
        if row["G/P (%)"] is None:
            continue

        ticker = row["Ticker"]
        gp_pct = row["G/P (%)"]
        gp_eur = row["G/P (€)"]
        nom    = row["Nom"]

        # STOP LOSS
        cle_sl = f"SL_{ticker}"
        if gp_pct <= STOP_LOSS_PCT and cle_sl not in _alertes_envoyees:
            msg = (
                f"🔴 <b>STOP LOSS — {ticker}</b>\n"
                f"{nom}\n"
                f"G/P : {gp_pct:.1f}% ({gp_eur:+.2f}€)\n"
                f"⚠️ Seuil atteint ({STOP_LOSS_PCT}%) — Envisage de couper !"
            )
            send_telegram(msg)
            send_email(
                f"🔴 STOP LOSS {ticker} ({gp_pct:.1f}%)",
                f"<p>{msg.replace(chr(10), '<br>')}</p>"
            )
            _alertes_envoyees.add(cle_sl)
            alertes.append({"type": "STOP LOSS", "ticker": ticker, "gp_pct": gp_pct})

        # TAKE PROFIT
        cle_tp = f"TP_{ticker}"
        if gp_pct >= TAKE_PROFIT_PCT and cle_tp not in _alertes_envoyees:
            msg = (
                f"🟢 <b>TAKE PROFIT — {ticker}</b>\n"
                f"{nom}\n"
                f"G/P : +{gp_pct:.1f}% (+{gp_eur:.2f}€)\n"
                f"💰 Objectif atteint ({TAKE_PROFIT_PCT}%) — Envisage de sécuriser !"
            )
            send_telegram(msg)
            send_email(
                f"🟢 TAKE PROFIT {ticker} (+{gp_pct:.1f}%)",
                f"<p>{msg.replace(chr(10), '<br>')}</p>"
            )
            _alertes_envoyees.add(cle_tp)
            alertes.append({"type": "TAKE PROFIT", "ticker": ticker, "gp_pct": gp_pct})

    return alertes

def send_weekly_summary(df):
    """Envoie un bilan hebdomadaire par email"""
    if df.empty:
        return

    total_valeur  = df["Valeur (€)"].sum()
    total_investi = df["Investi (€)"].sum()
    total_gp      = df["G/P (€)"].sum()
    total_gp_pct  = (total_gp / total_investi * 100) if total_investi > 0 else 0

    top3    = df.nlargest(3, "G/P (%)")
    bottom3 = df.nsmallest(3, "G/P (%)")

    html = f"""
    <h2>📊 Bilan hebdomadaire — {datetime.now().strftime('%d/%m/%Y')}</h2>
    <h3>Total portefeuille</h3>
    <ul>
      <li>Valeur totale : <b>{total_valeur:.2f}€</b></li>
      <li>Investi : <b>{total_investi:.2f}€</b></li>
      <li>G/P total : <b style="color:{'green' if total_gp >= 0 else 'red'}">{total_gp:+.2f}€ ({total_gp_pct:+.1f}%)</b></li>
    </ul>
    <h3>🏆 Top 3</h3>
    <ul>{''.join(f"<li>{r['Ticker']} — {r['Nom']} : <b style='color:green'>+{r['G/P (%)']:.1f}% (+{r['G/P (€)']:.2f}€)</b></li>" for _, r in top3.iterrows())}</ul>
    <h3>⚠️ Bottom 3</h3>
    <ul>{''.join(f"<li>{r['Ticker']} — {r['Nom']} : <b style='color:red'>{r['G/P (%)']:.1f}% ({r['G/P (€)']:.2f}€)</b></li>" for _, r in bottom3.iterrows())}</ul>
    """

    send_email(f"📊 Bilan hebdo portefeuille — {datetime.now().strftime('%d/%m/%Y')}", html)
    send_telegram(
        f"📊 <b>Bilan hebdo</b>\n"
        f"Valeur : {total_valeur:.0f}€\n"
        f"G/P : {total_gp:+.0f}€ ({total_gp_pct:+.1f}%)\n"
        f"🏆 Top : {top3.iloc[0]['Ticker']} ({top3.iloc[0]['G/P (%)']:+.1f}%)\n"
        f"⚠️ Bas : {bottom3.iloc[0]['Ticker']} ({bottom3.iloc[0]['G/P (%)']:+.1f}%)"
    )
