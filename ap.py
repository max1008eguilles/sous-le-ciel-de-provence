import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
try:
    from streamlit_calendar import calendar
except:
    st.error("Le module calendrier charge encore... Patiente 30 secondes.")

# --- CONFIGURATION ---
st.set_page_config(page_title="RNM IMMO - Vision Globale", layout="wide")
DATA_FILE = "data_rnm_immo.csv"
CONFIG_FILE = "config_biens.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: pass
    return pd.DataFrame(columns=columns)

cols_data = ["Date", "Bien", "Locataire", "Source", "Paiement", "Arrivée", "Départ", "Prix Total", "Charges", "Mail", "Tel"]
cols_config = ["Bien", "Prix Achat", "Apport", "Travaux", "Credit Mensuel", "Duree Credit"]

df = load_data(DATA_FILE, cols_data)
df_cfg = load_data(CONFIG_FILE, cols_config)

st.title("🏙️ RNM IMMO - Planning Global")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Planning", "Tableau de Bord", "Saisie Réservation", "Comptabilité", "Configuration"])

# --- 1. PLANNING (CALENDRIER MULTI-BIENS) ---
if menu == "Planning":
    st.subheader("📅 Vue d'ensemble EGUILLES 014 & 119")
    
    # Légende personnalisée
    c1, c2 = st.columns(2)
    c1.markdown("🟦 **EGUILLES 014** (Bleu)")
    c2.markdown("🟥 **EGUILLES 119** (Rouge)")
    
    events = []
    for i, row in df.iterrows():
        # Définition de la couleur selon le BIEN
        couleur = "#1E90FF" if "014" in str(row['Bien']) else "#FF4B4B"
        
        events.append({
            "title": f"{row['Bien']} - {row['Locataire']}",
            "start": str(row['Arrivée']),
            "end": str(row['Départ']),
            "color": couleur,
            "allDay": True,
        })

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek"
        },
        "initialView": "dayGridMonth",
        "locale": "fr", # Calendrier en Français
    }
    
    if "calendar" in globals():
        calendar(events=events, options=calendar_options)
    
    st.divider()
    st.info("💡 Les couleurs te permettent de voir instantanément quel appartement est occupé.")

# --- 2. SAISIE RÉSERVATION (Rappel : Bien choisir le bien ici) ---
elif menu == "Saisie Réservation":
    st.subheader("📩 Nouvelle Réservation")
    with st.form("form_resa"):
        bien = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        loc = st.text_input("Nom Locataire")
        source = st.selectbox("Source", ["Airbnb", "Booking", "Direct"])
        c1, c2 = st.columns(2)
        start = c1.date_input("Arrivée")
        end = c2.date_input("Sortie")
        prix = st.number_input("Prix Total (€)", min_value=0.0)
        paiement = st.selectbox("Mode", ["Virement", "Cash", "Carte"])
        if st.form_submit_button("Enregistrer"):
            new_row = pd.DataFrame([[datetime.now().date(), bien, loc, source, paiement, str(start), str(end), prix, 0, "", ""]], columns=cols_data)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Réservation pour {bien} enregistrée au planning !")
            st.rerun()

# --- Garder les autres menus (Tableau de Bord, Compta, Config) comme avant ---
elif menu == "Tableau de Bord":
    st.subheader("📊 Statistiques")
    if not df.empty:
        st.plotly_chart(px.bar(df, x="Bien", y="Prix Total", color="Bien", title="Revenus par appartement"))
