import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar

# --- CONFIG DE LA PAGE ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")

# --- SÉCURITÉ ---
def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        if user in st.secrets["passwords"] and pwd == st.secrets["passwords"][user]:
            st.session_state["password_correct"] = True
            st.session_state["user_authenticated"] = user
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🏛️ Accès RNM IMMO")
        st.text_input("Identifiant", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    return True

if check_password():
    
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"
    RESA_FILE = "reservations.csv"
    OBJ_FILE = "objectifs_014_v2.csv" # Fichier partagé pour les objectifs des deux biens

    def load_config():
        if os.path.exists(CONFIG_FILE):
            df = pd.read_csv(CONFIG_FILE)
            if "Date Début" in df.columns:
                df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
            return df
        return pd.DataFrame(columns=["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"])

    def load_compta():
        if os.path.exists(COMPTA_FILE):
            df = pd.read_csv(COMPTA_FILE)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df
        return pd.DataFrame(columns=["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"])

    def load_resa():
        if os.path.exists(RESA_FILE):
            df = pd.read_csv(RESA_FILE, dtype=str)
            df["Date Arrivée"] = pd.to_datetime(df["Date Arrivée"], errors='coerce').dt.date
            df["Date Départ"] = pd.to_datetime(df["Date Départ"], errors='coerce').dt.date
            if "Montant" in df.columns:
                df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0.0)
            return df
        return pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant", "Numéro tel", "Mail", "Code Résidence", "Code Studio", "Code Autre"])

    def load_objectifs():
        if os.path.exists(OBJ_FILE):
            df = pd.read_csv(OBJ_FILE)
            if "Bien" not in df.columns: df["Bien"] = "014" # Migration pour gérer plusieurs biens
            return df
        return pd.DataFrame(columns=["Année", "Mois", "Objectif", "Bien"])

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()
    df_obj_all = load_objectifs()

    def get_solde(compte_nom):
        if df_compta.empty: return 0.0
        df_c = df_compta[df_compta["Compte"] == compte_nom]
        rev = pd.to_numeric(df_c[df_c["Type"] == "Revenu"]["Montant"]).sum()
        dep = pd.to_numeric(df_c[df_c["Type"] == "Dépense"]["Montant"]).sum()
        cre = pd.to_numeric(df_c[df_c["Type"] == "Crédit"]["Montant"]).sum()
        return float(rev - dep - cre)

    solde_cic = get_solde("CIC")
    solde_cash_physique = get_solde("Cash")
    total_treso_dynamique = solde_cic + solde_cash_physique

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("📂 Navigation")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Réservations", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)
        
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- LOGIQUE RNM IMMO, COMPTA, RÉSERVATIONS (INCHANGÉE) ---
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Tableau de Bord")
        if not df_cfg.empty:
            for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
                df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
            total_brut = df_cfg["Valeur Actuelle"].sum()
            def calc_crd(row):
                try:
                    P, r, n = float(row["Montant Crédit"]), (float(row["Taux (%)"])/100)/12, int(row["Durée (mois)"])
                    diff = relativedelta(date.today(), row["Date Début"])
                    m = diff.years * 12 + diff.months
                    if m <= 0: return P
                    if m >= n: return 0
                    return P * ((1 + r)**n - (1 + r)**m) / ((1 + r)**n - 1)
                except: return 0
            df_cfg["Capital Restant"] = df_cfg.apply(calc_crd, axis=1)
            total_crd = df_cfg["Capital Restant"].sum()
            total_net = (total_brut + total_treso_dynamique) - total_crd
            df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
            df_cfg["% Net"] = (df_cfg["Patrimoine Net Bien"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
            df_cfg["% Dette"] = (df_cfg["Capital Restant"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
        else: total_brut = total_crd = total_net = 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net:,.0f} €")
        st.divider()
        edited_df = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Biens"):
            cols_save = [c for c in edited_df.columns if c not in ["Capital Restant", "Patrimoine Net Bien", "% Net", "% Dette"]]
            edited_df[cols_save].to_csv(CONFIG_FILE, index=False)
            st.rerun()
        if not df_cfg.empty:
            st.divider()
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            st.plotly_chart(fig, use_container_width=True)

    elif page == "COMPTA":
        st.title("💰 Comptabilité - RNM IMMO")
        c1, c2, c3 = st.columns(3)
        c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
        c2.metric("Montant Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL TRESORERIE", f"{total_treso_dynamique:,.2f} €")
        st.divider()
        ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Compta"):
            ed_c.to_csv(COMPTA_FILE, index=False)
            st.rerun()

    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        if os.path.exists(RESA_FILE):
            df_resa = pd.read_csv(RESA_FILE, dtype=str)
        edited_resa = st.data_editor(df_resa, num_rows="dynamic", use_container_width=True, key="editor_final_v4")
        if st.button("💾 SAUVEGARDER RÉSERVATIONS"):
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()
        # Calendrier de contrôle
        evts = []
        for _, r in edited_resa.iterrows():
            try:
                d1, d2 = pd.to_datetime(r["Date Arrivée"]), pd.to_datetime(r["Date Départ"])
                evts.append({"title": f"[{r['Appartement']}] {r['Prénom_Nom']}", "start": d1.strftime("%Y-%m-%d"), "end": d2.strftime("%Y-%m-%d"), "allDay": True})
            except: continue
        calendar(events=evts, options={"initialView": "dayGridMonth", "locale": "fr"})

    # --- PAGES DE DÉTAIL (014 & 119) ---
    elif page in ["Détail 014", "Détail 119"]:
        bien_id = "014" if page == "Détail 014" else "119"
        st.title(f"🏠 Détail Local {bien_id}")
        
        # 1. Gestion des Objectifs spécifiques au bien
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_filter = df_obj_all[(df_obj_all["Année"] == sel_year) & (df_obj_all["Bien"] == bien_id)].copy()
        if df_obj_filter.empty:
            df_obj_filter = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12, "Bien": [bien_id]*12})
        
        with st.expander(f"🎯 Objectifs {bien_id} - Année {sel_year}"):
            edited_obj = st.data_editor(df_obj_filter, use_container_width=True, hide_index=True,
                column_config={"Année": None, "Bien": None, "Mois": st.column_config.TextColumn(disabled=True), "Objectif": st.column_config.NumberColumn("Objectif (€)", format="%.2f €")})
            if st.button(f"💾 Sauver Objectifs {bien_id}"):
                df_obj_others = df_obj_all[~((df_obj_all["Année"] == sel_year) & (df_obj_all["Bien"] == bien_id))]
                pd.concat([df_obj_others, edited_obj], ignore_index=True).to_csv(OBJ_FILE, index=False)
                st.rerun()

        st.divider()
        
        # 2. Remplissage des données
        first_day = date(sel_year, sel_month, 1)
        last_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days_list = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        
        resa_bien = df_resa[df_resa["Appartement"].astype(str).str.contains(bien_id)].copy()
        month_data = {d: {"montant": 0.0, "menage": False, "client": ""} for d in days_list}
        
        for _, r in resa_bien.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                delta = (d_dep - d_arr).days
                if delta > 0:
                    px_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr in month_data:
                            month_data[curr]["montant"] = px_nuit
                            month_data[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
                    if d_dep in month_data: month_data[d_dep]["menage"] = True

        real_m = sum(v["montant"] for v in month_data.values())
        nuits = sum(1 for v in month_data.values() if v["montant"] > 0)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Réalisé Mois", f"{real_m:,.2f} €")
        m2.metric("Nb Nuits", f"{nuits} j")
        m3.metric("Prix Moyen", f"{(real_m/nuits if nuits > 0 else 0):,.2f} €")
        m4.metric("% Occupation", f"{(nuits/len(days_list)*100):.1f}%")

        # 3. Graphique & Tableau
        col_g, col_d = st.columns([1, 4])
        with col_g:
            st.subheader(f"Global {sel_year}")
            obj_an = edited_obj["Objectif"].sum() 
            real_an = sum(float(r["Montant"]) for _, r in resa_bien.iterrows() if pd.notnull(r["Date Arrivée"]) and r["Date Arrivée"].year == sel_year)
            st.metric(f"Réalisé {sel_year}", f"{real_an:,.0f} €")
            st.write(f"Cible : {obj_an:,.0f} €")
            st.progress(min(1.0, real_an / obj_an) if obj_an > 0 else 0)

        with col_d:
            rows = [{"Date": d.strftime("%d/%m"), "Montant": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-", "Client": v["client"], "Action": "🟢 Ménage" if v["menage"] else ""} for d,v in month_data.items()]
            st.table(pd.DataFrame(rows).style.apply(lambda x: ['background-color: #2E8B57; color: white' if 'Ménage' in str(x.Action) else '' for i in x], axis=1))

    elif page == "RO 2026": st.title("📈 RO 2026")
