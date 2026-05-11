import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
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
            df = pd.read_csv(RESA_FILE)
            # Conversion forcée pour éviter les erreurs st.data_editor
            df["Date Arrivée"] = pd.to_datetime(df["Date Arrivée"], errors='coerce').dt.date
            df["Date Départ"] = pd.to_datetime(df["Date Départ"], errors='coerce').dt.date
            return df
        return pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant", "Numéro tel", "Mail", "Code Résidence", "Code Studio", "Code Autre"])

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()

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

    # --- PAGE RNM IMMO (STRICTEMENT INCHANGÉE) ---
    if page == "RNM IMMO":
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
            cols_save = [c for c in edited_df.columns if c not in ["Capital Restant", "Patrimoine Net Bien", "% Net", "% Dette"]]
            edited_df[cols_save].to_csv(CONFIG_FILE, index=False)
            st.rerun()
        if not df_cfg.empty:
            st.divider()
            st.subheader("📊 Détail par Bien")
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            for i, row in df_cfg.iterrows():
                fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net Bien']/2, text=f"<b>{row['Patrimoine Net Bien']:,.0f}€</b><br>{row['% Net']:.1f}%", showarrow=False, font=dict(color="white"))
                if row['Capital Restant'] > 500:
                    fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net Bien'] + (row['Capital Restant']/2), text=f"<b>{row['Capital Restant']:,.0f}€</b><br>{row['% Dette']:.1f}%", showarrow=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA (STRICTEMENT INCHANGÉE) ---
    elif page == "COMPTA":
        st.title("💰 Comptabilité - RNM IMMO")
        c1, c2, c3 = st.columns(3)
        c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
        c2.metric("Montant Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL TRESORERIE", f"{total_treso_dynamique:,.2f} €")
        st.divider()
        ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder"):
            ed_c.to_csv(COMPTA_FILE, index=False)
            st.rerun()

    # --- PAGE RÉSERVATIONS (COULEURS RECTIFIÉES) ---
    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        
        # Sécurité pour le calcul automatique du Code Autre
        df_resa["Code Résidence"] = df_resa["Code Résidence"].fillna("").astype(str)
        df_resa["Code Autre"] = df_resa["Code Résidence"].apply(lambda x: x[:-1] if len(x) > 1 else "")

        # Tableau des réservations avec sécurité sur les dates
        edited_resa = st.data_editor(
            df_resa, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Date Arrivée": st.column_config.DateColumn("Arrivée"),
                "Date Départ": st.column_config.DateColumn("Départ"),
                "Appartement": st.column_config.SelectboxColumn("Appartement", options=["014", "119"]),
                "Code Autre": st.column_config.TextColumn("Code Autre", disabled=True)
            }
        )
        
        if st.button("💾 Sauvegarder Réservations"):
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()

        st.divider()
        st.subheader("🗓️ Calendrier Mensuel")
        evts = []
        for _, r in edited_resa.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                # --- RECTIFICATION DES COULEURS ---
                # Bleu pour le 014, Vert pour le 119
                # On vérifie si la chaîne contient "014" ou "119"
                apt_str = str(r["Appartement"])
                color = "#1E90FF" if "014" in apt_str else "#2E8B57" if "119" in apt_str else "#808080"
                
                evts.append({
                    "title": f"[{apt_str}] {r['Prénom_Nom']}", 
                    "start": str(r["Date Arrivée"]), 
                    "end": str(r["Date Départ"]), 
                    "color": color, 
                    "allDay": True
                })
        
        calendar(events=evts, options={"initialView": "dayGridMonth", "locale": "fr"})

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page in ["Détail 014", "Détail 119"]: st.title(f"🏠 {page}")
