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
st.set_page_config(page_title="RNM IMMO - Trésorerie", layout="wide")
DATA_FILE = "data_rnm_immo.csv"
COMPTA_FILE = "compta_rnm_immo.csv"
CONFIG_FILE = "config_biens.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: pass
    return pd.DataFrame(columns=columns)

# Structures
cols_resa = ["Date", "Bien", "Locataire", "Source", "Paiement", "Arrivée", "Départ", "Prix Total", "Mail", "Tel"]
cols_compta = ["Date", "Type", "Source_Flux", "Montant", "Catégorie", "Commentaire"]
cols_config = ["Bien", "Prix Achat", "Apport", "Travaux", "Credit Mensuel"]

df_resa = load_data(DATA_FILE, cols_resa)
df_compta = load_data(COMPTA_FILE, cols_compta)
df_cfg = load_data(CONFIG_FILE, cols_config)

st.title("💰 RNM IMMO - Trésorerie & Flux")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Trésorerie & Compta", "Planning", "Saisie Réservation", "Rentabilité Projet", "Configuration"])

# --- 1. TRÉSORERIE & COMPTA (NOUVEAU) ---
if menu == "Trésorerie & Compta":
    st.subheader("💳 Suivi des Comptes & Cash")
    
    # Calcul des soldes
    def calc_solde(flux):
        entrees = df_compta[(df_compta["Source_Flux"] == flux) & (df_compta["Type"] == "Revenu")]["Montant"].sum()
        sorties = df_compta[(df_compta["Source_Flux"] == flux) & (df_compta["Type"] == "Dépense")]["Montant"].sum()
        return entrees - sorties

    solde_banque = calc_solde("Compte Société")
    solde_cash = calc_solde("Cash")

    c1, c2, c3 = st.columns(3)
    c1.metric("Solde Compte Société", f"{solde_banque:,.2f} €")
    c2.metric("Solde Cash", f"{solde_cash:,.2f} €")
    c3.metric("Trésorerie Totale", f"{(solde_banque + solde_cash):,.2f} €")

    st.divider()
    
    # Formulaire de saisie comptable
    with st.expander("➕ Enregistrer une opération (Dépense / Recette)"):
        with st.form("form_compta"):
            col1, col2, col3 = st.columns(3)
            t_op = col1.selectbox("Type", ["Dépense", "Revenu"])
            source_f = col2.selectbox("Destination / Source", ["Compte Société", "Cash"])
            montant = col3.number_input("Montant (€)", min_value=0.0)
            
            cat = st.selectbox("Catégorie", ["Loyer", "Charges", "Travaux", "Assurance", "Divers"])
            comm = st.text_area("Commentaire / Détails")
            
            if st.form_submit_button("Valider l'opération"):
                new_op = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), t_op, source_f, montant, cat, comm]], columns=cols_compta)
                df_compta = pd.concat([df_compta, new_op], ignore_index=True)
                df_compta.to_csv(COMPTA_FILE, index=False)
                st.success("Opération enregistrée !")
                st.rerun()

    st.subheader("📜 Historique des flux")
    st.dataframe(df_compta.sort_values("Date", ascending=False), use_container_width=True)

# --- 2. PLANNING ---
elif menu == "Planning":
    st.subheader("📅 Planning Global")
    events = []
    for i, row in df_resa.iterrows():
        color = "#1E90FF" if "014" in str(row['Bien']) else "#FF4B4B"
        events.append({"title": f"{row['Bien']} - {row['Locataire']}", "start": str(row['Arrivée']), "end": str(row['Départ']), "color": color})
    calendar(events=events, options={"locale": "fr"})

# --- 3. SAISIE RÉSERVATION ---
elif menu == "Saisie Réservation":
    with st.form("resa"):
        bien = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        loc = st.text_input("Locataire")
        prix = st.number_input("Prix Total", min_value=0.0)
        mode = st.selectbox("Paiement", ["Virement", "Cash"])
        start = st.date_input("Arrivée")
        end = st.date_input("Sortie")
        if st.form_submit_button("Enregistrer"):
            # 1. Enregistre la résa
            new_r = pd.DataFrame([[datetime.now().date(), bien, loc, "Direct", mode, str(start), str(end), prix, "", ""]], columns=cols_resa)
            pd.concat([df_resa, new_r], ignore_index=True).to_csv(DATA_FILE, index=False)
            # 2. Ajoute automatiquement à la compta
            dest = "Compte Société" if mode == "Virement" else "Cash"
            new_c = pd.DataFrame([[str(start), "Revenu", dest, prix, "Loyer", f"Résa {loc} - {bien}"]], columns=cols_compta)
            pd.concat([df_compta, new_c], ignore_index=True).to_csv(COMPTA_FILE, index=False)
            st.success("Réservation et flux comptable enregistrés !")
            st.rerun()

# --- 4. RENTABILITÉ PROJET ---
elif menu == "Rentabilité Projet":
    # ... (Code précédent pour calculer la renta achat/travaux vs revenus totaux)
    st.info("Ici tu visualises la rentabilité brute vs investissement initial.")

# --- 5. CONFIGURATION ---
elif menu == "Configuration":
    with st.form("cfg"):
        b = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        p = st.number_input("Prix Achat")
        t = st.number_input("Travaux")
        m = st.number_input("Mensualité")
        if st.form_submit_button("Sauvegarder"):
            new_cfg = pd.DataFrame([[b, p, 0, t, m]], columns=cols_config)
            pd.concat([df_cfg[df_cfg["Bien"] != b], new_cfg], ignore_index=True).to_csv(CONFIG_FILE, index=False)
            st.success("Config enregistrée.")
