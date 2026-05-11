 import streamlit as st
import pandas as pd
import os

# --- CONFIG ---
st.set_page_config(page_title="RNM IMMO - Dashboard", layout="wide")

# Fichiers de stockage
CONFIG_FILE = "config_biens.csv"
COMPTA_FILE = "compta_rnm_immo.csv"

def load_data(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

# Chargement
df_cfg = load_data(CONFIG_FILE, ["Bien", "Valeur Actuelle", "Credit Restant", "Mensualité"])
df_compta = load_data(COMPTA_FILE, ["Date", "Type", "Source_Flux", "Montant", "Commentaire"])

# --- CALCULS PATRIMOINE (Ton dessin) ---
nb_biens = len(df_cfg)
patrimoine_brut = df_cfg["Valeur Actuelle"].sum()
credits_encours = df_cfg["Credit Restant"].sum()

# Calcul du Cash (Entrées - Sorties)
if not df_compta.empty:
    df_compta["Montant"] = pd.to_numeric(df_compta["Montant"], errors='coerce').fillna(0)
    cash_total = df_compta[df_compta["Type"] == "Revenu"]["Montant"].sum() - \
                 df_compta[df_compta["Type"] == "Dépense"]["Montant"].sum()
else:
    cash_total = 0

patrimoine_net = (patrimoine_brut + cash_total) - credits_encours

# --- AFFICHAGE (Style ton schéma) ---
st.title(f"🏛️ RNM IMMO")
st.subheader(f"Total : {nb_biens} Biens Immobiliers")

# Barre de metrics (La ligne violette de ton dessin)
style_cols = st.columns(4)
style_cols[0].metric("Patrimoine Brut Estimé", f"{patrimoine_brut:,.0f} €")
style_cols[1].metric("Crédit en cours", f"{credits_encours:,.0f} €")
style_cols[2].metric("Cash disponible", f"{cash_total:,.2f} €")
style_cols[3].metric("Patrimoine Net", f"{patrimoine_net:,.0f} €", delta=f"{cash_total:,.0f} € cash")

st.divider()

# --- INTERFACE DE SAISIE POUR ALIMENTER LE TABLEAU ---
menu = st.sidebar.radio("Navigation", ["Tableau de bord", "Éditer Valeur Biens", "Saisie Trésorerie"])

if menu == "Éditer Valeur Biens":
    st.subheader("⚙️ Configuration des valeurs de ton patrimoine")
    st.info("Remplis ces données pour que le Tableau de Bord se calcule.")
    
    # Éditeur interactif
    new_cfg = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
    if st.button("Sauvegarder les valeurs"):
        new_cfg.to_csv(CONFIG_FILE, index=False)
        st.success("Valeurs mises à jour !")
        st.rerun()

elif menu == "Saisie Trésorerie":
    st.subheader("💰 Mouvements de Cash")
    with st.form("flux"):
        t = st.selectbox("Type", ["Revenu", "Dépense"])
        m = st.number_input("Montant (€)", min_value=0.0)
        c = st.text_input("Commentaire (ex: Loyer Eguilles 014)")
        if st.form_submit_button("Ajouter"):
            new_op = pd.DataFrame([[pd.Timestamp.now(), t, "Banque", m, c]], 
                                  columns=["Date", "Type", "Source_Flux", "Montant", "Commentaire"])
            pd.concat([df_compta, new_op], ignore_index=True).to_csv(COMPTA_FILE, index=False)
            st.rerun()
    
    st.dataframe(df_compta.sort_values("Date", ascending=False))
