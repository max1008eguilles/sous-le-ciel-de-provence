import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- SÉCURITÉ ---
def check_password():
    """Retourne True si l'utilisateur a saisi le bon mot de passe."""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Accès Restreint - RNM IMMO")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Accès Restreint - RNM IMMO")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        st.error("😕 Mot de passe incorrect.")
        return False
    else:
        return True

if check_password():
    # --- TOUT TON CODE INITIAL COMMENCE ICI ---
    
    # CONFIG
    st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"

    # CHARGEMENT DES DONNÉES
    def load_config():
        cols = ["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", 
                "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
        if os.path.exists(CONFIG_FILE):
            df = pd.read_csv(CONFIG_FILE)
            if "Valeur Actuelle" not in df.columns: df["Valeur Actuelle"] = 0
            df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
            return df
        return pd.DataFrame(columns=cols)

    def load_compta():
        cols = ["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"]
        if os.path.exists(COMPTA_FILE):
            df = pd.read_csv(COMPTA_FILE)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)
            return df
        return pd.DataFrame(columns=cols)

    # CALCULS TRESORERIE
    df_compta = load_compta()
    def get_solde(compte_nom):
        if df_compta.empty: return 0.0
        df_c = df_compta[df_compta["Compte"] == compte_nom]
        rev = df_c[df_c["Type"] == "Revenu"]["Montant"].sum()
        dep = df_c[df_c["Type"] == "Dépense"]["Montant"].sum()
        return float(rev - dep)

    solde_cic = get_solde("CIC")
    solde_cash_physique = get_solde("Cash")
    total_treso_dynamique = solde_cic + solde_cash_physique

    # MENU LATÉRAL
    with st.sidebar:
        st.title("📂 Navigation")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # PAGE RNM IMMO
    if page == "RNM IMMO":
        df_cfg = load_config()
        if not df_cfg.empty:
            for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
                df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
            
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
            total_net = (total_brut + total_treso_dynamique) - total_crd
            df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
        else:
            total_brut = total_crd = total_net = 0

        st.title("🏛️ RNM IMMO - Tableau de Bord Financier")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net:,.0f} €")

        st.divider()
        st.subheader("⚙️ Configuration Précise des Biens")
        edited_df = st.data_editor(df_cfg[["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]], num_rows="dynamic", use_container_width=True, column_config={"Date Début": st.column_config.DateColumn("Date Début", format="DD/MM/YYYY")})
        if st.button("💾 Sauvegarder Biens"):
            edited_df.to_csv(CONFIG_FILE, index=False)
            st.rerun()

        if not df_cfg.empty:
            st.divider()
            st.subheader("📊 Détail par Bien (Répartition %)")
            df_plot = df_cfg.copy()
            df_plot['val_ref'] = df_plot['Valeur Actuelle'].apply(lambda x: x if x > 0 else 1)
            df_plot['% Net'] = (df_plot['Patrimoine Net Bien'] / df_plot['val_ref'] * 100).round(1).astype(str) + '%'
            df_plot['% Dette'] = (df_plot['Capital Restant'] / df_plot['val_ref'] * 100).round(1).astype(str) + '%'
            fig = px.bar(df_plot, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            fig.update_traces(name="Patrimoine Net", selector=dict(name="Patrimoine Net Bien"), text=df_plot['% Net'], textposition='inside')
            fig.update_traces(name="Capital Restant", selector=dict(name="Capital Restant"), text=df_plot['% Dette'], textposition='inside')
            st.plotly_chart(fig, use_container_width=True)

    # PAGE COMPTA
    elif page == "COMPTA":
        st.title("💰 Comptabilité - RNM IMMO")
        c1, c2, c3 = st.columns(3)
        c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
        c2.metric("Montant Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL TRESORERIE", f"{total_treso_dynamique:,.2f} €")
        st.divider()
        col_add, col_list = st.columns([1, 2])
        with col_add:
            st.subheader("➕ Ajouter")
            with st.form("f_compta"):
                d = st.date_input("Date", date.today())
                t = st.selectbox("Type", ["Revenu", "Dépense"])
                cpt = st.selectbox("Compte", ["CIC", "Cash"])
                m = st.number_input("Montant", min_value=0.0)
                txt = st.text_input("Commentaire")
                check = st.checkbox("Justificatif ?")
                if st.form_submit_button("Valider"):
                    new = pd.DataFrame([[d, t, cpt, m, txt, check]], columns=df_compta.columns)
                    pd.concat([df_compta, new], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                    st.rerun()
        with col_list:
            st.subheader("📝 Journal")
            st.caption("💡 Cliquez à gauche d'une ligne, puis 'Suppr' pour supprimer.")
            ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True, column_config={"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"), "Justificatif": st.column_config.CheckboxColumn("Justificatif")})
            if st.button("💾 Sauvegarder Compta"):
                ed_c.to_csv(COMPTA_FILE, index=False)
                st.rerun()
