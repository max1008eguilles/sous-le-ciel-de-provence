import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
try:
    from streamlit_calendar import calendar
except:
    st.error("Modules en cours de chargement...")

# --- CONFIGURATION ---
st.set_page_config(page_title="RNM IMMO - Direct Edit", layout="wide")
DATA_FILE = "data_rnm_immo.csv"
COMPTA_FILE = "compta_rnm_immo.csv"
CONFIG_FILE = "config_biens.csv"

def load_data(file, columns):
    if os.path.exists(file):
        try: return pd.read_csv(file)
        except: pass
    return pd.DataFrame(columns=columns)

cols_resa = ["Bien", "Locataire", "Source", "Paiement", "Arrivée", "Départ", "Prix Total", "Tel"]
cols_compta = ["Date", "Type", "Source_Flux", "Montant", "Catégorie", "Commentaire"]
cols_config = ["Bien", "Prix Achat", "Apport", "Travaux", "Credit Mensuel"]

df_resa = load_data(DATA_FILE, cols_resa)
df_compta = load_data(COMPTA_FILE, cols_compta)
df_cfg = load_data(CONFIG_FILE, cols_config)

st.title("🏛️ RNM IMMO - Gestion Interactive")

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Planning & Résas", "Trésorerie & Compta", "Saisie Rapide", "Rentabilité & Config"])

# --- 1. PLANNING & RÉSERVATIONS (MODIFIABLE) ---
if menu == "Planning & Résas":
    st.subheader("📅 Planning")
    events = []
    for i, row in df_resa.iterrows():
        color = "#1E90FF" if "014" in str(row['Bien']) else "#FF4B4B"
        events.append({"title": f"{row['Bien']} - {row['Locataire']}", "start": str(row['Arrivée']), "end": str(row['Départ']), "color": color})
    calendar(events=events, options={"locale": "fr"})
    
    st.divider()
    st.subheader("📝 Liste des Réservations (Modifiable)")
    st.info("💡 Double-clique sur une case pour modifier. Coche 'Supprimer' à gauche pour effacer.")
    
    # Ajout d'une colonne de suppression temporaire
    df_edit_resa = df_resa.copy()
    df_edit_resa.insert(0, "Supprimer", False)
    
    edited_resa = st.data_editor(df_edit_resa, use_container_width=True, num_rows="dynamic", key="editor_resa")
    
    if st.button("Enregistrer les modifications (Résas)"):
        # On garde uniquement les lignes non cochées pour suppression
        final_df = edited_resa[edited_resa["Supprimer"] == False].drop(columns=["Supprimer"])
        final_df.to_csv(DATA_FILE, index=False)
        st.success("Modifications enregistrées !")
        st.rerun()

# --- 2. TRÉSORERIE & COMPTA (MODIFIABLE) ---
elif menu == "Trésorerie & Compta":
    st.subheader("💳 État des Flux")
    
    # Calcul des soldes en direct
    df_compta["Montant"] = pd.to_numeric(df_compta["Montant"], errors='coerce').fillna(0)
    banque = df_compta[(df_compta["Source_Flux"] == "Compte Société") & (df_compta["Type"] == "Revenu")]["Montant"].sum() - \
             df_compta[(df_compta["Source_Flux"] == "Compte Société") & (df_compta["Type"] == "Dépense")]["Montant"].sum()
    cash = df_compta[(df_compta["Source_Flux"] == "Cash") & (df_compta["Type"] == "Revenu")]["Montant"].sum() - \
           df_compta[(df_compta["Source_Flux"] == "Cash") & (df_compta["Type"] == "Dépense")]["Montant"].sum()

    c1, c2 = st.columns(2)
    c1.metric("Compte Société", f"{banque:,.2f} €")
    c2.metric("Cash", f"{cash:,.2f} €")

    st.divider()
    st.subheader("📝 Journal de Caisse (Modifiable)")
    
    df_edit_compta = df_compta.copy()
    df_edit_compta.insert(0, "Supprimer", False)
    
    edited_compta = st.data_editor(df_edit_compta, use_container_width=True, num_rows="dynamic", key="editor_compta")
    
    if st.button("Mettre à jour la Comptabilité"):
        final_df_c = edited_compta[edited_compta["Supprimer"] == False].drop(columns=["Supprimer"])
        final_df_c.to_csv(COMPTA_FILE, index=False)
        st.success("Comptabilité mise à jour !")
        st.rerun()

# --- 3. SAISIE RAPIDE ---
elif menu == "Saisie Rapide":
    with st.form("saisie_f"):
        st.subheader("Entrer une nouvelle donnée")
        cat_type = st.radio("Nature", ["Réservation", "Dépense/Autre Revenu"], horizontal=True)
        
        if cat_type == "Réservation":
            b = st.selectbox("Bien", ["EGUILLES 014", "EGUILLES 119"])
            l = st.text_input("Locataire")
            p = st.number_input("Prix Total (€)")
            m = st.selectbox("Paiement", ["Virement", "Cash"])
            arr = st.date_input("Arrivée")
            dep = st.date_input("Départ")
            if st.form_submit_button("Enregistrer Résa"):
                # Sauvegarde Résa
                new_r = pd.DataFrame([[b, l, "Direct", m, str(arr), str(dep), p, ""]], columns=cols_resa)
                pd.concat([df_resa, new_r], ignore_index=True).to_csv(DATA_FILE, index=False)
                # Sauvegarde Compta auto
                dest = "Compte Société" if m == "Virement" else "Cash"
                new_c = pd.DataFrame([[str(arr), "Revenu", dest, p, "Loyer", f"Résa {l}"]], columns=cols_compta)
                pd.concat([df_compta, new_c], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            t = col1.selectbox("Type", ["Dépense", "Revenu"])
            s = col2.selectbox("Flux", ["Compte Société", "Cash"])
            m = st.number_input("Montant")
            com = st.text_input("Commentaire")
            if st.form_submit_button("Enregistrer Flux"):
                new_c = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), t, s, m, "Divers", com]], columns=cols_compta)
                pd.concat([df_compta, new_c], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                st.rerun()

# --- 4. RENTABILITÉ & CONFIG ---
elif menu == "Rentabilité & Config":
    # (Garder le code de config et de renta projet ici)
    st.write("Gestion de la configuration des biens")
    
