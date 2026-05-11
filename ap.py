import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Maxence Immo", layout="wide")
DATA_FILE = "data_immo.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return pd.read_csv(DATA_FILE)
        except: pass
    return pd.DataFrame(columns=["Date", "Bien", "Type", "Montant", "Description"])

df = load_data()

st.title("🏠 Maxence Immo - Gestion Professionnelle")

# --- BARRE LATÉRALE ---
st.sidebar.header("📥 Nouvelle Transaction")
with st.sidebar.form("form_trans"):
    date = st.date_input("Date", datetime.now())
    bien = st.text_input("Nom du bien (ex: Studio Aix)")
    type_trans = st.selectbox("Catégorie", ["Loyer", "Charge Copro", "Travaux", "Taxe Foncière"])
    montant = st.number_input("Montant (€)", min_value=0.0)
    desc = st.text_area("Notes")
    submit = st.form_submit_button("Enregistrer la donnée")

if submit:
    # On s'assure que le nom du bien n'est pas vide
    nom_bien = bien if bien else "Non spécifié"
    new_data = pd.DataFrame([[str(date), nom_bien, type_trans, montant, desc]], columns=df.columns)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success("Donnée ajoutée !")
    st.rerun()

# --- DASHBOARD ---
# Sécurité : On vérifie si on a des données et si la colonne 'Bien' existe
if not df.empty and "Bien" in df.columns:
    # TRI BLINDÉ : On transforme tout en texte pour éviter le TypeError
    liste_biens = ["Tous"] + sorted(list(set([str(b) for b in df["Bien"].dropna()])))
    filtre_bien = st.selectbox("Filtrer par Bien", liste_biens)
    
    data_vue = df if filtre_bien == "Tous" else df[df["Bien"] == filtre_bien]

    # KPIs
    st.divider()
    c1, c2, c3 = st.columns(3)
    loyers = pd.to_numeric(data_vue[data_vue["Type"] == "Loyer"]["Montant"]).sum()
    charges = pd.to_numeric(data_vue[data_vue["Type"] != "Loyer"]["Montant"]).sum()
    
    c1.metric("Revenus", f"{loyers:.2f} €")
    c2.metric("Charges", f"{charges:.2f} €", delta_color="inverse")
    c3.metric("Bénéfice Net", f"{loyers - charges:.2f} €")

    # Graphiques
    st.divider()
    col_left, col_right = st.columns(2)
    with col_left:
        if not data_vue.empty:
            fig_pie = px.pie(data_vue, values='Montant', names='Type', title="Répartition Financière")
            st.plotly_chart(fig_pie, use_container_width=True)
    with col_right:
        st.subheader("Historique")
        st.dataframe(data_vue, use_container_width=True)
else:
    st.warning("👋 Bienvenue ! Ton fichier est vide. Ajoute ta première transaction à gauche pour activer le dashboard.")
