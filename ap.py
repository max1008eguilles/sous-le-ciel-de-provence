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
            df = pd.read_csv(RESA_FILE, dtype={'Appartement': str})
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
        
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)
        
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- PAGE RNM IMMO ---
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Patrimoine")
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
            fig = px.bar(df_cfg, x="Bien", y=["Patrimoine Net Bien", "Capital Restant"], barmode="stack", color_discrete_map={"Patrimoine Net Bien": "#7030A0", "Capital Restant": "#E1E1E1"})
            st.plotly_chart(fig, use_container_width=True)

    # --- PAGE COMPTA ---
    elif page == "COMPTA":
        st.title("💰 Comptabilité")
        c1, c2, c3 = st.columns(3)
        c1.metric("CIC", f"{solde_cic:,.2f} €")
        c2.metric("Cash", f"{solde_cash_physique:,.2f} €")
        c3.metric("TOTAL", f"{total_treso_dynamique:,.2f} €")
        
        if not df_compta.empty:
            df_calc = df_compta.copy()
            df_calc['Date'] = pd.to_datetime(df_calc['Date'])
            df_calc['Année'] = df_calc['Date'].dt.strftime('%Y')
            df_calc['Mois'] = df_calc['Date'].dt.strftime('%m/%Y')
            recap_y = df_calc.groupby(['Année', 'Type'])['Montant'].sum().unstack(fill_value=0)
            
            final_rows = []
            for a in sorted(df_calc['Année'].unique(), reverse=True):
                val_y = recap_y.loc[a]
                final_rows.append({"Période": f"TOTAL {a}", "Revenus": val_y.get("Revenu",0), "Charges": val_y.get("Dépense",0), "Crédit": val_y.get("Crédit",0), "Cash Flow": val_y.get("Revenu",0)-val_y.get("Dépense",0)-val_y.get("Crédit",0)})
            st.table(pd.DataFrame(final_rows))

        ed_c = st.data_editor(df_compta, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Compta"):
            ed_c.to_csv(COMPTA_FILE, index=False)
            st.rerun()

    # --- PAGE RÉSERVATIONS (VERSION STABLE) ---
    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        
        # On travaille en texte brut pour éviter les bugs d'années
        if os.path.exists(RESA_FILE):
            df_resa = pd.read_csv(RESA_FILE, dtype=str)

        edited_resa = st.data_editor(
            df_resa, 
            num_rows="dynamic", 
            use_container_width=True,
            key="res_editor_v5",
            column_config={
                "Date Arrivée": st.column_config.TextColumn("Arrivée (AAAA-MM-JJ)"),
                "Date Départ": st.column_config.TextColumn("Départ (AAAA-MM-JJ)"),
                "Appartement": st.column_config.SelectboxColumn("Appartement", options=["014", "119"]),
                "Montant": st.column_config.NumberColumn("Montant", format="%.2f €"),
            }
        )

        if st.button("💾 SAUVEGARDER DÉFINITIVEMENT"):
            df_to_save = edited_resa.copy()
            # Auto-correction si 2025 saisi par erreur en départ
            def fix_date(row):
                d = str(row["Date Départ"])
                if "2025" in d and "2026" in str(row["Date Arrivée"]): return d.replace("2025", "2026")
                return d
            df_to_save["Date Départ"] = df_to_save.apply(fix_date, axis=1)
            df_to_save.to_csv(RESA_FILE, index=False)
            st.success("Données enregistrées !")
            st.rerun()

    # --- PAGE DÉTAIL 014 (STATS MENSUELLES INTÉGRÉES) ---
    elif page == "Détail 014":
        st.title("🏠 Détail Local 014")
        
        # 1. Préparation des Objectifs pour l'année
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_year = df_obj_all[df_obj_all["Année"].astype(str) == str(sel_year)].copy()
        if df_obj_year.empty:
            df_obj_year = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12})
        
        # 2. Calcul du réalisé mois (Lien avec Réservations)
        first_day = date(sel_year, sel_month, 1)
        last_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days_list = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        
        resa_014 = df_resa[df_resa["Appartement"].isin(["014", "14"])].copy()
        month_data = {d: {"montant": 0.0, "client": ""} for d in days_list}
        
        for _, r in resa_014.iterrows():
            try:
                d_arr = pd.to_datetime(r["Date Arrivée"]).date()
                d_dep = pd.to_datetime(r["Date Départ"]).date()
                mt = float(r["Montant"])
                delta = (d_dep - d_arr).days
                if delta > 0:
                    pr_nuit = mt / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr in month_data:
                            month_data[curr]["montant"] = pr_nuit
                            month_data[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
            except: continue

        realise_mois = sum(v["montant"] for v in month_data.values())
        obj_mois = df_obj_year.iloc[sel_month-1]["Objectif"]
        nb_nuits = sum(1 for v in month_data.values() if v["montant"] > 0)
        
        # --- BLOC STATS HAUT DE PAGE ---
        st.divider()
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Réalisé Mois", f"{realise_mois:,.2f} €")
        s2.metric("Objectif Mois", f"{obj_mois:,.0f} €")
        s3.metric("% R/O", f"{(realise_mois/obj_mois*100 if obj_mois > 0 else 0):.1f}%")
        s4.metric("Nb Nuits", f"{nb_nuits} j")
        s5.metric("% Occupation", f"{(nb_nuits/len(days_list)*100):.1f}%")
        st.divider()

        # 3. Affichage Tableaux
        col_g, col_d = st.columns([1, 4])
        with col_g:
            st.subheader(f"Global {sel_year}")
            obj_an = df_obj_year["Objectif"].sum()
            real_an = sum(pd.to_numeric(resa_014[pd.to_datetime(resa_014["Date Arrivée"]).dt.year == sel_year]["Montant"], errors='coerce').fillna(0))
            st.metric("Réalisé Année", f"{real_an:,.0f} €")
            st.progress(min(1.0, real_an/obj_an) if obj_an > 0 else 0)
            
        with col_d:
            rows = [{"Date": d.strftime("%d/%m"), "Montant": f"{v['montant']:.2f} €" if v['montant']>0 else "-", "Client": v["client"]} for d,v in month_data.items()]
            st.table(pd.DataFrame(rows))

        with st.expander("🎯 Configurer les Objectifs"):
            ed_obj = st.data_editor(df_obj_year, use_container_width=True, hide_index=True)
            if st.button("💾 Sauver Objectifs"):
                df_other = df_obj_all[df_obj_all["Année"].astype(str) != str(sel_year)]
                pd.concat([df_other, ed_obj]).to_csv(OBJ_FILE, index=False)
                st.rerun()

    elif page == "RO 2026": st.title("📈 RO 2026")
    elif page == "Détail 119": st.title("🏠 Détail 119")
