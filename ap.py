import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIG DE LA PAGE ---
st.set_page_config(page_title="RNM IMMO - Expert", layout="wide")

# --- SÉCURITÉ ---
def check_password():
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        if user in st.secrets["passwords"] and pwd == st.secrets["passwords"][user]:
            st.session_state["password_correct"] = True
            st.session_state["user_authenticated"] = user
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🏛️ Accès RNM IMMO")
        st.text_input("Identifiant", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    return True

if check_password():
    
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"

    def load_config():
        if os.path.exists(CONFIG_FILE):
            df = pd.read_csv(CONFIG_FILE)
            df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
            return df
        return pd.DataFrame(columns=["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"])

    def load_compta():
        if os.path.exists(COMPTA_FILE):
            df = pd.read_csv(COMPTA_FILE)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df
        return pd.DataFrame(columns=["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"])

    df_compta = load_compta()
    df_cfg = load_config()

    def get_solde(compte_nom):
        if df_compta.empty: return 0.0
        df_c = df_compta[df_compta["Compte"] == compte_nom]
        rev = pd.to_numeric(df_c[df_c["Type"] == "Revenu"]["Montant"]).sum()
        dep = pd.to_numeric(df_c[df_c["Type"] == "Dépense"]["Montant"]).sum()
        cre = pd.to_numeric(df_c[df_c["Type"] == "Crédit"]["Montant"]).sum()
        return float(rev - dep - cre)

    solde_cic = get_solde("CIC")
    solde_cash_physique = get_solde("Cash")
    total_treso_dynamique = solde_cic + solde_cash_physique

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("📂 Navigation")
        st.write(f"👤 Connecté : **{st.session_state.get('user_authenticated')}**")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE RNM IMMO ---
    if page == "RNM IMMO":
        if not df_cfg.empty:
            for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
                df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
            
            total_brut = df_cfg["Valeur Actuelle"].sum()
            
            # Calcul de la répartition % pour le tableau
            if total_brut > 0:
                df_cfg["%"] = (df_cfg["Valeur Actuelle"] / total_brut) * 100
            else:
                df_cfg["%"] = 0

            def calc_crd(row):
                try:
                    P, r, n = float(row["Montant Crédit"]), (float(row["Taux (%)"])/100)/12, int(row["Durée (mois)"])
                    diff = relativedelta(date.today(), row["Date Début"])
                    m = diff.years * 12 + diff.months
                    if m <= 0: return P
                    if m >= n: return 0
                    return P * ((1 + r)**n - (1 + r)**m) / ((1 + r)**n - 1)
                except: return 0

            df_cfg["Capital Restant"] = df_cfg.apply(calc_crd, axis=1)
            total_crd = df_cfg["Capital Restant"].sum()
            total_net = (total_brut + total_treso_dynamique) - total_crd
            df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
            
            # Calcul des rentabilités pour le graphique
            df_cfg["Rentabilité Brut (%)"] = ( (df_cfg["Mensualité"] * 12) / (df_cfg["Prix Achat"] + df_cfg["Travaux"] + df_cfg["Frais Notaire"]) ) * 100
            df_cfg["Rentabilité Net (%)"] = ( ((df_cfg["Mensualité"] * 12) - (df_cfg["Mensualité"] * 12 * 0.3)) / (df_cfg["Prix Achat"] + df_cfg["Travaux"] + df_cfg["Frais Notaire"]) ) * 100
        else:
            total_brut = total_crd = total_net = 0

        st.title("🏛️ RNM IMMO - Tableau de Bord")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net:,.0f} €")
        
        st.divider()
        st.subheader("⚙️ Configuration des Biens")
        cols_order = ["Bien", "%", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"]
        existing_cols = [c for c in cols_order if c in df_cfg.columns]
        
        edited_df = st.data_editor(df_cfg[existing_cols], num_rows="dynamic", use_container_width=True,
                                  column_config={"%": st.column_config.NumberFormatColumn(format="%.1f %%")})
        
        if st.button("💾 Sauvegarder Biens"):
            save_df = edited_df.drop(columns=["%"]) if "%" in edited_df.columns else edited_df
            save_df.to_csv(CONFIG_FILE, index=False)
            st.rerun()

        if not df_cfg.empty:
            st.divider()
            st.subheader("📊 Détail par Bien")
            # Ajout des informations de % dans le graphique
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], 
                         barmode="stack", 
                         color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"},
                         hover_data={
                             "Rentabilité Brut (%)": ":.2f",
                             "Rentabilité Net (%)": ":.2f"
                         })
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA ---
    elif page == "COMPTA":
        st.title("💰 Comptabilité - RNM IMMO")
        c1, c2, c3 = st.columns(3)
        c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
        c2.metric("Montant Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL TRESORERIE", f"{total_treso_dynamique:,.2f} €")
        
        if not df_compta.empty:
            st.divider()
            st.subheader("📊 Analyse Financière")
            df_calc = df_compta.copy()
            df_calc['Date'] = pd.to_datetime(df_calc['Date'])
            df_calc['Année'] = df_calc['Date'].dt.strftime('%Y')
            df_calc['Mois'] = df_calc['Date'].dt.strftime('%m/%Y')
            
            recap_y = df_calc.groupby(['Année', 'Type'])['Montant'].sum().unstack(fill_value=0)
            recap_m = df_calc.groupby(['Mois', 'Type', 'Année'])['Montant'].sum().unstack(level=1, fill_value=0)
            
            for col in ["Revenu", "Dépense", "Crédit"]:
                if col not in recap_y.columns: recap_y[col] = 0.0
                if col not in recap_m.columns: recap_m[col] = 0.0

            final_rows = []
            for a in sorted(df_calc['Année'].unique(), reverse=True):
                val_y = recap_y.loc[a]
                final_rows.append({"Période": f"TOTAL {a}", "Revenus": val_y["Revenu"], "Charges": val_y["Dépense"], "Crédit": val_y["Crédit"], "Cash Flow": val_y["Revenu"]-val_y["Dépense"]-val_y["Crédit"]})
                mes_mois = recap_m.xs(a, level='Année').sort_index(ascending=False)
                for m, val_m in mes_mois.iterrows():
                    final_rows.append({"Période": m, "Revenus": val_m["Revenu"], "Charges": val_m["Dépense"], "Crédit": val_m["Crédit"], "Cash Flow": val_m["Revenu"]-val_m["Dépense"]-val_m["Crédit"]})
            
            st.table(pd.DataFrame(final_rows).style.format("{:,.2f} €", subset=["Revenus", "Charges", "Crédit", "Cash Flow"]))

        st.divider()
        col_add, col_list = st.columns([1, 2])
        with col_add:
            st.subheader("➕ Ajouter")
            with st.form("f_compta", clear_on_submit=True):
                d = st.date_input("Date", date.today())
                t = st.selectbox("Type", ["Revenu", "Dépense", "Crédit"])
                cpt = st.selectbox("Compte", ["CIC", "Cash"])
                m = st.number_input("Montant", min_value=0.0)
                txt = st.text_input("Commentaire")
                if st.form_submit_button("Valider"):
                    new = pd.DataFrame([[d, t, cpt, m, txt, False]], columns=df_compta.columns)
                    pd.concat([df_compta, new], ignore_index=True).to_csv(COMPTA_FILE, index=False)
                    st.rerun()
        with col_list:
            st.subheader("📝 Journal")
            ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True, column_config={"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")})
            if st.button("💾 Sauvegarder"):
                ed_c.to_csv(COMPTA_FILE, index=False)
                st.rerun()

    # --- NOUVELLES PAGES ---
    elif page == "RO 2026":
        st.title("📈 RO 2026")
    elif page == "Détail 014":
        st.title("🏠 Détail 014")
    elif page == "Détail 119":
        st.title("🏠 Détail 119")
