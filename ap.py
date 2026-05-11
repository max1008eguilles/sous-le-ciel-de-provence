import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIG ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")
CONFIG_FILE = "config_biens_v3.csv"
COMPTA_FILE = "compta_v3.csv"

# --- CHARGEMENT DES DONNÉES ---
def load_config():
    cols = ["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", 
            "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
    if os.path.exists(CONFIG_FILE):
        df = pd.read_csv(CONFIG_FILE)
        df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
        return df
    return pd.DataFrame(columns=cols)

def load_compta():
    cols = ["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"]
    if os.path.exists(COMPTA_FILE):
        df = pd.read_csv(COMPTA_FILE)
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        return df
    return pd.DataFrame(columns=cols)

# --- CALCULS ---
df_compta = load_compta()

def get_solde(compte_nom):
    if df_compta.empty: return 0.0
    df_c = df_compta[df_compta["Compte"] == compte_nom]
    revenus = df_c[df_c["Type"] == "Revenu"]["Montant"].sum()
    depenses = df_c[df_c["Type"] == "Dépense"]["Montant"].sum()
    return float(revenus - depenses)

solde_cic = get_solde("CIC")
solde_cash = get_solde("Cash")
total_treso = solde_cic + solde_cash

# --- BARRE LATÉRALE (MENU) ---
with st.sidebar:
    st.title("📂 Navigation")
    page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA"])
    st.divider()
    st.metric("Total Trésorerie", f"{total_treso:,.2f} €")

# --- PAGE RNM IMMO (Dashboard Initial) ---
if page == "RNM IMMO":
    df_cfg = load_config()
    # Le Cash disponible est maintenant dynamique !
    cash_total_pour_dashboard = total_treso 

    if not df_cfg.empty:
        for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
            df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
        
        # Fonctions calcul CRD (identique à avant)
        def calc_crd(row):
            try:
                P, r, n = float(row["Montant Crédit"]), (float(row["Taux (%)"])/100)/12, int(row["Durée (mois)"])
                diff = relativedelta(date.today(), row["Date Début"])
                m = diff.years * 12 + diff.months
                if m <= 0: return P
                if m >= n: return 0
                return P * ((1 + r)**n - (1 + r)**m) / ((1 + r)**n - 1)
            except: return 0

        total_brut = df_cfg["Valeur Actuelle"].sum()
        df_cfg["Capital Restant"] = df_cfg.apply(calc_crd, axis=1)
        total_crd = df_cfg["Capital Restant"].sum()
        total_net = (total_brut + cash_total_pour_dashboard) - total_crd
        df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
    else:
        total_brut = total_crd = total_net = 0

    st.title("🏛️ RNM IMMO - Tableau de Bord Financier")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
    m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
    m3.metric("Cash disponible", f"{cash_total_pour_dashboard:,.2f} €")
    m4.metric("Patrimoine Net", f"{total_net:,.0f} €")

    st.divider()
    st.subheader("⚙️ Configuration Précise des Biens")
    edited_df = st.data_editor(df_cfg[["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]], num_rows="dynamic", use_container_width=True, column_config={"Date Début": st.column_config.DateColumn("Date Début", format="DD/MM/YYYY")})
    if st.button("💾 Sauvegarder Biens"):
        edited_df.to_csv(CONFIG_FILE, index=False)
        st.rerun()

# --- PAGE COMPTA (Nouvelle Section) ---
elif page == "COMPTA":
    st.title("💰 Comptabilité - RNM IMMO")
    
    # Affichage des soldes demandés
    c1, c2, c3 = st.columns(3)
    c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
    c2.metric("Montant Cash", f"{solde_cash:,.2f} €")
    c3.metric("TOTAL TRESORERIE", f"{total_treso:,.2f} €")

    st.divider()
    
    col_add, col_list = st.columns([1, 3])
    
    with col_add:
        st.subheader("➕ Nouvelle Transaction")
        with st.form("form_compta"):
            d = st.date_input("Date", date.today())
            t = st.selectbox("Type", ["Revenu", "Dépense"])
            cpt = st.selectbox("Compte", ["CIC", "Cash"])
            m = st.number_input("Montant", min_value=0.0)
            txt = st.text_input("Commentaire")
            check = st.checkbox("Justificatif déposé ?")
            if st.form_submit_button("Ajouter la transaction"):
                new_row = pd.DataFrame([[d, t, cpt, m, txt, check]], columns=df_compta.columns)
                pd.concat([df_compta, new_row], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                st.rerun()

    with col_list:
        st.subheader("📝 Journal des Transactions")
        st.caption("Double-clique pour modifier. Sélectionne une ligne et appuie sur 'Suppr' pour effacer.")
        # Tableau éditable avec case à cocher pour justificatif
        edited_compta = st.data_editor(
            df_compta,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "Type": st.column_config.SelectboxColumn("Type", options=["Revenu", "Dépense"]),
                "Compte": st.column_config.SelectboxColumn("Compte", options=["CIC", "Cash"]),
                "Justificatif": st.column_config.CheckboxColumn("Justificatif")
            }
        )
        if st.button("💾 Enregistrer modifications Compta"):
            edited_compta.to_csv(COMPTA_FILE, index=False)
            st.rerun()
