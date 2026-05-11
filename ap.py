import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
try:
    from streamlit_calendar import calendar
except:
    st.error("Installation des modules... Patiente 30 secondes.")

# --- CONFIGURATION ---
st.set_page_config(page_title="RNM IMMO - Full Management", layout="wide")
DATA_FILE = "data_rnm_immo.csv"
COMPTA_FILE = "compta_rnm_immo.csv"
CONFIG_FILE = "config_biens.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: pass
    return pd.DataFrame(columns=columns)

cols_resa = ["ID", "Date", "Bien", "Locataire", "Source", "Paiement", "Arrivée", "Départ", "Prix Total", "Mail", "Tel"]
cols_compta = ["ID", "Date", "Type", "Source_Flux", "Montant", "Catégorie", "Commentaire"]
cols_config = ["Bien", "Prix Achat", "Apport", "Travaux", "Credit Mensuel"]

df_resa = load_data(DATA_FILE, cols_resa)
df_compta = load_data(COMPTA_FILE, cols_compta)
df_cfg = load_data(CONFIG_FILE, cols_config)

st.title("🏛️ RNM IMMO - Pilotage Complet")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Planning & Résas", "Trésorerie & Compta", "Saisie Réservation", "Rentabilité Projet", "Configuration", "Admin / Modification"])

# --- 1. PLANNING & RÉSERVATIONS ---
if menu == "Planning & Résas":
    st.subheader("📅 Planning Global")
    events = []
    for i, row in df_resa.iterrows():
        color = "#1E90FF" if "014" in str(row['Bien']) else "#FF4B4B"
        events.append({"title": f"{row['Bien']} - {row['Locataire']}", "start": str(row['Arrivée']), "end": str(row['Départ']), "color": color})
    
    if "calendar" in globals():
        calendar(events=events, options={"locale": "fr"})
    
    st.divider()
    st.subheader("📋 Historique des Réservations")
    if not df_resa.empty:
        st.dataframe(df_resa.sort_values("Arrivée", ascending=False), use_container_width=True)
    else:
        st.info("Aucune réservation enregistrée.")

# --- 2. TRÉSORERIE & COMPTA ---
elif menu == "Trésorerie & Compta":
    st.subheader("💳 État des Comptes")
    def calc_solde(flux):
        entrees = pd.to_numeric(df_compta[(df_compta["Source_Flux"] == flux) & (df_compta["Type"] == "Revenu")]["Montant"]).sum()
        sorties = pd.to_numeric(df_compta[(df_compta["Source_Flux"] == flux) & (df_compta["Type"] == "Dépense")]["Montant"]).sum()
        return entrees - sorties

    c1, c2, c3 = st.columns(3)
    c1.metric("Compte Société", f"{calc_solde('Compte Société'):,.2f} €")
    c2.metric("Cash", f"{calc_solde('Cash'):,.2f} €")
    c3.metric("Total", f"{(calc_solde('Compte Société') + calc_solde('Cash')):,.2f} €")

    st.divider()
    with st.expander("➕ Ajouter une opération Manuelle"):
        with st.form("compta_man"):
            t_op = st.selectbox("Type", ["Dépense", "Revenu"])
            src = st.selectbox("Flux", ["Compte Société", "Cash"])
            mnt = st.number_input("Montant", min_value=0.0)
            cat = st.selectbox("Catégorie", ["Charges", "Travaux", "Assurance", "Loyer", "Autre"])
            txt = st.text_input("Commentaire")
            if st.form_submit_button("Enregistrer"):
                new_id = datetime.now().strftime("%Y%m%d%H%M%S")
                new_op = pd.DataFrame([[new_id, datetime.now().strftime("%Y-%m-%d"), t_op, src, mnt, cat, txt]], columns=cols_compta)
                pd.concat([df_compta, new_op], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                st.rerun()

    st.dataframe(df_compta.sort_values("Date", ascending=False), use_container_width=True)

# --- 3. SAISIE RÉSERVATION ---
elif menu == "Saisie Réservation":
    with st.form("resa_new"):
        st.subheader("Nouvelle entrée")
        b = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        l = st.text_input("Nom Locataire")
        p = st.number_input("Prix Total", min_value=0.0)
        m = st.selectbox("Paiement", ["Virement", "Cash"])
        s = st.date_input("Arrivée")
        e = st.date_input("Sortie")
        if st.form_submit_button("Valider"):
            rid = datetime.now().strftime("R%Y%m%d%H%M%S")
            # Enregistre Résa
            nr = pd.DataFrame([[rid, datetime.now().date(), b, l, "Direct", m, str(s), str(e), p, "", ""]], columns=cols_resa)
            pd.concat([df_resa, nr], ignore_index=True).to_csv(DATA_FILE, index=False)
            # Enregistre Compta auto
            dest = "Compte Société" if m == "Virement" else "Cash"
            nc = pd.DataFrame([[rid, str(s), "Revenu", dest, p, "Loyer", f"Résa {l} - {b}"]], columns=cols_compta)
            pd.concat([df_compta, nc], ignore_index=True).to_csv(COMPTA_FILE, index=False)
            st.success("C'est en ligne !")
            st.rerun()

# --- 6. ADMIN / MODIFICATION (NOUVEAU) ---
elif menu == "Admin / Modification":
    st.subheader("🛠️ Modifier ou Supprimer des données")
    
    tab1, tab2 = st.tabs(["Réservations", "Trésorerie"])
    
    with tab1:
        if not df_resa.empty:
            id_del = st.selectbox("Choisir une résa à supprimer (par ID)", df_resa["ID"].tolist())
            if st.button("Supprimer cette réservation"):
                # Supprime de la résa ET de la compta (car ils partagent le même ID)
                df_resa = df_resa[df_resa["ID"] != id_del]
                df_compta = df_compta[df_compta["ID"] != id_del]
                df_resa.to_csv(DATA_FILE, index=False)
                df_compta.to_csv(COMPTA_FILE, index=False)
                st.success("Réservation et flux associé supprimés !")
                st.rerun()
        else: st.write("Rien à supprimer.")

    with tab2:
        if not df_compta.empty:
            id_c = st.selectbox("Choisir une transaction à supprimer", df_compta["ID"].tolist())
            st.write(df_compta[df_compta["ID"] == id_c])
            if st.button("Supprimer cette transaction"):
                df_compta = df_compta[df_compta["ID"] != id_c]
                df_compta.to_csv(COMPTA_FILE, index=False)
                st.success("Transaction supprimée !")
                st.rerun()

# --- Garder les autres menus simplified pour la lecture ---
elif menu == "Rentabilité Projet":
    st.info("Visualisation de la rentabilité projet")
elif menu == "Configuration":
    st.info("Configuration des biens")
