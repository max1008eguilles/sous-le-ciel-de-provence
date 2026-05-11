import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Config
st.set_page_config(page_title="Maxence Immo", layout="wide")
DATA_FILE = "data_immo.csv"

def load_data():
    if os.path.exists(DATA_FILE): return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Date", "Bien", "Type", "Montant"])

df = load_data()

st.title("🏠 Maxence Immo - Gestion")

# Formulaire
with st.sidebar.form("Ajout"):
    date = st.date_input("Date")
    bien = st.text_input("Nom du bien")
    type_t = st.selectbox("Type", ["Loyer", "Charge"])
    montant = st.number_input("Montant (€)", min_value=0.0)
    if st.form_submit_button("Enregistrer"):
        new_row = pd.DataFrame([[str(date), bien, type_t, montant]], columns=df.columns)
        pd.concat([df, new_row]).to_csv(DATA_FILE, index=False)
        st.success("Enregistré !")
        st.rerun()

# Affichage
if not df.empty:
    st.metric("Total Loyers", f"{df[df['Type']=='Loyer']['Montant'].sum():.2f} €")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Utilise le menu à gauche pour ajouter ton premier loyer.")
