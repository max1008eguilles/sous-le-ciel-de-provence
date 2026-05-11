import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIG ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")
CONFIG_FILE = "config_biens_v2.csv"

def load_data():
    cols = ["Bien", "Prix Achat", "Travaux", "Frais Notaire", "Apport", 
            "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
    if os.path.exists(CONFIG_FILE):
        return pd.read_csv(CONFIG_FILE)
    return pd.DataFrame(columns=cols)

df_cfg = load_data()

# --- FONCTION CALCUL CAPITAL RESTANT ---
def calculer_capital_restant(row):
    try:
        P = float(row["Prix Achat"]) + float(row["Frais Notaire"]) + float(row["Travaux"]) - float(row["Apport"])
        r = (float(row["Taux (%)"]) / 100) / 12
        n = int(row["Durée (mois)"])
        
        date_debut = pd.to_datetime(row["Date Début"])
        date_actuelle = datetime.now()
        
        # Nombre de mensualités déjà payées
        diff = relativedelta(date_actuelle, date_debut)
        m_payees = diff.years * 12 + diff.months
        
        if m_payees <= 0: return P
        if m_payees >= n: return 0
        
        # Formule du capital restant dû
        # CRD = P * [(1+r)^n - (1+r)^p] / [(1+r)^n - 1]
        crd = P * ((1 + r)**n - (1 + r)**m_payees) / ((1 + r)**n - 1)
        return max(0, crd)
    except:
        return 0

# --- TRAITEMENT DES DONNÉES ---
if not df_cfg.empty:
    df_cfg["Valeur Brute"] = df_cfg["Prix Achat"] + df_cfg["Travaux"] + df_cfg["Frais Notaire"]
    df_cfg["Capital Restant"] = df_cfg.apply(calculer_capital_restant, axis=1)
    df_cfg["Patrimoine Net"] = df_cfg["Valeur Brute"] - df_cfg["Capital Restant"]
    
    total_brut = df_cfg["Valeur Brute"].sum()
    total_crd = df_cfg["Capital Restant"].sum()
    total_net = df_cfg["Patrimoine Net"].sum()
else:
    total_brut = total_crd = total_net = 0

# --- INTERFACE (Selon ton dessin) ---
st.title("🏛️ RNM IMMO - Tableau de Bord Financier")
st.subheader(f"= {len(df_cfg)} Biens immo")

m1, m2, m3 = st.columns(3)
m1.metric("Patrimoine Brut (Achat+Travaux)", f"{total_brut:,.0f} €")
m2.metric("Dette Bancaire Totale", f"{total_crd:,.0f} €", delta=f"-{total_brut-total_crd:,.0f} remboursés", delta_color="normal")
m3.metric("Patrimoine Net (Réel)", f"{total_net:,.0f} €")

st.divider()

# --- SAISIE ET MODIFICATION ---
st.subheader("⚙️ Configuration Précise des Biens")
st.info("Saisis tes chiffres d'achat et de crédit. Le système calcule l'amortissement automatiquement à la date d'aujourd'hui.")

# Aide pour le format de date
st.caption("Format Date Début : AAAA-MM-JJ (ex: 2023-01-01)")

edited_df = st.data_editor(
    df_cfg[["Bien", "Prix Achat", "Travaux", "Frais Notaire", "Apport", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]],
    num_rows="dynamic",
    use_container_width=True
)

if st.button("💾 Sauvegarder et Recalculer"):
    # Nettoyage et sauvegarde
    edited_df.to_csv(CONFIG_FILE, index=False)
    st.success("Données enregistrées ! Les compteurs en haut ont été mis à jour.")
    st.rerun()

# --- DÉTAIL PAR BIEN ---
if not df_cfg.empty:
    st.divider()
    st.subheader("📊 Détail de la Valeur Nette par Bien")
    # Petit graphique pour voir quel bien pèse le plus dans ton patrimoine net
    import plotly.express as px
    fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net", "Capital Restant"], 
                 title="Répartition Valeur Nette vs Dette",
                 color_discrete_sequence=['#7030A0', '#E1E1E1'])
    st.plotly_chart(fig, use_container_width=True)
