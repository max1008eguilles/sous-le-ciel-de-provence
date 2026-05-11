import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIG ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")
CONFIG_FILE = "config_biens_v3.csv"

def load_data():
    cols = ["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", 
            "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
    if os.path.exists(CONFIG_FILE):
        df = pd.read_csv(CONFIG_FILE)
        if "Valeur Actuelle" not in df.columns:
            df["Valeur Actuelle"] = 0
        df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
        return df
    return pd.DataFrame(columns=cols)

df_cfg = load_data()

# --- FONCTION CALCUL CAPITAL RESTANT ---
def calculer_capital_restant(row):
    try:
        P = float(row["Montant Crédit"])
        if P <= 0: return 0
        r = (float(row["Taux (%)"]) / 100) / 12
        n = int(row["Durée (mois)"])
        date_debut = row["Date Début"]
        if not isinstance(date_debut, (date, datetime)):
            return P
        date_actuelle = date.today()
        diff = relativedelta(date_actuelle, date_debut)
        m_payees = diff.years * 12 + diff.months
        if m_payees <= 0: return P
        if m_payees >= n: return 0
        crd = P * ((1 + r)**n - (1 + r)**m_payees) / ((1 + r)**n - 1)
        return max(0, crd)
    except:
        return 0

# --- CALCULS GENERAUX ---
if not df_cfg.empty:
    for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
        df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
    
    total_brut = df_cfg["Valeur Actuelle"].sum()
    df_cfg["Capital Restant"] = df_cfg.apply(calculer_capital_restant, axis=1)
    df_cfg["Patrimoine Net"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
    
    total_crd = df_cfg["Capital Restant"].sum()
    total_net = df_cfg["Patrimoine Net"].sum()
else:
    total_brut = total_crd = total_net = 0

# --- INTERFACE ---
st.title("🏛️ RNM IMMO - Tableau de Bord Financier")
st.subheader(f"= {len(df_cfg)} Biens immo")

m1, m2, m3 = st.columns(3)
m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
m2.metric("Dette Bancaire", f"{total_crd:,.0f} €", delta=f"-{total_brut-total_crd:,.0f} remboursés", delta_color="normal")
m3.metric("Patrimoine Net", f"{total_net:,.0f} €")

st.divider()

st.subheader("⚙️ Configuration Précise des Biens")
edited_df = st.data_editor(
    df_cfg[["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]],
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Date Début": st.column_config.DateColumn("Date Début", format="DD/MM/YYYY"),
    }
)

if st.button("💾 Sauvegarder et Recalculer"):
    edited_df.to_csv(CONFIG_FILE, index=False)
    st.success("Données enregistrées !")
    st.rerun()

# --- GRAPHIQUE AVEC % ---
if not df_cfg.empty:
    st.divider()
    st.subheader("📊 Détail par Bien (Répartition %)")
    
    df_plot = df_cfg.copy()
    # On évite la division par zéro
    df_plot['val_ref'] = df_plot['Valeur Actuelle'].apply(lambda x: x if x > 0 else 1)
    
    df_plot['% Net'] = (df_plot['Patrimoine Net'] / df_plot['val_ref'] * 100).round(1).astype(str) + '%'
    df_plot['% Dette'] = (df_plot['Capital Restant'] / df_plot['val_ref'] * 100).round(1).astype(str) + '%'

    fig = px.bar(df_plot, x="Bien", y=["Patrimoine Net", "Capital Restant"], 
                 title="Composition du Patrimoine par Bien",
                 barmode="stack",
                 color_discrete_map={"Patrimoine Net": "#7030A0", "Capital Restant": "#E1E1E1"},
                 text_auto=False)
    
    # Ajout manuel des étiquettes de pourcentage
    fig.update_traces(name="Patrimoine Net", selector=dict(name="Patrimoine Net"), text=df_plot['% Net'], textposition='inside')
    fig.update_traces(name="Capital Restant", selector=dict(name="Capital Restant"), text=df_plot['% Dette'], textposition='inside')

    st.plotly_chart(fig, use_container_width=True)
