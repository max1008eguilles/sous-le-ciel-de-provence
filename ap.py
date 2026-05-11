import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURATION ET DATAFRAMES ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")
DATA_FILE = "data_rnm_immo.csv"
CONFIG_FILE = "config_biens.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: pass
    return pd.DataFrame(columns=columns)

# Structure pour les réservations et les charges
cols_data = ["Date", "Bien", "Locataire", "Source", "Paiement", "Arrivée", "Départ", "Prix Total", "Charges", "Mail", "Tel"]
# Structure pour la rentabilité projet
cols_config = ["Bien", "Prix Achat", "Apport", "Travaux", "Credit Mensuel", "Duree Credit"]

df = load_data(DATA_FILE, cols_data)
df_cfg = load_data(CONFIG_FILE, cols_config)

st.title("🏛️ RNM IMMO - Gestion Haute Performance")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Tableau de Bord", "Saisie Réservation", "Comptabilité & Rentabilité", "Configuration Biens"])

# --- 1. CONFIGURATION DES BIENS ---
if menu == "Configuration Biens":
    st.subheader("⚙️ Paramètres financiers des biens")
    with st.form("cfg_form"):
        nom = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        col1, col2 = st.columns(2)
        achat = col1.number_input("Prix d'achat (€)", min_value=0)
        apport = col2.number_input("Apport personnel (€)", min_value=0)
        travaux = col1.number_input("Montant Travaux (€)", min_value=0)
        mensu = col2.number_input("Mensualité Crédit (€)", min_value=0)
        if st.form_submit_button("Enregistrer la config"):
            new_cfg = pd.DataFrame([[nom, achat, apport, travaux, mensu, 240]], columns=cols_config)
            df_cfg = pd.concat([df_cfg[df_cfg["Bien"] != nom], new_cfg], ignore_index=True)
            df_cfg.to_csv(CONFIG_FILE, index=False)
            st.success(f"Configuration {nom} mise à jour !")

# --- 2. SAISIE RÉSERVATION ---
elif menu == "Saisie Réservation":
    st.subheader("📩 Nouvelle Réservation / Transaction")
    with st.form("form_resa"):
        c1, c2, c3 = st.columns(3)
        bien = c1.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
        locataire = c2.text_input("Nom Prénom Locataire")
        source = c3.selectbox("Source", ["Airbnb", "Booking", "Direct"])
        
        c4, c5, c6 = st.columns(3)
        start = c4.date_input("Date Arrivée")
        end = c5.date_input("Date Sortie")
        paiement = c6.selectbox("Mode de paiement", ["Virement", "Cash", "Carte"])
        
        c7, c8, c9 = st.columns(3)
        prix = c7.number_input("Prix Total Séjour (€)", min_value=0.0)
        mail = c8.text_input("Email")
        tel = c9.text_input("Téléphone")
        
        if st.form_submit_button("Valider la réservation"):
            new_row = pd.DataFrame([[datetime.now().date(), bien, locataire, source, paiement, str(start), str(end), prix, 0, mail, tel]], columns=cols_data)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Réservation enregistrée !")

# --- 3. TABLEAU DE BORD ---
elif menu == "Tableau de Bord":
    if not df.empty:
        # Filtre Bien
        sel_bien = st.selectbox("Filtrer par bien", ["Tous"] + list(df["Bien"].unique()))
        df_v = df if sel_bien == "Tous" else df[df["Bien"] == sel_bien]
        
        # Stats Clés
        df_v["Arrivée"] = pd.to_datetime(df_v["Arrivée"])
        df_v["Départ"] = pd.to_datetime(df_v["Départ"])
        df_v["Nuits"] = (df_v["Départ"] - df_v["Arrivée"]).dt.days
        
        st.divider()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CA Total", f"{df_v['Prix Total'].sum():,.2f} €")
        k2.metric("Nuits totales", int(df_v['Nuits'].sum()))
        k3.metric("Durée Moyenne", f"{df_v['Nuits'].mean():.1f} j")
        
        # Graphiques
        st.divider()
        g1, g2 = st.columns(2)
        with g1:
            fig_p = px.pie(df_v, values='Prix Total', names='Source', title="Origine des Revenus")
            st.plotly_chart(fig_p, use_container_width=True)
        with g2:
            fig_m = px.pie(df_v, values='Prix Total', names='Paiement', title="Modes de Paiement")
            st.plotly_chart(fig_m, use_container_width=True)
            
        st.subheader("📋 Liste des locataires")
        st.dataframe(df_v[["Arrivée", "Locataire", "Tel", "Mail", "Source", "Prix Total"]])
    else:
        st.info("Aucune donnée disponible. Commencez par configurer vos biens ou saisir une réservation.")

# --- 4. RENTABILITÉ PROJET ---
elif menu == "Comptabilité & Rentabilité":
    st.subheader("📊 Analyse de Rentabilité")
    for bien in ["EGUILLES 014", "EGUILLES 119"]:
        with st.expander(f"Détails {bien}"):
            cfg = df_cfg[df_cfg["Bien"] == bien]
            if not cfg.empty:
                rev = df[df["Bien"] == bien]["Prix Total"].sum()
                invest = cfg["Prix Achat"].values[0] + cfg["Travaux"].values[0]
                mensu = cfg["Credit Mensuel"].values[0]
                
                # Calcul Renta brute et nette
                renta_brute = (rev / invest) * 100 if invest > 0 else 0
                cashflow = rev - (mensu * 12) # Simplifié
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Investissement Total", f"{invest:,.0f} €")
                c2.metric("Renta Brute Annuelle", f"{renta_brute:.2f} %")
                c3.metric("Cashflow estimé (Annuel)", f"{cashflow:,.2f} €")
            else:
                st.warning(f"Configurez les données financières de {bien} dans l'onglet Configuration.")
