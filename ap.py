import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Groupe Maxence Immo", layout="wide")
DATA_FILE = "data_immo.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except: pass
    return pd.DataFrame(columns=["Date", "Société", "Bien", "Type", "Montant", "Description"])

df = load_data()

st.title("🏙️ Gestion Immobilière Multi-Sociétés")

# --- BARRE LATÉRALE : SAISIE ---
st.sidebar.header("📥 Nouvelle Transaction")
with st.sidebar.form("form_trans"):
    soc = st.selectbox("Société", ["RNM IMMO", "SCI PHOCEA"])
    date = st.date_input("Date", datetime.now())
    bien = st.text_input("Nom du bien (ex: Studio Aix)")
    type_trans = st.selectbox("Catégorie", ["Loyer", "Charge Copro", "Travaux", "Taxe Foncière", "Assurance", "Crédit"])
    montant = st.number_input("Montant (€)", min_value=0.0)
    desc = st.text_area("Notes")
    submit = st.form_submit_button("Enregistrer la donnée")

if submit:
    nom_bien = bien if bien else "Non spécifié"
    new_data = pd.DataFrame([[str(date), soc, nom_bien, type_trans, montant, desc]], columns=df.columns)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success(f"Enregistré pour {soc} !")
    st.rerun()

# --- DASHBOARD GLOBAL ET FILTRES ---
if not df.empty:
    # FILTRE DE VUE (Global vs Société)
    st.write("---")
    vue = st.radio("🔍 Choisir la vision :", ["Vision Globale (IMMO)", "RNM IMMO", "SCI PHOCEA"], horizontal=True)
    
    # Logique de filtrage
    if vue == "Vision Globale (IMMO)":
        data_vue = df
    else:
        data_vue = df[df["Société"] == vue]

    # Sous-filtre par bien
    biens_existants = ["Tous les biens"] + sorted(list(set([str(b) for b in data_vue["Bien"].dropna()])))
    filtre_bien = st.selectbox("Filtrer par Bien Immobilier", biens_existants)
    if filtre_bien != "Tous les biens":
        data_vue = data_vue[data_vue["Bien"] == filtre_bien]

    # KPIs
    c1, c2, c3 = st.columns(3)
    loyers = pd.to_numeric(data_vue[data_vue["Type"] == "Loyer"]["Montant"]).sum()
    charges
