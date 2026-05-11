import streamlit as st
import pandas as pd
import os

# --- CONFIG ---
st.set_page_config(page_title="RNM IMMO - Dashboard", layout="wide")

# Fichiers de stockage
CONFIG_FILE = "config_biens.csv"
COMPTA_FILE = "compta_rnm_immo.csv"

# Fonction de chargement sécurisée
def load_data(file, columns):
    if os.path.exists(file):
        df = pd.read_csv(file)
        # Vérifie que toutes les colonnes attendues sont là
        for col in columns:
            if col not in df.columns:
                df[col] = 0
        return df
    return pd.DataFrame(columns=columns)

# Définition des structures
cols_cfg = ["Bien", "Valeur Actuelle", "Credit Restant", "Mensualité"]
cols_compta = ["Date", "Type", "Source_Flux", "Montant", "Commentaire"]

df_cfg = load_data(CONFIG_FILE, cols_cfg)
df_compta = load_data(COMPTA_FILE, cols_compta)

# --- CALCULS (Ton dessin) ---
nb_biens = len(df_cfg)
patrimoine_brut = pd.to_numeric(df_cfg["Valeur Actuelle"]).sum()
credits_encours = pd.to_numeric(df_cfg["Credit Restant"]).sum()

# Calcul du Cash propre
if not df_compta.empty:
    df_compta["Montant"] = pd.to_numeric(df_compta["Montant"], errors='coerce').fillna(0)
    cash_total = df_compta[df_compta["Type"] == "Revenu"]["Montant"].sum() - \
                 df_compta[df_compta["Type"] == "Dépense"]["Montant"].sum()
else:
    cash_total = 0

patrimoine_net = (patrimoine_brut + cash_total) - credits_encours

# --- INTERFACE ---
st.title("🏛️ RNM IMMO")
st.subheader(f"= {nb_biens} Biens immo")

# La ligne de metrics (Design de ton dessin)
# On utilise du CSS pour rapprocher les metrics du style violet de ton croquis
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 30px; color: #7030A0; }
    </style>
    """, unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Patrimoine brut estimé", f"{patrimoine_brut:,.0f} €")
m2.metric("Crédit en cours", f"{credits_encours:,.0f} €")
m3.metric("Cash disponible", f"{cash_total:,.2f} €")
m4.metric("Patrimoine Net", f"{patrimoine_net:,.0f} €")

st.divider()

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Tableau de bord", "Éditer mon Patrimoine", "Journal Trésorerie"])

if menu == "Éditer mon Patrimoine":
    st.subheader("🏠 Gestion des Biens")
    st.info("Ajoute tes biens ici (ex: Eguilles 014) avec leur valeur de revente estimée et le capital restant dû.")
    
    # Éditeur pour ajouter/modifier les biens
    edited_cfg = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Sauvegarder mon Patrimoine"):
        edited_cfg.to_csv(CONFIG_FILE, index=False)
        st.success("Patrimoine mis à jour !")
        st.rerun()

elif menu == "Journal Trésorerie":
    st.subheader("💰 Entrées / Sorties de Cash")
    
    with st.expander("➕ Ajouter une opération"):
        with st.form("add_cash"):
            t = st.selectbox("Type", ["Revenu", "Dépense"])
            m = st.number_input("Montant (€)")
            c = st.text_input("Commentaire")
            if st.form_submit_button("Enregistrer"):
                new_op = pd.DataFrame([[pd.Timestamp.now().strftime("%d/%m/%Y"), t, "Banque", m, c]], columns=cols_compta)
                pd.concat([df_compta, new_op], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                st.rerun()
    
    # Tableau éditable pour supprimer/modifier les erreurs
    st.write("### Historique complet")
    edited_compta = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Sauvegarder les modifications Compta"):
        edited_compta.to_csv(COMPTA_FILE, index=False)
        st.rerun()
