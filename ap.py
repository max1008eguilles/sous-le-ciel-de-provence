import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Gestion Patrimoine - Expert", layout="wide")

# --- 2. DÉFINITION DES FICHIERS ---
MENAGE_014_FILE = "menages_manuels_014.csv"
MENAGE_119_FILE = "menages_manuels_119.csv"
COMPTA_FILE = "compta.csv"
RESA_FILE = "reservations.csv" # Assure-toi que ce fichier existe

# --- 3. FONCTIONS DE CHARGEMENT ---
def load_data(file):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()

# --- 4. SYSTÈME DE SÉCURITÉ ---
def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        if user in st.secrets["passwords"] and pwd == st.secrets["passwords"][user]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Accès Privé Patrimoine")
        st.text_input("Identifiant", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.error("Identifiant ou mot de passe incorrect")
        st.text_input("Identifiant", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    return True

# --- Lancement de l'application après vérification ---
if check_password():
    
    # Chargement des réservations global
    df_resa = load_data(RESA_FILE)
    if not df_resa.empty:
        df_resa['Date Arrivée'] = pd.to_datetime(df_resa['Date Arrivée'], errors='coerce')

    # --- 5. BARRE LATÉRALE : LE SÉLECTEUR D'UNIVERS ---
    with st.sidebar:
        st.title("📂 NAVIGATION")
        univers = st.selectbox("CHOISIR UN UNIVERS", ["🏠 RNM IMMO", "🏛️ SCI PHOCEA", "👤 PERSO (Maxence)"])
        st.divider()

    # =========================================================
    # UNIVERS 1 : RNM IMMO (Tout ton travail actuel)
    # =========================================================
    if univers == "🏠 RNM IMMO":
        with st.sidebar:
            st.subheader("Menu RNM IMMO")
            page = st.radio("Aller vers :", [
                "Tableau de Bord", 
                "RO 2026", 
                "Détail 014", 
                "Détail 119", 
                "Ménages", 
                "Compta"
            ])

        if page == "Tableau de Bord":
            st.title("🏠 RNM IMMO - Vue Patrimoine")
            # --- Métriques de ton tableau de bord actuel ---
            col1, col2, col3 = st.columns(3)
            col1.metric("Cash disponible", "15 288 €") 
            col2.metric("Valeur Estimée", "315 000 €")
            col3.metric("Rendement Brut", "8.4 %")
            st.info("Ici s'affiche ton tableau de bord avec les jauges.")

        elif page == "RO 2026":
            st.title("🚀 RNM IMMO - Cockpit de Pilotage 2026")
            # --- Code Cockpit Consolidé ---
            mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
            CREDIT_119 = 689.72
            
            stats_list = []
            for i, m in enumerate(mois_noms):
                # Calcul simplifié pour l'exemple
                stats_list.append({
                    "Mois": m, "CA RNM": 0, "Charges": 0, "Crédits": CREDIT_119, "NET": -CREDIT_119
                })
            df_cockpit = pd.DataFrame(stats_list).set_index("Mois")
            st.dataframe(df_cockpit, use_container_width=True)

        elif page == "Détail 014":
            st.title("📊 Détail Studio 014")
            st.write("Données spécifiques au 014...")

        elif page == "Détail 119":
            st.title("📊 Détail Studio 119")
            st.write("Données spécifiques au 119...")

        elif page == "Ménages":
            st.title("🧹 Gestion des Ménages")
            # Ton code pour WhatsApp et codes boîtes à clés
            st.write("Calendrier et suivi des ménages...")

        elif page == "Compta":
            st.title("🧾 Journal de Comptabilité")
            # Ton formulaire de saisie compta
            st.write("Saisie des recettes et dépenses...")

    # =========================================================
    # UNIVERS 2 : SCI PHOCEA (Vierge pour nouveau départ)
    # =========================================================
    elif univers == "🏛️ SCI PHOCEA":
        with st.sidebar:
            st.subheader("Menu SCI PHOCEA")
            page_sci = st.radio("Navigation :", ["Vue d'ensemble", "Suivi Travaux", "Documents"])
        
        if page_sci == "Vue d'ensemble":
            st.title("🏛️ SCI PHOCEA - Pilotage")
            st.info("Cet univers est vierge. Tu peux commencer à coder ici tes nouvelles données.")
            # Exemple de futur contenu
            st.metric("Budget Travaux", "45 000 €", "- 2 500 €")

    # =========================================================
    # UNIVERS 3 : PERSO (MAXENCE)
    # =========================================================
    elif univers == "👤 PERSO (Maxence)":
        st.title("👤 Espace Personnel")
        st.write("Suivi du patrimoine personnel et investissements hors immo.")
        st.info("Espace sécurisé et privé.")

# --- FIN DU CODE ---
