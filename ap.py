
import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import requests  # Ajouté pour la liaison avec Make
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
# --- SECTION 1 : ENVOI RAPIDE (ARRIVÉES DU JOUR) ---
st.subheader("🚀 Arrivées du jour")

# On calcule l'heure de Paris sans bibliothèque externe
# datetime.utcnow() donne l'heure de Londres, on ajoute 2h pour Paris (été)
from datetime import timedelta
aujourdhui = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")

st.write(f"Vérification des arrivées pour : **{aujourdhui}**")
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

# --- PAGE RÉSERVATIONS ---
    elif page == "Réservations":
        st.title("📅 Gestion & Envois")

        if os.path.exists(RESA_FILE):
            df_resa = pd.read_csv(RESA_FILE, dtype=str)
            
            # --- SECTION 1 : ENVOI RAPIDE (ARRIVÉES DU JOUR) ---
            st.subheader("🚀 Arrivées du jour")
            
            # Calcul unique de la date de Paris (UTC + 2h pour l'été)
            from datetime import timedelta
            date_paris = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")
            
            # On filtre le tableau avec CETTE date précise
            df_jour = df_resa[df_resa["Date Arrivée"] == date_paris].copy()

            if df_jour.empty:
                st.info(f"Aucune arrivée prévue aujourd'hui ({date_paris}).")
            else:
                st.write(f"Vérification des arrivées pour : **{date_paris}**")
                client_a_envoyer = st.selectbox(
                    "Sélectionner le client du jour :", 
                    df_jour['Prénom_Nom'].unique()
                )
                
                if st.button("📤 Envoyer le guide au client sélectionné"):
                    resa_sel = df_jour[df_jour['Prénom_Nom'] == client_a_envoyer].iloc[0]
                    
                    # Ton webhook pour le 014
                    webhook_url = "https://hook.eu2.make.com/7v3yap243qgcxbu8pc539owwgrvr32qt"
                    
                    payload = {
                        "Nom": str(resa_sel['Prénom_Nom']),
                        "Date_arrivée": str(resa_sel['Date Arrivée']),
                        "Date_départ": str(resa_sel.get('Date Départ', '')),
                        "Code_studio": str(resa_sel.get('Code Studio', '')),
                        "Code_résidence": str(resa_sel.get('Code Résidence', '')),
                        "Code_autre": str(resa_sel.get('Code Autre', '')), # <-- Ajouté !
                        "Mail": str(resa_sel.get('Mail', ''))             # <-- Présent !
                    }
                    try:
                        r = requests.post(webhook_url, json=payload)
                        if r.status_code == 200:
                            st.success(f"✅ Guide envoyé à {resa_sel['Prénom_Nom']} !")
                        else:
                            st.error(f"❌ Erreur Make (Code: {r.status_code})")
                    except Exception as e:
                        st.error(f"❌ Erreur technique : {e}")

            st.divider()

            # --- SECTION 2 : TABLEAU COMPLET ---
            st.subheader("📝 Toutes les réservations")
            
            # On affiche le reste comme avant
            edited_resa = st.data_editor(
                df_resa, 
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_full_list"
            )

            if st.button("💾 SAUVEGARDER LES MODIFICATIONS"):
                edited_resa.to_csv(RESA_FILE, index=False)
                st.success("Enregistré !")
                st.rerun()

            # --- SECTION 3 : CALENDRIER ---
            # (Garde ton code du calendrier ici sans changement)

            # --- SECTION 3 : CALENDRIER ---
            st.divider()
            st.subheader("🗓️ Calendrier de contrôle")
            evts = []
            for _, r in edited_resa.iterrows():
                try:
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
                
    # --- PAGE DÉTAIL 014 ---
    elif page == "Détail 014":
        st.title("🏠 Détail Studio 014")
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_year = df_obj_all[df_obj_all["Année"] == sel_year].copy()
        if df_obj_year.empty:
            df_obj_year = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12})
        
        with st.expander(f"🎯 Configurer les Objectifs du 014 pour l'année {sel_year}"):
            edited_obj = st.data_editor(df_obj_year, use_container_width=True, hide_index=True,
                column_config={"Année": None, "Mois": st.column_config.TextColumn(disabled=True), "Objectif": st.column_config.NumberColumn("Objectif (€)", format="%.2f €")})
            if st.button("💾 Sauvegarder Objectifs"):
                df_obj_others = df_obj_all[df_obj_all["Année"] != sel_year]
                pd.concat([df_obj_others, edited_obj], ignore_index=True).to_csv(OBJ_FILE, index=False)
                st.rerun()
        st.divider()

        # Calcul des données mensuelles
        first_day = date(sel_year, sel_month, 1)
        last_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days_list = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        resa_014 = df_resa[df_resa["Appartement"].isin(["014", "14", 14])].copy()
        month_data = {d: {"montant": 0.0, "menage": False, "client": ""} for d in days_list}
        
        for _, r in resa_014.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                delta = (d_dep - d_arr).days
                if delta > 0:
                    prix_par_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr in month_data:
                            month_data[curr]["montant"] = prix_par_nuit
                            month_data[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
                    if d_dep in month_data: month_data[d_dep]["menage"] = True

        real_m = sum(v["montant"] for v in month_data.values())
        obj_m_val = edited_obj.iloc[sel_month-1]["Objectif"]
        perc_m = (real_m / obj_m_val * 100) if obj_m_val > 0 else 0
        nuits = sum(1 for v in month_data.values() if v["montant"] > 0)
        
        # Affichage des métriques en haut
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Réalisé Mois", f"{real_m:,.2f} €")
        m2.metric("Objectif Mois", f"{obj_m_val:,.2f} €")
        m3.metric("% Réalisé", f"{perc_m:.1f}%")
        m4.metric("Nb Nuits", f"{nuits} j")
        m5.metric("Prix Moyen", f"{(real_m/nuits if nuits > 0 else 0):,.2f} €")
        m6.metric("% Occupation", f"{(nuits/len(days_list)*100):.1f}%")

        col_g, col_d = st.columns([1, 4])
        with col_g:
            st.subheader(f"Global {sel_year}")
            obj_an = edited_obj["Objectif"].sum() 
            real_an = sum(float(r["Montant"]) for _, r in resa_014.iterrows() if pd.notnull(r["Date Arrivée"]) and r["Date Arrivée"].year == sel_year)
            st.metric(f"Réalisé {sel_year}", f"{real_an:,.0f} €")
            st.write(f"Cible : {obj_an:,.0f} €")
            st.metric("Restant", f"{max(0, obj_an - real_an):,.0f} €")
            st.progress(min(1.0, real_an / obj_an))
        with col_d:
            rows = [{"Date": d.strftime("%d/%m"), "Montant": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-", "Client": v["client"], "Action": "🟢 Ménage" if v["menage"] else ""} for d,v in month_data.items()]
            st.table(pd.DataFrame(rows).style.apply(lambda x: ['background-color: #2E8B57; color: white' if 'Ménage' in str(x.Action) else '' for i in x], axis=1))

    # --- PAGE DÉTAIL 119 ---
    elif page == "Détail 119":
        st.title("🏠 Détail Studio 119")
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_year = df_obj_all[df_obj_all["Année"] == sel_year].copy()
        if df_obj_year.empty:
            df_obj_year = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12})
        
        with st.expander(f"🎯 Configurer les Objectifs du 119 pour l'année {sel_year}"):
            edited_obj = st.data_editor(df_obj_year, use_container_width=True, hide_index=True,
                column_config={"Année": None, "Mois": st.column_config.TextColumn(disabled=True), "Objectif": st.column_config.NumberColumn("Objectif (€)", format="%.2f €")})
            if st.button("💾 Sauvegarder Objectifs 119"):
                df_obj_others = df_obj_all[df_obj_all["Année"] != sel_year]
                pd.concat([df_obj_others, edited_obj], ignore_index=True).to_csv(OBJ_FILE, index=False)
                st.rerun()
        st.divider()

        first_day = date(sel_year, sel_month, 1)
        last_day = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        days_list = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        resa_119 = df_resa[df_resa["Appartement"].isin(["119"])].copy()
        month_data = {d: {"montant": 0.0, "menage": False, "client": ""} for d in days_list}
        
        for _, r in resa_119.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                delta = (d_dep - d_arr).days
                if delta > 0:
                    prix_par_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr in month_data:
                            month_data[curr]["montant"] = prix_par_nuit
                            month_data[curr]["client"] = r["Prénom_Nom"]
                        curr += timedelta(days=1)
                    if d_dep in month_data: month_data[d_dep]["menage"] = True
                        
        real_m = sum(v["montant"] for v in month_data.values())
        obj_m_val = edited_obj.iloc[sel_month-1]["Objectif"]
        perc_m = (real_m / obj_m_val * 100) if obj_m_val > 0 else 0
        nuits = sum(1 for v in month_data.values() if v["montant"] > 0)

        # Affichage des métriques en haut
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Réalisé Mois", f"{real_m:,.2f} €")
        m2.metric("Objectif Mois", f"{obj_m_val:,.2f} €")
        m3.metric("% Réalisé", f"{perc_m:.1f}%")
        m4.metric("Nb Nuits", f"{nuits} j")
        m5.metric("Prix Moyen", f"{(real_m/nuits if nuits > 0 else 0):,.2f} €")
        m6.metric("% Occupation", f"{(nuits/len(days_list)*100):.1f}%")
        
        col_g, col_d = st.columns([1, 4])
        with col_g:
            st.subheader(f"Global {sel_year}")
            obj_an = edited_obj["Objectif"].sum() 
            real_an = sum(float(r["Montant"]) for _, r in resa_119.iterrows() if pd.notnull(r["Date Arrivée"]) and r["Date Arrivée"].year == sel_year)
            st.metric(f"Réalisé {sel_year}", f"{real_an:,.0f} €")
            st.write(f"Cible : {obj_an:,.0f} €")
            st.metric("Restant", f"{max(0, obj_an - real_an):,.0f} €")
            st.progress(min(1.0, real_an / obj_an))
            
        with col_d:
            rows = [{"Date": d.strftime("%d/%m"), "Montant": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-", "Client": v["client"], "Action": "🟢 Ménage" if v["menage"] else ""} for d,v in month_data.items()]
            st.table(pd.DataFrame(rows).style.apply(lambda x: ['background-color: #2E8B57; color: white' if 'Ménage' in str(x.Action) else '' for i in x], axis=1))

    # --- PAGE RO 2026 ---
    elif page == "RO 2026":
        st.title("📈 Récapitulatif Opérationnel - RO 2026")
        
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        
        try:
            df_obj_014 = pd.read_csv("objectifs_014_v2.csv")
            df_obj_119 = pd.read_csv("objectifs_119_v2.csv")
            obj_an_014 = df_obj_014[df_obj_014["Année"] == 2026]["Objectif"].sum()
            obj_an_119 = df_obj_119[df_obj_119["Année"] == 2026]["Objectif"].sum()
        except:
            obj_an_014 = 0.0
            obj_an_119 = 0.0

        objectif_annuel_rnm = obj_an_014 + obj_an_119

        categories = [
            "Nb nuits (Total)", "% occu (Total)", "P moyen (Total)",
            "--- RNM IMMO ---",
            "CA (RNM)", "CHARGES (RNM)", "FRAIS MENAGE (RNM)", "CREDIT (RNM)", "Objectif (RNM)", "% Objectif (RNM)", "NET AV IMP (RNM)",
            "--- EGUILLES 014 ---",
            "CA (014)", "FRAIS MENAGE (014)", "Objectif (014)", "% Objectif (014)",
            "--- EGUILLES 119 ---",
            "CA (119)", "CREDIT (119)", "FRAIS MENAGE (119)", "Objectif (119)", "% Objectif (119)"
        ]
        
        final_matrix = {cat: [0.0] * 12 for cat in categories}
        for sep in ["--- RNM IMMO ---", "--- EGUILLES 014 ---", "--- EGUILLES 119 ---"]:
            final_matrix[sep] = [""] * 12

        df_resa['Date Arrivée'] = pd.to_datetime(df_resa['Date Arrivée'], errors='coerce')
        df_compta['Date'] = pd.to_datetime(df_compta['Date'], errors='coerce')

        for i, mois_nom in enumerate(mois_noms):
            m_num = i + 1
            res_m = df_resa[(df_resa['Date Arrivée'].dt.month == m_num) & (df_resa['Date Arrivée'].dt.year == 2026)]
            res_014 = res_m[res_m["Appartement"].astype(str).str.contains("14|014")]
            res_119 = res_m[res_m["Appartement"].astype(str) == "119"]
            
            o_m_014 = df_obj_014[(df_obj_014["Année"] == 2026) & (df_obj_014["Mois"] == mois_nom)]["Objectif"].sum() if 'df_obj_014' in locals() else 0
            o_m_119 = df_obj_119[(df_obj_119["Année"] == 2026) & (df_obj_119["Mois"] == mois_nom)]["Objectif"].sum() if 'df_obj_119' in locals() else 0

            final_matrix["CA (RNM)"][i] = res_014["Montant"].sum() + res_119["Montant"].sum()
            final_matrix["Objectif (RNM)"][i] = o_m_014 + o_m_119
            final_matrix["Objectif (014)"][i] = o_m_014
            final_matrix["Objectif (119)"][i] = o_m_119

        st.table(pd.DataFrame(final_matrix, index=mois_noms).T)

        st.divider()
        st.subheader("🎯 Synthèse Annuelle RNM IMMO")
        
        ca_total_an = sum(final_matrix["CA (RNM)"])
        c1, c2, c3, c4 = st.columns(4)
        c5, c6, c7, _ = st.columns(4)
        
        c1.metric("CA TOTAL", f"{ca_total_an:,.2f} €")
        c5.metric("OBJECTIF", f"{objectif_annuel_rnm:,.2f} €")
        
        perc_realisation = (ca_total_an / objectif_annuel_rnm * 100) if objectif_annuel_rnm > 0 else 0
        c6.metric("% OBJECTIF", f"{perc_realisation:.1f}%")
