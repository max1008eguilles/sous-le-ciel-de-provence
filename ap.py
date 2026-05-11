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

    # --- CHARGEMENT DES DONNÉES ---
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

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()

    # --- CALCUL TRÉSORERIE ---
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
        st.write(f"👤 Connecté : **{st.session_state.get('user_authenticated')}**")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Réservations", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGES EXISTANTES (INCHANGÉES) ---
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Tableau de Bord")
        # ... (Logique Patrimoine identique)
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
        st.data_editor(df_cfg, use_container_width=True)

    elif page == "COMPTA":
        st.title("💰 Comptabilité")
        # ... (Logique Compta identique)
        st.write("Gestion des flux financiers.")
        ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Compta"):
            ed_c.to_csv(COMPTA_FILE, index=False)
            st.rerun()

    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        edited_resa = st.data_editor(df_resa, num_rows="dynamic", use_container_width=True,
            column_config={
                "Appartement": st.column_config.SelectboxColumn("Appartement", options=["014", "119"]),
                "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
                "Mail": st.column_config.TextColumn("Mail")
            })
        if st.button("💾 Sauvegarder Réservations"):
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()

    # --- NOUVELLE PAGE DÉTAIL 014 (LOGIQUE EXCEL RESTAURÉE) ---
    elif page == "Détail 014":
        st.title("🏠 Détail Local 014")
        
        # Filtre Année / Mois
        col_f1, col_f2 = st.columns(2)
        sel_year = col_f1.selectbox("Année", [2024, 2025, 2026], index=2)
        sel_month = col_f2.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)
        
        # --- LOGIQUE DE CALCUL ---
        # 1. On filtre les résas de l'appart 014
        resa_014 = df_resa[df_resa["Appartement"].isin(["014", "14"])].copy()
        
        # 2. On crée le dictionnaire des jours du mois
        num_days = (date(sel_year, sel_month % 12 + 1, 1) - date(sel_year, sel_month, 1)).days if sel_month < 12 else 31
        days_list = [date(sel_year, sel_month, d) for d in range(1, num_days + 1)]
        
        data_month = {d: {"montant": 0.0, "menage": False, "client": ""} for d in days_list}
        
        for _, r in resa_014.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                # Calcul prix par nuit
                delta = (r["Date Départ"] - r["Date Arrivée"]).days
                if delta > 0:
                    prix_nuit = float(r["Montant"]) / delta
                    # On remplit chaque jour
                    curr = r["Date Arrivée"]
                    while curr < r["Date Départ"]:
                        if curr in data_month:
                            data_month[curr]["montant"] = prix_nuit
                            data_month[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
                    # On marque le jour du ménage (Date Départ)
                    if r["Date Départ"] in data_month:
                        data_month[r["Date Départ"]]["menage"] = True

        # --- AFFICHAGE INDICATEURS HAUT ---
        realise_mois = sum(v["montant"] for v in data_month.values())
        nb_nuits = sum(1 for v in data_month.values() if v["montant"] > 0)
        prix_moyen = realise_mois / nb_nuits if nb_nuits > 0 else 0
        occ_rate = (nb_nuits / num_days) * 100
        
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Réalisé Mois", f"{realise_mois:,.2f} €")
        h2.metric("Nb Nuits", f"{nb_nuits} j")
        h3.metric("Prix Moyen / Nuit", f"{prix_moyen:,.2f} €")
        h4.metric("% Occupation", f"{occ_rate:.1f} %")

        st.divider()

        # --- LAYOUT : GAUCHE (ANNÉE) | CENTRE (TABLEAU) ---
        col_left, col_main = st.columns([1, 4])
        
        with col_left:
            st.subheader("Objectif Annuel")
            obj_an = 14000.0 # À modifier si besoin
            # Calcul réalisé annuel
            realise_an = 0
            for _, r in resa_014.iterrows():
                if pd.notnull(r["Date Arrivée"]) and r["Date Arrivée"].year == sel_year:
                    realise_an += float(r["Montant"])
            
            st.write(f"Cible : **{obj_an:,.0f} €**")
            st.metric("Réalisé 2026", f"{realise_an:,.2f} €")
            st.metric("Restant", f"{max(0, obj_an - realise_an):,.2f} €", delta_color="inverse")
            st.progress(min(1.0, realise_an / obj_an))

        with col_main:
            # Construction du tableau visuel
            table_rows = []
            for d in days_list:
                style = ""
                if data_month[d]["menage"]: style = "🟢 Ménage"
                elif data_month[d]["montant"] > 0: style = "🏨 Réservé"
                
                table_rows.append({
                    "Date": d.strftime("%d/%m"),
                    "Jour": d.strftime("%A"),
                    "Montant": f"{data_month[d]['montant']:.2f} €" if data_month[d]['montant'] > 0 else "-",
                    "Client": data_month[d]['client'],
                    "Note": style
                })
            
            df_display = pd.DataFrame(table_rows)
            
            def color_rows(row):
                if "Ménage" in str(row.Note): return ['background-color: #2E8B57'] * len(row)
                if "Réservé" in str(row.Note): return ['background-color: #333333'] * len(row)
                return [''] * len(row)

            st.table(df_display.style.apply(color_rows, axis=1))

            # --- BAS DU TABLEAU (OBJECTIF MENSUEL) ---
            st.divider()
            obj_mois = 1250.0 # Exemple d'objectif
            b1, b2 = st.columns(2)
            with b1:
                st.info(f"🎯 Objectif du mois : **{obj_mois:,.2f} €**")
            with b2:
                pct_obj = (realise_mois / obj_mois) * 100 if obj_mois > 0 else 0
                st.write(f"**Performance : {pct_obj:.1f} %**")

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page == "Détail 119": st.title("🏠 Détail 119")
