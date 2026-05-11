import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from streamlit_calendar import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="RNM IMMO - Expert LCD", layout="wide")
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

st.title("🏛️ RNM IMMO - Gestion & Planning")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Planning", "Tableau de Bord", "Saisie Réservation", "Comptabilité & Rentabilité", "Configuration"])

# --- 1. PLANNING (CALENDRIER) ---
if menu == "Planning":
    st.subheader("📅 Calendrier des disponibilités")
    bien_visu = st.selectbox("Choisir le bien à visualiser", ["EGUILLES 014", "EGUILLES 119"])
    
    # Préparation des événements pour le calendrier
    events = []
    df_bien = df[df["Bien"] == bien_visu]
    
    for i, row in df_bien.iterrows():
        events.append({
            "title": f"🔴 {row['Locataire']} ({row['Source']})",
            "start": str(row['Arrivée']),
            "end": str(row['Départ']),
            "color": "#FF4B4B" if row['Source'] == "Airbnb" else "#1E90FF",
        })

    calendar_options = {
        "editable": "true",
        "selectable": "true",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek",
        },
        "initialView": "dayGridMonth",
    }
    
    calendar(events=events, options=calendar_options)
    st.info("💡 Bleu = Booking / Direct | Rouge = Airbnb")

# --- 2. SAISIE RÉSERVATION ---
elif menu == "Saisie Réservation":
    st.subheader("📩 Nouvelle Réservation")
    with st.form("form_resa"):
        c1, c2, c3 = st.columns(3)
        bien = c1.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        locataire = c2.text_input("Nom Prénom Locataire")
        source = c3.selectbox("Source", ["Airbnb", "Booking", "Direct"])
        
        c4, c5 = st.columns(2)
        start = c4.date_input("Date Arrivée")
        end = c5.date_input("Date Sortie")
        
        c6, c7, c8 = st.columns(3)
        prix = c6.number_input("Prix Total (€)", min_value=0.0)
        paiement = c7.selectbox("Mode de paiement", ["Virement", "Cash", "Carte"])
        tel = c8.text_input("Téléphone")
        
        if st.form_submit_button("Enregistrer"):
            new_row = pd.DataFrame([[datetime.now().date(), bien, locataire, source, paiement, str(start), str(end), prix, 0, "", tel]], columns=cols_data)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Réservation ajoutée au planning !")
            st.rerun()

# --- 3. TABLEAU DE BORD (STATS) ---
elif menu == "Tableau de Bord":
    if not df.empty:
        st.subheader("📊 Statistiques de performance")
        # Calculs Taux d'occupation
        df['Arrivée'] = pd.to_datetime(df['Arrivée'])
        df['Départ'] = pd.to_datetime(df['Départ'])
        df['Nuits'] = (df['Départ'] - df['Arrivée']).dt.days
        
        c1, c2, c3 = st.columns(3)
        c1.metric("CA Cumulé", f"{df['Prix Total'].sum():,.2f} €")
        c2.metric("Durée Moyenne", f"{df['Nuits'].mean():.1f} nuits")
        c3.metric("Total Nuits", int(df['Nuits'].sum()))
        
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("📈 % par Mode de Paiement")
            st.plotly_chart(px.pie(df, values='Prix Total', names='Paiement'), use_container_width=True)
        with col_b:
            st.write("📊 % par Plateforme")
            st.plotly_chart(px.pie(df, values='Prix Total', names='Source'), use_container_width=True)
    else:
        st.warning("Aucune donnée. Enregistrez une réservation d'abord.")

# --- 4. COMPTABILITÉ & RENTA ---
elif menu == "Comptabilité & Rentabilité":
    st.subheader("💰 Rentabilité du Projet")
    for b in ["EGUILLES 014", "EGUILLES 119"]:
        with st.expander(f"Analyse {b}"):
            c = df_cfg[df_cfg["Bien"] == b]
            if not c.empty:
                inv = c["Prix Achat"].values[0] + c["Travaux"].values[0]
                mensu = c["Credit Mensuel"].values[0]
                revenu = df[df["Bien"] == b]["Prix Total"].sum()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Investissement", f"{inv:,.0f} €")
                col2.metric("Cashflow (vs Crédit)", f"{revenu - (mensu*12):,.2f} €")
                col3.metric("Renta Projet", f"{(revenu/inv)*100 if inv>0 else 0:.2f} %")
            else:
                st.info("Allez dans 'Configuration' pour entrer les prix d'achat/travaux.")

# --- 5. CONFIGURATION ---
elif menu == "Configuration":
    st.subheader("⚙️ Paramètres financiers")
    with st.form("cfg"):
        b = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        p = st.number_input("Prix Achat", min_value=0)
        t = st.number_input("Travaux", min_value=0)
        m = st.number_input("Mensualité Crédit", min_value=0)
        if st.form_submit_button("Sauvegarder"):
            new_c = pd.DataFrame([[b, p, 0, t, m, 20]], columns=cols_config)
            df_cfg = pd.concat([df_cfg[df_cfg["Bien"] != b], new_c], ignore_index=True)
            df_cfg.to_csv(CONFIG_FILE, index=False)
            st.success("Config enregistrée.")
