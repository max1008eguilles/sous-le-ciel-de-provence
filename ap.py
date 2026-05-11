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
    
    # --- FICHIERS ---
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"
    RESA_FILE = "reservations.csv"
    OBJ_FILE = "objectifs_014_v2.csv"

    # --- CHARGEMENT DES DONNÉES ---
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
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.date
            return df
        return pd.DataFrame(columns=["Date", "Type", "Compte", "Montant", "Commentaire"])

    def load_resa():
        if os.path.exists(RESA_FILE):
            return pd.read_csv(RESA_FILE, dtype=str)
        return pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant"])

    def load_objectifs():
        if os.path.exists(OBJ_FILE):
            return pd.read_csv(OBJ_FILE)
        return pd.DataFrame(columns=["Année", "Mois", "Objectif"])

    df_cfg = load_config()
    df_compta = load_compta()
    df_resa = load_resa()
    df_obj_all = load_objectifs()

    # --- CALCULS TRESORERIE ---
    def get_solde(compte_nom):
        if df_compta.empty: return 0.0
        df_c = df_compta[df_compta["Compte"] == compte_nom].copy()
        df_c["Montant"] = pd.to_numeric(df_c["Montant"], errors='coerce').fillna(0)
        rev = df_c[df_c["Type"] == "Revenu"]["Montant"].sum()
        dep = df_c[df_c["Type"] == "Dépense"]["Montant"].sum()
        cre = df_c[df_c["Type"] == "Crédit"]["Montant"].sum()
        return float(rev - dep - cre)

    solde_cic = get_solde("CIC")
    solde_cash = get_solde("Cash")
    total_treso = solde_cic + solde_cash

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("📂 Navigation")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "RO 2026", "Réservations", "Détail 014", "Détail 119"])
        st.divider()
        st.metric("Trésorerie Totale", f"{total_treso:,.2f} €")
        
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)
        
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE PRINCIPALE : RNM IMMO ---
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Patrimoine & Graphiques")
        
        if not df_cfg.empty:
            # Nettoyage numérique
            for c in ["Valeur Actuelle", "Prix Achat", "Travaux", "Frais Notaire", "Montant Crédit", "Taux (%)", "Durée (mois)"]:
                df_cfg[c] = pd.to_numeric(df_cfg[c], errors='coerce').fillna(0)
            
            # Calcul Capital Restant Dû (CRD)
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
            df_cfg["Patrimoine Net Bien"] = df_cfg["Valeur Actuelle"] - df_cfg["Capital Restant"]
            df_cfg["% Net"] = (df_cfg["Patrimoine Net Bien"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
            df_cfg["% Dette"] = (df_cfg["Capital Restant"] / df_cfg["Valeur Actuelle"] * 100).fillna(0)
            
            t_brut = df_cfg["Valeur Actuelle"].sum()
            t_crd = df_cfg["Capital Restant"].sum()
            t_net = (t_brut + total_treso) - t_crd
        else:
            t_brut = t_crd = t_net = 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Patrimoine Brut", f"{t_brut:,.0f} €")
        m2.metric("Dette Bancaire", f"{t_crd:,.0f} €")
        m3.metric("Cash disponible", f"{total_treso:,.2f} €")
        m4.metric("Patrimoine Net", f"{t_net:,.0f} €")
        
        st.divider()
        # Tableau éditable
        ed_cfg = st.data_editor(df_cfg, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Biens"):
            cols_save = [c for c in ed_cfg.columns if c not in ["Capital Restant", "Patrimoine Net Bien", "% Net", "% Dette"]]
            ed_cfg[cols_save].to_csv(CONFIG_FILE, index=False)
            st.rerun()
            
        # Graphique
        if not df_cfg.empty:
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], 
                         title="Répartition par Bien", barmode="stack",
                         color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA ---
    elif page == "COMPTA":
        st.title("💰 Comptabilité")
        st.subheader("📝 Journal")
        ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Compta"):
            ed_c.to_csv(COMPTA_FILE, index=False)
            st.rerun()

    # --- PAGE RÉSERVATIONS ---
    elif page == "Réservations":
        st.title("📅 Réservations")
        ed_resa = st.data_editor(df_resa, num_rows="dynamic", use_container_width=True, key="resa_final")
        if st.button("💾 Sauvegarder Réservations"):
            # Correction auto année 2025/2026
            df_s = ed_resa.copy()
            def fix_y(row):
                if "2025" in str(row["Date Départ"]) and "2026" in str(row["Date Arrivée"]):
                    return str(row["Date Départ"]).replace("2025", "2026")
                return row["Date Départ"]
            df_s["Date Départ"] = df_s.apply(fix_y, axis=1)
            df_s.to_csv(RESA_FILE, index=False)
            st.rerun()

    # --- PAGE DÉTAIL 014 ---
    elif page == "Détail 014":
        st.title("🏠 Détail Local 014")
        
        # Objectifs
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_y = df_obj_all[df_obj_all["Année"].astype(str) == str(sel_year)].copy()
        if df_obj_y.empty:
            df_obj_y = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12})
        
        # Calcul Réalisé Mois
        f_day = date(sel_year, sel_month, 1)
        l_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days = [f_day + timedelta(days=i) for i in range((l_day - f_day).days + 1)]
        
        # On filtre les résas pour le 014
        r014 = df_resa[df_resa["Appartement"].isin(["014", "14"])].copy()
        m_vals = {d: {"mt": 0.0, "cl": ""} for d in days}
        
        for _, r in r014.iterrows():
            try:
                da, dd = pd.to_datetime(r["Date Arrivée"]).date(), pd.to_datetime(r["Date Départ"]).date()
                mt = float(r["Montant"])
                delta = (dd - da).days
                if delta > 0:
                    pxn = mt / delta
                    curr = da
                    while curr < dd:
                        if curr in m_vals:
                            m_vals[curr]["mt"] = pxn
                            m_vals[curr]["cl"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
            except: continue

        real_m = sum(v["mt"] for v in m_vals.values())
        obj_m = float(df_obj_y.iloc[sel_month-1]["Objectif"])
        n_m = sum(1 for v in m_vals.values() if v["mt"] > 0)
        
        # --- STATS DU HAUT (Remises d'aplomb) ---
        st.divider()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Réalisé Mois", f"{real_m:,.2f} €")
        c2.metric("Objectif Mois", f"{obj_m:,.0f} €")
        c3.metric("% R/O", f"{(real_m/obj_m*100 if obj_m > 0 else 0):.1f}%")
        c4.metric("Nb Nuits", f"{n_m} j")
        c5.metric("% Occupation", f"{(n_m/len(days)*100):.1f}%")
        st.divider()

        # Détail Année et Tableau
        col_l, col_r = st.columns([1, 4])
        with col_l:
            st.subheader(f"Global {sel_year}")
            obj_an = df_obj_y["Objectif"].sum()
            real_an = sum(pd.to_numeric(r014[pd.to_datetime(r014["Date Arrivée"]).dt.year == sel_year]["Montant"], errors='coerce').fillna(0))
            st.metric("Total Année", f"{real_an:,.0f} €")
            st.progress(min(1.0, real_an/obj_an) if obj_an > 0 else 0)
            
        with col_r:
            st.subheader("📅 Calendrier")
            rows = [{"Date": d.strftime("%d/%m"), "Montant": f"{v['mt']:.2f} €" if v['mt']>0 else "-", "Client": v["cl"]} for d,v in m_vals.items()]
            st.table(pd.DataFrame(rows))

        with st.expander("🎯 Configurer Objectifs"):
            ed_obj = st.data_editor(df_obj_y, use_container_width=True, hide_index=True)
            if st.button("💾 Sauver Objectifs"):
                df_oth = df_obj_all[df_obj_all["Année"].astype(str) != str(sel_year)]
                pd.concat([df_oth, ed_obj]).to_csv(OBJ_FILE, index=False)
                st.rerun()

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page == "Détail 119": st.title("🏠 Détail 119")
