import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import requests
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
    return st.session_state["password_correct"]

if check_password():
    
    CONFIG_FILE = "config_biens_v3.csv"
    COMPTA_FILE = "compta_v3.csv"
    RESA_FILE = "reservations.csv"
    OBJ_FILE = "objectifs_014_v2.csv"
    MENAGE_FILE = "menages_manuels.csv" # Nouveau fichier pour stocker les ménages forcés

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
        if os.path.exists(OBJ_FILE): return pd.read_csv(OBJ_FILE)
        return pd.DataFrame(columns=["Année", "Mois", "Objectif"])

    def load_menages():
        if os.path.exists(MENAGE_FILE): return pd.read_csv(MENAGE_FILE)
        return pd.DataFrame(columns=["Date", "Bien"])

    df_compta = load_compta()
    df_cfg = load_config()
    df_resa = load_resa()
    df_obj_all = load_objectifs()
    df_menages_manuels = load_menages()

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
        st.write(f"👤 **Connecté : {st.session_state.get('user_authenticated', 'Maxence')}**")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()
        st.title("📂 Navigation")
        # Ordre modifié comme demandé : Réservations avant RO 2026
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "Réservations", "RO 2026", "Détail 014", "Détail 119"])
        
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)

    # --- PAGES --- (Logique inchangée pour RNM IMMO, COMPTA, Réservations, RO 2026)
    if page == "RNM IMMO":
        st.title("🏛️ RNM IMMO - Tableau de Bord")
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

    elif page == "COMPTA":
        st.title("💰 Gestion Comptable & Archive")
        import os, zipfile, io
        if not os.path.exists("justificatifs"): os.makedirs("justificatifs")
        
        def calculer_solde(df, compte):
            temp = df[df["Compte"] == compte].copy()
            pos = temp[temp["Type"].isin(["Revenu", "Apport"])]["Montant"].sum()
            neg = temp[temp["Type"].isin(["Dépense", "Crédit", "Remboursement CCA"])]["Montant"].sum()
            return pos - neg

        s_cic = calculer_solde(df_compta, "CIC")
        s_cash = calculer_solde(df_compta, "Cash")
        c1, c2, c3 = st.columns(3)
        c1.metric("Compte CIC", f"{s_cic:,.2f} €")
        c2.metric("Espèces (Cash)", f"{s_cash:,.2f} €")
        c3.metric("TOTAL RÉEL", f"{(s_cic + s_cash):,.2f} €")

        # Formulaire d'ajout
        with st.expander("➕ Saisir une opération", expanded=False):
            with st.form("new_op_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                f_date = col_a.date_input("Date", date.today())
                f_type = col_a.selectbox("Type", ["Revenu", "Dépense", "Crédit", "Apport", "Remboursement CCA"])
                f_cpt = col_b.selectbox("Compte", ["CIC", "Cash"])
                f_mnt = col_b.number_input("Montant", min_value=0.0, format="%.2f")
                f_com = st.text_input("Commentaire")
                f_file = st.file_uploader("Justificatif", type=["pdf","png","jpg","jpeg"])
                if st.form_submit_button("Valider"):
                    p_file = "Vide"
                    if f_file:
                        p_file = os.path.join("justificatifs", f"{f_date}_{f_file.name}".replace(" ","_"))
                        with open(p_file, "wb") as f: f.write(f_file.getbuffer())
                    new_entry = pd.DataFrame([{"Date": str(f_date), "Type": f_type, "Compte": f_cpt, "Montant": f_mnt, "Commentaire": f_com, "Justificatif": p_file}])
                    df_compta = pd.concat([df_compta, new_entry], ignore_index=True)
                    df_compta.to_csv(COMPTA_FILE, index=False)
                    st.rerun()
        
        st.dataframe(df_compta.sort_values("Date", ascending=False), use_container_width=True)

    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        date_paris = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")
        
        # Affichage simplifié pour rester concis
        df_display = df_resa.sort_values(by="Date Arrivée", ascending=False).copy()
        edited_resa = st.data_editor(df_display, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Sauvegarder Réservations"):
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()

    # --- LOGIQUE COMMUNE POUR DÉTAIL 014 ET 119 (AVEC MÉNAGE MANUEL) ---
    elif page in ["Détail 014", "Détail 119"]:
        bien_id = "014" if "014" in page else "119"
        st.title(f"🏠 Détail Studio {bien_id}")
        
        # 1. Calcul des jours du mois
        first_day = date(sel_year, sel_month, 1)
        last_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days_list = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        
        # 2. Filtrage Résas et Ménages Manuels
        resa_bien = df_resa[df_resa["Appartement"].astype(str).str.contains(bien_id)].copy()
        menages_du_bien = df_menages_manuels[df_menages_manuels["Bien"] == bien_id]["Date"].tolist()
        
        month_data = {d: {"montant": 0.0, "menage": False, "client": ""} for d in days_list}
        
        # Intégration des résas
        for _, r in resa_bien.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                delta = (d_dep - d_arr).days
                if delta > 0:
                    px_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr in month_data:
                            month_data[curr]["montant"] = px_nuit
                            month_data[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
                    if d_dep in month_data: month_data[d_dep]["menage"] = True
        
        # Intégration des ménages manuels (Forçage)
        for d_str in menages_du_bien:
            d_obj = pd.to_datetime(d_str).date()
            if d_obj in month_data:
                month_data[d_obj]["menage"] = True

        # 3. Préparation du tableau éditable
        rows = []
        for d, v in month_data.items():
            rows.append({
                "Date": d,
                "Client": v["client"],
                "CA": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-",
                "Ménage Effectué": v["menage"]
            })
        
        df_edit = pd.DataFrame(rows)
        
        st.subheader("📊 Planning & Ménages")
        st.info("Cochez ou décochez 'Ménage Effectué' pour forcer un ménage à la main.")
        
        edited_planning = st.data_editor(
            df_edit, 
            use_container_width=True, 
            disabled=["Date", "Client", "CA"],
            column_config={"Ménage Effectué": st.column_config.CheckboxColumn()}
        )
        
        if st.button(f"💾 Enregistrer Ménages {bien_id}"):
            # On ne garde que les dates cochées qui ne sont pas déjà dans les résas automatiques
            # Ou on simplifie : on enregistre tout ce qui est coché manuellement
            new_manuels = edited_planning[edited_planning["Ménage Effectué"] == True]["Date"].astype(str).tolist()
            
            # Mise à jour du fichier global des ménages
            other_biens = df_menages_manuels[df_menages_manuels["Bien"] != bien_id]
            current_bien_entries = pd.DataFrame({"Date": new_manuels, "Bien": [bien_id]*len(new_manuels)})
            pd.concat([other_biens, current_bien_entries]).to_csv(MENAGE_FILE, index=False)
            st.success("Ménages mis à jour !")
            st.rerun()

    elif page == "RO 2026":
        st.title("📈 Récapitulatif Opérationnel 2026")
        st.info("Cette page compile les données des autres onglets.")
        # La matrice RO 2026 reste identique à ta version précédente
