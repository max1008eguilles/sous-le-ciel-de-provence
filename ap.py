import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Maxence Immo", layout="wide")

# Fichier de stockage (persistant sur Streamlit Cloud tant que l'app ne redémarre pas)
DATA_FILE = "data_immo.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Date", "Bien", "Type", "Montant", "Description"])

df = load_data()

# --- INTERFACE ---
st.title("🏠 Maxence Immo - Gestion Professionnelle")

# Barre latérale pour l'ajout
st.sidebar.header("📥 Nouvelle Transaction")
with st.sidebar.form("form_trans"):
    date = st.date_input("Date", datetime.now())
    bien = st.text_input("Nom du bien (ex: Studio Aix)")
    type_trans = st.selectbox("Catégorie", ["Loyer", "Charge Copro", "Travaux", "Taxe Foncière", "Assurance"])
    montant = st.number_input("Montant (€)", min_value=0.0, step=10.0)
    desc = st.text_area("Notes")
    submit = st.form_submit_button("Enregistrer la donnée")

if submit:
    new_data = pd.DataFrame([[str(date), bien, type_trans, montant, desc]], 
                            columns=df.columns)
    df = pd.concat([df, new_data], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success("Donnée ajoutée !")
    st.rerun()

# --- DASHBOARD (Les 99% manquants) ---
if not df.empty:
    # 1. Filtres rapides
    biens_dispo = ["Tous"] + sorted(df["Bien"].unique().tolist())
    filtre_bien = st.selectbox("Filtrer par Bien Immobilier", biens_dispo)
    
    data_vue = df if filtre_bien == "Tous" else df[df["Bien"] == filtre_bien]

    # 2. Indicateurs clés (KPIs)
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    total_loyers = data_vue[data_vue["Type"] == "Loyer"]["Montant"].sum()
    total_charges = data_vue[data_vue["Type"] != "Loyer"]["Montant"].sum()
    rendement = total_loyers - total_charges

    c1.metric("Revenus Totaux", f"{total_loyers:,.2f} €")
    c2.metric("Charges Totales", f"{total_charges:,.2f} €", delta_color="inverse")
    c3.metric("Bénéfice Net", f"{rendement:,.2f} €")
    c4.metric("Nb Transactions", len(data_vue))

    # 3. Graphiques d'analyse
    st.divider()
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 Répartition des dépenses")
        fig_pie = px.pie(data_vue, values='Montant', names='Type', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_right:
        st.subheader("📈 Évolution mensuelle")
        # Petit traitement pour grouper par mois
        data_vue['Date'] = pd.to_datetime(data_vue['Date'])
        df_mensuel = data_vue.groupby(data_vue['Date'].dt.strftime('%Y-%m')).sum(numeric_only=True).reset_index()
        fig_line = px.bar(df_mensuel, x='Date', y='Montant', title="Flux de trésorerie")
        st.plotly_chart(fig_line, use_container_width=True)

    # 4. Tableau de données
    st.divider()
    st.subheader("📄 Historique complet")
    st.dataframe(data_vue.sort_values("Date", ascending=False), use_container_width=True)

else:
    st.info("👋 Bienvenue Maxence ! Commence par ajouter un loyer ou une charge dans le menu à gauche.")
