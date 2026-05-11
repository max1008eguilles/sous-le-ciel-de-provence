import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIG DE LA PAGE ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")

# --- SÉCURITÉ MULTI-UTILISATEURS ---
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
        st.text_input("Identifiant (Robin, Nathan ou Maxence)", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🏛️ Accès RNM IMMO")
        st.text_input("Identifiant (Robin, Nathan ou Maxence)", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        st.error("🚫 Identifiant ou mot de passe incorrect.")
        return False
    else:
        return True

if check_password():
    
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"

    def load_config():
        cols = ["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", 
                "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
        if os.path.exists(CONFIG_FILE):
            df = pd.read_csv(CONFIG_FILE)
            if "Date Début" in df.columns:
                df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
            return df
        return pd.DataFrame(columns=cols)

    def load_compta():
        cols = ["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"]
        if os.path.exists(COMPTA_FILE):
            df = pd.read_csv(COMPTA_FILE)
            df["Date"] = pd.to_datetime(df["Date"])
            df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0)
            return df
        return pd.DataFrame(columns=cols)

    df_compta = load_compta()
    df_cfg = load_config()

    # --- CALCULS TRESORERIE ---
    def get_solde(compte_nom):
        if df_compta.empty: return 0.0
        df_c = df_compta[df_compta["Compte"] == compte_nom]
        rev = df_c[df_c["Type"] == "Revenu"]["Montant"].sum()
        dep = df_c[df_c["Type"] == "Dépense"]["Montant"].sum()
        cre = df_c[df_c["Type"] == "Crédit"]["Montant"].sum() # Prise en compte du type Crédit
        return float(rev - dep - cre)

    solde_cic = get_solde("CIC")
    solde_cash_physique = get_solde("Cash")
    total_treso_dynamique = solde_cic + solde_cash_physique

    # --- BARRE LATÉRALE ---
    with st.sidebar:
        st.title("📂 Navigation")
        current_user = st.session_state.get('user_authenticated', 'Utilisateur')
        st.write(f"👤 Connecté : **{current_user}**")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE RNM IMMO ---
    if page == "RNM IMMO":
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

        st.title("🏛️ RNM IMMO - Tableau de Bord")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net:,.0f} €")

        st.divider()
        st.subheader("⚙️ Configuration des Biens")
        edited_df = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Biens"):
            edited_df.to_csv(CONFIG_FILE, index=False)
            st.rerun()

        if not df_cfg.empty:
            st.divider()
            st.subheader("📊 Détail par Bien")
            df_plot = df_cfg.copy()
            fig = px.bar(df_plot, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA ---
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
                t = st.selectbox("Type", ["Revenu", "Dépense", "Crédit"])
                cpt = st.selectbox("Compte", ["CIC", "Cash"])
                m = st.number_input("Montant", min_value=0.0)
                txt = st.text_input("Commentaire")
                if st.form_submit_button("Valider"):
                    new = pd.DataFrame([[pd.to_datetime(d), t, cpt, m, txt, False]], columns=df_compta.columns)
                    pd.concat([df_compta, new], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                    st.rerun()
        
        with col_list:
            st.subheader("📝 Journal")
            ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Sauvegarder Compta"):
                ed_c.to_csv(COMPTA_FILE, index=False)
                st.rerun()

        # --- SECTION RÉCAP MOIS ET ANNÉE ---
        if not df_compta.empty:
            st.divider()
            col_m, col_y = st.columns(2)
            
            with col_m:
                st.subheader("🗓️ Récapitulatif Mensuel")
                df_m = df_compta.copy()
                df_m['Mois'] = df_m['Date'].dt.strftime('%Y-%m')
                recap_m = df_m.groupby(['Mois', 'Type'])['Montant'].sum().unstack(fill_value=0)
                for col in ["Revenu", "Dépense", "Crédit"]:
                    if col not in recap_m.columns: recap_m[col] = 0.0
                recap_m = recap_m.rename(columns={"Revenu": "Revenus", "Dépense": "Charges", "Crédit": "Crédit"})
                recap_m["Cash Flow"] = recap_m["Revenus"] - recap_m["Charges"] - recap_m["Crédit"]
                st.table(recap_m.sort_index(ascending=False).style.format("{:,.2f} €"))

            with col_y:
                st.subheader("📅 Récapitulatif Annuel")
                df_y = df_compta.copy()
                df_y['Année'] = df_y['Date'].dt.strftime('%Y')
                recap_y = df_y.groupby(['Année', 'Type'])['Montant'].sum().unstack(fill_value=0)
                for col in ["Revenu", "Dépense", "Crédit"]:
                    if col not in recap_y.columns: recap_y[col] = 0.0
                recap_y = recap_y.rename(columns={"Revenu": "Total Revenus", "Dépense": "Total Charges", "Crédit": "Total Crédit"})
                recap_y["Cash Flow Annuel"] = recap_y["Total Revenus"] - recap_y["Total Charges"] - recap_y["Total Crédit"]
                st.table(recap_y.sort_index(ascending=False).style.format("{:,.2f} €"))
        else:
            st.info("Ajoutez des données pour voir les analyses.")
