import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from streamlit_calendar import calendar

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
    OBJ_FILE = "objectifs_014_v2.csv"

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
            df = pd.read_csv(RESA_FILE, dtype=str)
            df["Date Arrivée"] = pd.to_datetime(df["Date Arrivée"], errors='coerce').dt.date
            df["Date Départ"] = pd.to_datetime(df["Date Départ"], errors='coerce').dt.date
            if "Montant" in df.columns:
                df["Montant"] = pd.to_numeric(df["Montant"], errors='coerce').fillna(0.0)
            return df
        return pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant", "Numéro tel", "Mail", "Code Résidence", "Code Studio", "Code Autre"])

    def load_objectifs():
        if os.path.exists(OBJ_FILE):
            return pd.read_csv(OBJ_FILE)
        return pd.DataFrame(columns=["Année", "Mois", "Objectif"])

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()
    df_obj_all = load_objectifs()

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
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Réservations", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso_dynamique:,.2f} €")
        
        # Sélecteurs globaux pour les pages de détail
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)
        
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE RNM IMMO ---
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Tableau de Bord")
        # ... (Logique identique à la précédente pour le patrimoine)
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
            total_net = (total_brut + total_treso_dynamique) - total_crd
            df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
            df_cfg["% Net"] = (df_cfg["Patrimoine Net Bien"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
            df_cfg["% Dette"] = (df_cfg["Capital Restant"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
        else: total_brut = total_crd = total_net = 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{total_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{total_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.2f} €")
        m4.metric("Patrimoine Net", f"{total_net:,.0f} €")
        st.divider()
        edited_df = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Biens"):
            cols_save = [c for c in edited_df.columns if c not in ["Capital Restant", "Patrimoine Net Bien", "% Net", "% Dette"]]
            edited_df[cols_save].to_csv(CONFIG_FILE, index=False)
            st.rerun()
        if not df_cfg.empty:
            st.divider()
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            for i, row in df_cfg.iterrows():
                fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net Bien']/2, text=f"<b>{row['Patrimoine Net Bien']:,.0f}€</b><br>{row['% Net']:.1f}%", showarrow=False, font=dict(color="white"))
                if row['Capital Restant'] > 500:
                    fig.add_annotation(x=row['Bien'], y=row['Patrimoine Net Bien'] + (row['Capital Restant']/2), text=f"<b>{row['Capital Restant']:,.0f}€</b><br>{row['% Dette']:.1f}%", showarrow=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA ---
    elif page == "COMPTA":
        st.title("💰 Comptabilité - RNM IMMO")
        # ... (Logique identique à la précédente)
        c1, c2, c3 = st.columns(3)
        c1.metric("Montant CIC", f"{solde_cic:,.2f} €")
        c2.metric("Montant Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL TRESORERIE", f"{total_treso_dynamique:,.2f} €")
        if not df_compta.empty:
            st.divider(); st.subheader("📊 Analyse Financière")
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
            ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Sauvegarder Compta"):
                ed_c.to_csv(COMPTA_FILE, index=False)
                st.rerun()

  # --- PAGE RÉSERVATIONS (FIX ULTIME STABILITÉ) ---
    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        
        # 1. Chargement sans aucune transformation (on lit le texte brut du CSV)
        if os.path.exists(RESA_FILE):
            df_resa = pd.read_csv(RESA_FILE, dtype=str)
        
        # Préparation de l'affichage (on s'assure que les colonnes existent)
        for col in ["Date Arrivée", "Date Départ", "Appartement"]:
            if col not in df_resa.columns:
                df_resa[col] = ""

        # 2. L'éditeur avec une configuration de type texte pour éviter les calculs auto de Streamlit
        # Mais on garde le format visuel propre
        edited_resa = st.data_editor(
            df_resa, 
            num_rows="dynamic", 
            use_container_width=True,
            key="editor_final_v4", # Nouvelle clé pour réinitialiser le cache corrompu
            column_config={
                "Date Arrivée": st.column_config.TextColumn("Arrivée (AAAA-MM-JJ)", help="Ex: 2026-05-10"),
                "Date Départ": st.column_config.TextColumn("Départ (AAAA-MM-JJ)", help="Ex: 2026-05-15"),
                "Appartement": st.column_config.SelectboxColumn("Appartement", options=["014", "119"]),
                "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
            }
        )

        # 3. Sauvegarde "Blindée" : on nettoie les dates AVANT d'écrire
        if st.button("💾 SAUVEGARDER DÉFINITIVEMENT"):
            df_to_save = edited_resa.copy()
            
            # Petit script de secours : si l'année est 2025 mais que l'arrivée est 2026, on corrige
            def fix_year(row):
                try:
                    # Si la date de départ est avant la date d'arrivée, on force l'année de l'arrivée
                    arr = str(row["Date Arrivée"])
                    dep = str(row["Date Départ"])
                    if "2025" in dep and "2026" in arr:
                        return dep.replace("2025", "2026")
                    return dep
                except: return row["Date Départ"]

            df_to_save["Date Départ"] = df_to_save.apply(fix_year, axis=1)
            
            # On sauve en CSV
            df_to_save.to_csv(RESA_FILE, index=False)
            st.success("✅ Données nettoyées et sauvegardées !")
            st.rerun()

        st.divider()
        st.subheader("🗓️ Calendrier de contrôle")
        
        evts = []
        for _, r in edited_resa.iterrows():
            try:
                # On ne l'affiche au calendrier que si c'est valide
                d1 = pd.to_datetime(r["Date Arrivée"])
                d2 = pd.to_datetime(r["Date Départ"])
                if d2 >= d1:
                    apt = str(r["Appartement"])
                    color = "#1E90FF" if "014" in apt else "#2E8B57" if "119" in apt else "#808080"
                    evts.append({
                        "title": f"[{apt}] {r['Prénom_Nom']}", 
                        "start": d1.strftime("%Y-%m-%d"), 
                        "end": d2.strftime("%Y-%m-%d"), 
                        "color": color, "allDay": True
                    })
            except: continue
        calendar(events=evts, options={"initialView": "dayGridMonth", "locale": "fr"})
        
   # --- PAGE DÉTAIL 014 (MISE À JOUR STATS) ---
    elif page == "Détail 014":
        st.title("🏠 Détail Local 014")

        # Récupération de l'objectif pour le mois sélectionné (depuis df_obj_014)
        mois_nom = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"][sel_month-1]
        
        obj_mensuel = df_obj_014[df_obj_014["Mois"] == mois_nom]["Objectif (€)"].values[0] if mois_nom in df_obj_014["Mois"].values else 0
        
        # Calcul des stats du mois (déjà existant dans ton code normalement)
        df_m = df_day_014[df_day_014["Date"].dt.month == sel_month]
        realise_mois = df_m["Montant"].sum()
        nb_nuits = len(df_m[df_m["Montant"] > 0])
        tx_occ = (nb_nuits / len(df_m) * 100) if len(df_m) > 0 else 0
        
        # Calcul du % de réalisation de l'objectif mensuel
        percent_obj = (realise_mois / obj_mensuel * 100) if obj_mensuel > 0 else 0

        # Affichage des métriques en colonnes
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Réalisé Mois", f"{realise_mois:.2f} €")
        col2.metric("Objectif Mois", f"{obj_mensuel:.0f} €")
        col3.metric("% R/O", f"{percent_obj:.1f}%")
        col4.metric("Nb Nuits", f"{nb_nuits} j")
        col5.metric("% Occupation", f"{tx_occ:.1f}%")

        # --- LE RESTE DU CODE (Détail Année, Tableaux, etc.) RESTE INCHANGÉ ---

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page == "Détail 119": st.title("🏠 Détail 119")
