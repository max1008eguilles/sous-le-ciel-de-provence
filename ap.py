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
    RESA_FILE = "reservations.csv"

    def load_config():
        if os.path.exists(CONFIG_FILE):
            df = pd.read_csv(CONFIG_FILE)
            if "Date Début" in df.columns:
                df["Date Début"] = pd.to_datetime(df["Date Début"]).dt.date
            return df
        return pd.DataFrame(columns=["Bien", "Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Mensualité", "Durée (mois)", "Taux (%)", "Date Début"])

    def load_compta():
        if os.path.exists(COMPTA_FILE):
            df = pd.read_csv(COMPTA_FILE)
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df
        return pd.DataFrame(columns=["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"])

    def load_resa():
        if os.path.exists(RESA_FILE):
            df = pd.read_csv(RESA_FILE)
            df["Date Arrivée"] = pd.to_datetime(df["Date Arrivée"]).dt.date
            df["Date Départ"] = pd.to_datetime(df["Date Départ"]).dt.date
            return df
        return pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant", "Numéro tel", "Mail", "Code Résidence", "Code Studio", "Code Autre"])

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()

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
        # Ajout de l'onglet Réservations après RO 2026
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Réservations", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE RNM IMMO (FIGÉE) ---
    if page == "RNM IMMO":
        if not df_cfg.empty:
            for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit"]:
                df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
            total_brut = df_cfg["Valeur Actuelle"].sum()
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
            total_net_patrimoine = (total_brut + total_treso_dynamique) - total_crd
            df_cfg["Patrimoine Net"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
            df_cfg["% Net"] = (df_cfg["Patrimoine Net"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
            df_cfg["% Dette"] = (df_cfg["Capital Restant"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
        else: total_brut = total_crd = total_net_patrimoine = 0

        st.title("🏛️ RNM IMMO - Tableau de Bord")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net_patrimoine:,.0f} €")
        st.divider()
        st.subheader("⚙️ Configuration des Biens")
        edited_df = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Biens"):
            cols_to_save = [c for c in edited_df.columns if c not in ["Capital Restant", "Patrimoine Net", "% Net", "% Dette"]]
            edited_df[cols_to_save].to_csv(CONFIG_FILE, index=False)
            st.rerun()
        if not df_cfg.empty:
            st.divider()
            st.subheader("📊 Détail par Bien (Répartition %)")
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net": "#7030A0", "Capital Restant": "#E1E1E1"})
            for i, row in df_cfg.iterrows():
                fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net']/2, text=f"<b>{row['Patrimoine Net']:,.0f} €</b><br>{row['% Net']:.1f}%", showarrow=False, font=dict(color="white", size=12))
                if row['Capital Restant'] > 500:
                    fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net'] + (row['Capital Restant']/2), text=f"<b>{row['Capital Restant']:,.0f} €</b><br>{row['% Dette']:.1f}%", showarrow=False, font=dict(color="#333333", size=12))
            fig.update_layout(yaxis_title="Valeur (€)", showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA (FIGÉE) ---
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

    # --- NOUVELLE PAGE RÉSERVATIONS ---
    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        
        # Logique de calcul automatique du Code Autre (Code Résidence sans le dernier caractère)
        if not df_resa.empty:
            df_resa["Code Autre"] = df_resa["Code Résidence"].astype(str).apply(lambda x: x[:-1] if len(x) > 0 else "")

        edited_resa = st.data_editor(
            df_resa, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Date Arrivée": st.column_config.DateColumn("Arrivée", format="DD/MM/YYYY"),
                "Date Départ": st.column_config.DateColumn("Départ", format="DD/MM/YYYY"),
                "Appartement": st.column_config.SelectboxColumn("Appartement", options=["014", "119"]),
                "Montant": st.column_config.NumberColumn("Montant (€)", format="%.2f €"),
                "Code Autre": st.column_config.TextColumn("Code Autre (Auto)", disabled=True)
            }
        )
        
        if st.button("💾 Sauvegarder Réservations"):
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page == "Détail 014": st.title("🏠 Détail 014")
    elif page == "Détail 119": st.title("🏠 Détail 119")
