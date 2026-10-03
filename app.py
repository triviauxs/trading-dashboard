import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, os, time
from datetime import datetime
import streamlit.components.v1 as components
from prices import get_prices
from alerts import check_alerts

# Répertoire du script pour les chemins relatifs
_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Trading Dashboard", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 24px !important; }
.green { color: #a6e3a1; } .red { color: #f38ba8; }
</style>
""", unsafe_allow_html=True)

# ── Chargement données ───────────────────────────────────────────────────────
def load_portfolio():
    with open(os.path.join(_DIR, "portfolio.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(data):
    with open(os.path.join(_DIR, "portfolio.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_dividendes():
    path = os.path.join("data", "dividendes.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

portfolio_data = load_portfolio()
positions      = portfolio_data["positions"]
settings       = portfolio_data["settings"]

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Trading Dashboard")
    st.caption(f"MAJ : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()
    refresh  = st.slider("Rafraîchissement (sec)", 30, 300, 60, step=30)
    sl_pct   = st.number_input("Stop Loss (%)",    value=settings["stop_loss_pct"],   step=1.0)
    tp_pct   = st.number_input("Take Profit (%)",  value=settings["take_profit_pct"], step=5.0)
    filtre   = st.multiselect("Filtrer", ["Action","ETF","Crypto"], default=["Action","ETF","Crypto"])
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔔 Telegram"):
            from alerts import send_telegram
            ok = send_telegram("✅ Test Dashboard OK !")
            st.success("Envoyé !") if ok else st.error("Config manquante")
    with c2:
        if st.button("📧 Email"):
            from alerts import send_email
            ok = send_email("✅ Test", "<p>OK</p>")
            st.success("Envoyé !") if ok else st.error("Config manquante")
    if st.button("📊 Bilan hebdo"):
        from alerts import send_weekly_summary
        df_tmp = get_prices([p for p in positions if p["type"] in filtre])
        send_weekly_summary(df_tmp)
        st.success("Bilan envoyé !")

# ── ONGLETS PRINCIPAUX ───────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "💰 Dividendes",
    "⚙️ Gestion Portfolio",
    "🏦 IBKR Trading",
    "🤖 Agent IA"
])

# ════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    col_t, col_d = st.columns([3,1])
    with col_t:
        st.title("📈 Mon Portefeuille eToro")
    with col_d:
        st.write("")
        st.caption(f"🕐 MAJ : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    with st.spinner("Chargement des prix..."):
        pos_filtrees = [p for p in positions if p["type"] in filtre]
        df = get_prices(pos_filtrees)

    df_v = df.dropna(subset=["G/P (%)"])
    alertes = check_alerts(df_v)
    for a in alertes:
        if a["type"] == "STOP LOSS":
            st.error(f"🔴 STOP LOSS : {a['ticker']} ({a['gp_pct']:.1f}%)")
        else:
            st.success(f"🟢 TAKE PROFIT : {a['ticker']} ({a['gp_pct']:.1f}%)")

    total_v  = df_v["Valeur (€)"].sum()
    total_i  = df_v["Investi (€)"].sum()
    total_gp = df_v["G/P (€)"].sum()
    gp_pct   = (total_gp / total_i * 100) if total_i > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💼 Valeur Totale",  f"{total_v:,.0f} €")
    c2.metric("💰 Investi",        f"{total_i:,.0f} €")
    c3.metric("📈 Gain/Perte",     f"{total_gp:+,.0f} €", f"{gp_pct:+.1f}%")
    c4.metric("📊 Positions",      f"{len(df_v)} actifs")

    st.divider()

    cg1, cg2 = st.columns(2)
    with cg1:
        st.subheader("Répartition")
        rep = df_v.groupby("Type")["Valeur (€)"].sum().reset_index()
        fig = px.pie(rep, values="Valeur (€)", names="Type", hole=0.4,
                     color_discrete_map={"Action":"#89b4fa","ETF":"#a6e3a1","Crypto":"#f9e2af"})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with cg2:
        st.subheader("Performance par position")
        ds = df_v.sort_values("G/P (%)")
        fig2 = go.Figure(go.Bar(
            x=ds["G/P (%)"], y=ds["Ticker"], orientation="h",
            marker_color=["#f38ba8" if x < 0 else "#a6e3a1" for x in ds["G/P (%)"]],
            text=[f"{v:+.1f}%" for v in ds["G/P (%)"]],
            textposition="outside"
        ))
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                           height=450, margin=dict(t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("📋 Toutes les positions")

    def color_gp(val):
        if not isinstance(val, (int, float)): return ""
        return "color: #a6e3a1; font-weight:bold" if val > 0 else "color: #f38ba8; font-weight:bold" if val < 0 else ""

    def color_alert(val):
        if not isinstance(val, (int, float)): return ""
        if val <= sl_pct: return "background:#3d1010; color:#f38ba8; font-weight:bold"
        if val >= tp_pct: return "background:#103d10; color:#a6e3a1; font-weight:bold"
        return ""

    cols = ["Ticker","Nom","Type","Prix Actuel","Devise","Valeur (€)","Investi (€)","G/P (€)","G/P (%)","MAJ"]
    styled = (df[cols].style
              .map(color_gp, subset=["G/P (€)"])
              .map(color_alert, subset=["G/P (%)"])
              .format({"Prix Actuel": lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A",
                       "Valeur (€)":  lambda x: f"{x:,.2f} €" if pd.notna(x) else "N/A",
                       "Investi (€)": lambda x: f"{x:,.2f} €" if pd.notna(x) else "N/A",
                       "G/P (€)":     lambda x: f"{x:+,.2f} €" if pd.notna(x) else "N/A",
                       "G/P (%)":     lambda x: f"{x:+,.2f} %" if pd.notna(x) else "N/A"}))
    st.dataframe(styled, use_container_width=True, height=700)

    st.divider()
    ct1, ct2 = st.columns(2)
    with ct1:
        st.subheader("🏆 Top 5")
        for _, r in df_v.nlargest(5,"G/P (%)").iterrows():
            st.markdown(f"**{r['Ticker']}** — {r['Nom']}  \n"
                        f"<span style='color:#a6e3a1'>+{r['G/P (%)']:.1f}% (+{r['G/P (€)']:.0f}€)</span>",
                        unsafe_allow_html=True)
            st.divider()
    with ct2:
        st.subheader("⚠️ À surveiller")
        for _, r in df_v.nsmallest(5,"G/P (%)").iterrows():
            c = "#f38ba8" if r["G/P (%)"] <= sl_pct else "#f9e2af"
            st.markdown(f"**{r['Ticker']}** — {r['Nom']}  \n"
                        f"<span style='color:{c}'>{r['G/P (%)']:.1f}% ({r['G/P (€)']:.0f}€)</span>",
                        unsafe_allow_html=True)
            st.divider()

    st.caption(f"⏱ Rafraîchissement automatique toutes les {refresh}s")
    components.html(f"<script>setTimeout(()=>window.location.reload(),{refresh*1000});</script>", height=0)

# ════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — DIVIDENDES
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.title("💰 Dividendes reçus")
    divs = load_dividendes()

    if not divs:
        st.info("Pas encore de données. Upload ton relevé eToro ci-dessous.")
    else:
        df_d = pd.DataFrame(divs)
        df_d["montant_eur"] = pd.to_numeric(df_d["montant_eur"], errors="coerce")
        df_d["date"]        = pd.to_datetime(df_d["date"], errors="coerce")
        df_d["mois"]        = df_d["date"].dt.strftime("%Y-%m")

        total    = df_d["montant_eur"].sum()
        nb       = len(df_d)
        moy_m    = df_d.groupby("mois")["montant_eur"].sum().mean()
        top_p    = df_d.groupby("nom")["montant_eur"].sum().idxmax()

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("💶 Total 2026",      f"{total:.2f} €")
        c2.metric("📅 Paiements",       str(nb))
        c3.metric("📆 Moyenne/mois",    f"{moy_m:.2f} €")
        c4.metric("🏆 Top payeur",      top_p.split(" ")[0])

        st.divider()
        cg1, cg2 = st.columns(2)
        with cg1:
            st.subheader("Par mois")
            dm = df_d.groupby("mois")["montant_eur"].sum().reset_index()
            fig = px.bar(dm, x="mois", y="montant_eur",
                         color_discrete_sequence=["#a6e3a1"],
                         labels={"mois":"Mois","montant_eur":"€"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

        with cg2:
            st.subheader("Par action")
            da = df_d.groupby("nom")["montant_eur"].sum().reset_index()
            fig2 = px.pie(da, values="montant_eur", names="nom", hole=0.4)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.subheader("Détail des paiements")
        df_show = df_d.sort_values("date", ascending=False).copy()
        df_show["date"] = df_show["date"].dt.strftime("%d/%m/%Y")
        df_show.columns = ["Date","Société","Montant (€)","Mois"]
        st.dataframe(df_show[["Date","Société","Montant (€)"]].style.format({"Montant (€)":"{:.4f} €"}),
                     use_container_width=True, height=400)

        mois_ec = df_d["mois"].nunique()
        proj    = (total / mois_ec) * 12
        st.info(f"📈 **Projection annuelle : ~{proj:.0f}€/an** ({proj/12:.0f}€/mois de revenus passifs)")

    st.divider()
    st.subheader("📥 Mettre à jour depuis eToro")
    up = st.file_uploader("Relevé eToro (.xlsx)", type=["xlsx"])
    if up:
        try:
            df_new   = pd.read_excel(up, sheet_name="Dividendes")
            df_clean = df_new[[df_new.columns[0], df_new.columns[1], df_new.columns[7]]].copy()
            df_clean.columns = ["date","nom","montant_eur"]
            df_clean["date"] = df_clean["date"].astype(str)
            os.makedirs("data", exist_ok=True)
            with open("data/dividendes.json","w",encoding="utf-8") as f:
                json.dump(df_clean.to_dict("records"), f, ensure_ascii=False, indent=2)
            st.success(f"✅ {len(df_clean)} dividendes importés !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

# ════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — GESTION PORTFOLIO
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.title("⚙️ Gestion du Portefeuille")
    data = load_portfolio()

    st.subheader("📋 Positions actuelles")
    st.dataframe(pd.DataFrame(data["positions"])[["ticker","name","type","units","buy_price","currency"]],
                 use_container_width=True, height=400)

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("➕ Ajouter / Modifier une position")
        with st.form("add"):
            ticker   = st.text_input("Ticker", placeholder="NVDA, BTC-EUR, AIR.PA").upper().strip()
            name     = st.text_input("Nom", placeholder="Nvidia Corporation")
            typ      = st.selectbox("Type", ["Action","ETF","Crypto"])
            units    = st.number_input("Unités", min_value=0.0, format="%.6f")
            price    = st.number_input("Prix d'achat", min_value=0.0, format="%.4f")
            currency = st.selectbox("Devise", ["USD","EUR","GBp","HKD"])
            if st.form_submit_button("✅ Ajouter", type="primary"):
                if ticker and units > 0 and price > 0:
                    existants = [p["ticker"] for p in data["positions"]]
                    if ticker in existants:
                        for p in data["positions"]:
                            if p["ticker"] == ticker:
                                p["units"] = units; p["buy_price"] = price
                        st.success(f"✅ {ticker} mis à jour !")
                    else:
                        data["positions"].append({"ticker":ticker,"name":name,"units":units,
                                                   "buy_price":price,"currency":currency,"type":typ})
                        st.success(f"✅ {ticker} ajouté !")
                    save_portfolio(data)
                    st.rerun()
                else:
                    st.error("Remplis tous les champs !")

    with c2:
        st.subheader("🗑️ Fermer une position")
        tickers = [f"{p['ticker']} — {p['name']}" for p in data["positions"]]
        to_del  = st.selectbox("Position à supprimer", tickers)
        if st.button("🗑️ Supprimer", type="primary"):
            t = to_del.split(" — ")[0]
            data["positions"] = [p for p in data["positions"] if p["ticker"] != t]
            save_portfolio(data)
            st.success(f"✅ {t} supprimé !")
            st.rerun()

    # ── Import eToro ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("📥 Synchroniser depuis eToro (Excel)")
    st.caption("eToro → Portefeuille → Historique → Exporter → glisse le fichier ici")

    up_etoro = st.file_uploader("Relevé eToro (.xlsx)", type=["xlsx"], key="etoro_up")
    if up_etoro:
        try:
            xl = pd.ExcelFile(up_etoro)
            st.info(f"Feuilles trouvées : {', '.join(xl.sheet_names)}")

            # Chercher la feuille des positions ouvertes
            sheet = None
            for name_sh in xl.sheet_names:
                if any(k in name_sh.lower() for k in ["open", "position", "portfolio", "portefeuille"]):
                    sheet = name_sh
                    break
            if not sheet:
                sheet = xl.sheet_names[0]

            df_raw = pd.read_excel(up_etoro, sheet_name=sheet)
            st.write(f"**Feuille utilisée : {sheet}** ({len(df_raw)} lignes)")
            st.dataframe(df_raw.head(5), use_container_width=True)

            # Mapping automatique des colonnes
            cols = [c.lower() for c in df_raw.columns]
            col_map = {}
            for c in df_raw.columns:
                cl = c.lower()
                if any(k in cl for k in ["symbol","ticker","action","instrument"]):
                    col_map["ticker"] = c
                elif any(k in cl for k in ["name","nom","libellé","compagnie"]):
                    col_map["name"] = c
                elif any(k in cl for k in ["unit","quantit","amount","nb"]):
                    col_map["units"] = c
                elif any(k in cl for k in ["open rate","prix","price","open","cours"]):
                    col_map["buy_price"] = c

            if "ticker" in col_map and "units" in col_map and "buy_price" in col_map:
                if st.button("✅ Importer ces positions", type="primary"):
                    nouvelles = []
                    for _, row in df_raw.iterrows():
                        ticker_val = str(row[col_map["ticker"]]).strip().upper()
                        if not ticker_val or ticker_val == "NAN":
                            continue
                        nom = str(row[col_map.get("name", col_map["ticker"])]).strip()
                        try:
                            units_val = float(row[col_map["units"]])
                            price_val = float(row[col_map["buy_price"]])
                        except:
                            continue
                        if units_val <= 0 or price_val <= 0:
                            continue
                        currency = "EUR" if any(x in ticker_val for x in [".PA",".MI",".DE",".L","-EUR"]) else "USD"
                        typ = "Crypto" if "BTC" in ticker_val or "ETH" in ticker_val else "ETF" if ticker_val in ["GLD","SPY","QQQ"] else "Action"
                        nouvelles.append({"ticker": ticker_val, "name": nom, "units": round(units_val,8),
                                          "buy_price": round(price_val,4), "currency": currency, "type": typ})

                    if nouvelles:
                        data["positions"] = nouvelles
                        save_portfolio(data)
                        st.success(f"✅ {len(nouvelles)} positions importées depuis eToro !")
                        st.rerun()
                    else:
                        st.error("Aucune position valide trouvée dans le fichier.")
            else:
                st.warning(f"Colonnes détectées : {list(df_raw.columns)}\n\nJe n'arrive pas à mapper automatiquement. Envoie une capture à Claude pour qu'il ajuste.")
        except Exception as e:
            st.error(f"Erreur lecture fichier : {e}")

# ════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — IBKR TRADING
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.title("🏦 IBKR — Trading en direct")

    try:
        from ibkr import is_connected, get_account_summary, get_balance, get_portfolio
        connected = is_connected()
    except:
        connected = False

    if not connected:
        st.error("❌ Non connecté au gateway IBKR")
        st.info("""
        **Compte créé ✅ — En attente de validation (24-48h)**

        Une fois validé, pour activer la connexion :
        1. Télécharge **Client Portal Gateway** → interactivebrokers.com/api
        2. Lance `gateway/bin/run.bat`
        3. Connecte-toi sur **https://localhost:5000**
        4. Reviens ici et rafraîchis

        📧 Surveille ta boîte mail — IBKR enverra la confirmation sous 24-48h
        """)
        st.metric("Compte IBKR", "U26157956")
        st.metric("Statut", "⏳ En attente de validation")
    else:
        summary = get_account_summary()
        balance = get_balance()
        c1,c2,c3 = st.columns(3)
        c1.metric("💶 Solde", f"{balance:,.2f} €" if balance else "N/A")
        c2.metric("📈 P&L non réalisé", f"{summary.get('unrealizedpnl',{}).get('amount',0):+,.2f} €")
        c3.metric("🏦 Valeur nette",    f"{summary.get('netliquidation',{}).get('amount',0):,.2f} €")

# ════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — AGENT IA (Seb+)
# ════════════════════════════════════════════════════════════════════════════
with tab5:
    from agent import process_command, call_sebplus, test_sebplus_auth

    # ── Init session state ────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "sebplus_pwd" not in st.session_state:
        try:
            from config import SEBPLUS_PASSWORD
            st.session_state.sebplus_pwd = SEBPLUS_PASSWORD
        except:
            st.session_state.sebplus_pwd = ""

    sebplus_pwd = st.session_state.sebplus_pwd

    # ── Header ───────────────────────────────────────────────────────────
    col_title, col_status = st.columns([4, 1])
    with col_title:
        st.title("🤖 Agent IA — Seb+")
    with col_status:
        st.write("")
        if sebplus_pwd:
            st.success("🟢 Seb+ actif")
        else:
            st.warning("🟡 Mode local")

    # ── Configuration Seb+ ───────────────────────────────────────────────
    if not sebplus_pwd:
        with st.expander("🔌 **Connecter Seb+** — Ton assistant IA personnel", expanded=True):
            st.markdown("""
            Seb+ est ton assistant Claude personnel hébergé sur **assistant-seb.onrender.com**.
            Entre ton mot de passe pour l'activer comme moteur IA du dashboard.
            """)
            col_pwd, col_btn = st.columns([3, 1])
            with col_pwd:
                pwd_input = st.text_input("Mot de passe Seb+", type="password",
                                          placeholder="Ton mot de passe Seb+",
                                          key="seb_pwd_input")
            with col_btn:
                st.write("")
                st.write("")
                if st.button("🔌 Connecter", type="primary"):
                    if pwd_input:
                        with st.spinner("Connexion à Seb+..."):
                            ok = test_sebplus_auth(pwd_input)
                        if ok:
                            st.session_state.sebplus_pwd = pwd_input
                            st.success("✅ Seb+ connecté !")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Mot de passe incorrect ou Seb+ hors ligne")
                    else:
                        st.warning("Saisis ton mot de passe")

        st.info("""
        **Mode local actif** — Commandes portefeuille disponibles sans Seb+ :
        • *"J'ai vendu PINS"*
        • *"J'ai acheté 5 NVDA à 210$"*
        • *"J'ai investi 100€ dans Oracle à 226$"*
        """)
    else:
        # Bouton déconnecter discret
        with st.expander("⚙️ Paramètres Seb+"):
            st.write("Connecté à : `assistant-seb.onrender.com`")
            if st.button("🔒 Déconnecter Seb+"):
                st.session_state.sebplus_pwd = ""
                st.rerun()
            st.caption("Tu peux aussi sauvegarder ton mot de passe dans `config.py → SEBPLUS_PASSWORD`")

        st.caption("💬 Parle à Seb+ — il gère aussi ton portefeuille, pose n'importe quelle question !")

    st.divider()

    # ── Affichage historique ──────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # ── Input utilisateur ─────────────────────────────────────────────────
    placeholder = "Pose une question à Seb+ ou dis-lui ce que tu as tradé..." if sebplus_pwd else "Dis-moi ce que tu as tradé..."
    user_input = st.chat_input(placeholder)
    modifie    = False
    response   = ""

    if user_input:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            spinner_txt = "Seb+ réfléchit..." if sebplus_pwd else "Analyse en cours..."
            with st.spinner(spinner_txt):
                try:
                    # ── Étape 1 : détection action portefeuille ────────────
                    local_response, modifie = process_command(user_input)

                    if sebplus_pwd:
                        # ── Étape 2 : appel Seb+ ──────────────────────────
                        # Construire l'historique de conversation pour Seb+
                        seb_messages = []
                        for m in st.session_state.chat_history[-10:]:  # 10 derniers messages
                            role = "user" if m["role"] == "user" else "assistant"
                            seb_messages.append({"role": role, "content": m["content"]})
                        seb_messages.append({"role": "user", "content": user_input})

                        seb_response = call_sebplus(sebplus_pwd, seb_messages)

                        if seb_response:
                            if modifie:
                                # Action portefeuille + réponse Seb+
                                response = f"{local_response}\n\n---\n\n{seb_response}"
                            else:
                                response = seb_response
                        else:
                            # Seb+ indisponible → mode local
                            response = local_response
                            if not modifie:
                                response += "\n\n⚠️ *Seb+ momentanément indisponible — réponse locale uniquement*"
                    else:
                        # Mode local uniquement
                        response = local_response

                    st.markdown(response)
                    if modifie:
                        st.balloons()

                except Exception as e:
                    response = f"⚠️ Erreur : {str(e)}"
                    st.error(response)

        st.session_state.chat_history.append({"role": "user",      "content": user_input})
        st.session_state.chat_history.append({"role": "assistant",  "content": response})

        if modifie:
            import time as _t; _t.sleep(1)
            st.rerun()

    # ── Effacer conversation ──────────────────────────────────────────────
    if st.session_state.chat_history:
        st.divider()
        if st.button("🗑️ Effacer la conversation"):
            st.session_state.chat_history = []
            st.rerun()
