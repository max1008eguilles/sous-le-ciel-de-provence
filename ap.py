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

MENAGE_014_FILE = "menages_manuels_014.csv"

def load_menages_014():
    if os.path.exists(MENAGE_014_FILE):
        return pd.read_csv(MENAGE_014_FILE)
    return pd.DataFrame(columns=["Date"])

df_menages_014 = load_menages_014()

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
            

with st.sidebar:
    st.title("📂 RNM IMMO")
    page = st.radio("Navigation", ["Tableau de Bord", "RO 2026", "Détail 014", "Détail 119", "Ménages", "Compta"])
    
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
        st.write(f"👤 **Connecté en tant que : {st.session_state.get('user_authenticated', 'Maxence')}**")
        if st.button("Se déconnecter"):
            st.session_state["password_correct"] = False
            st.rerun()
        st.divider()
        st.title("📂 Navigation")
        page = st.radio("Aller vers :", ["RNM IMMO", "COMPTA", "Réservations", "RO 2026", "Détail 014", "Détail 119", "Ménages"])
        
        if page in ["Détail 014", "Détail 119"]:
            st.divider()
            sel_year = st.selectbox("Année", [2025, 2026, 2027], index=1)
            sel_month = st.selectbox("Mois", list(range(1, 13)), index=date.today().month - 1)

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
        m3.metric("Cash disponible", f"{total_treso_dynamique:,.0f} €")
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
        st.title("💰 Gestion Comptable & Archive")
        import os, zipfile, io
        if not os.path.exists("justificatifs"): os.makedirs("justificatifs")

        df_compta["Justificatif"] = df_compta["Justificatif"].astype(str).replace(["False", "nan", "None", ""], "Vide")
        
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

        if not df_compta.empty:
            st.divider()
            st.subheader("📊 Analyse Financière")
            df_calc = df_compta.copy()
            df_calc['Date'] = pd.to_datetime(df_calc['Date'])
            df_calc['Année'] = df_calc['Date'].dt.strftime('%Y')
            df_calc['Mois'] = df_calc['Date'].dt.strftime('%m/%Y')
            recap_y = df_calc.groupby(['Année', 'Type'])['Montant'].sum().unstack(fill_value=0)
            recap_m = df_calc.groupby(['Mois', 'Type', 'Année'])['Montant'].sum().unstack(level=1, fill_value=0)
            
            for col in ["Revenu", "Dépense", "Crédit", "Apport", "Remboursement CCA"]:
                if col not in recap_y.columns: recap_y[col] = 0.0
                if col not in recap_m.columns: recap_m[col] = 0.0
            
            final_rows = []
            for a in sorted(df_calc['Année'].unique(), reverse=True):
                v = recap_y.loc[a]
                cf_y = v["Revenu"] - (v["Dépense"] + v["Crédit"])
                final_rows.append({"Période": f"TOTAL {a}", "Revenus": v["Revenu"], "Charges": v["Dépense"], "Crédit": v["Crédit"], "Cash Flow": cf_y})
                mes_mois = recap_m.xs(a, level='Année').sort_index(ascending=False)
                for m, vm in mes_mois.iterrows():
                    cf_m = vm["Revenu"] - (vm["Dépense"] + vm["Crédit"])
                    final_rows.append({"Période": m, "Revenus": vm["Revenu"], "Charges": vm["Dépense"], "Crédit": vm["Crédit"], "Cash Flow": cf_m})
            st.table(pd.DataFrame(final_rows).set_index("Période").style.format("{:,.2f} €"))

        st.divider()
        with st.expander("➕ Saisir une nouvelle opération", expanded=False):
            with st.form("new_op_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                f_date = col_a.date_input("Date", date.today())
                f_type = col_a.selectbox("Type", ["Revenu", "Dépense", "Crédit", "Apport", "Remboursement CCA"])
                f_cpt = col_b.selectbox("Compte", ["CIC", "Cash"])
                f_mnt = col_b.number_input("Montant", min_value=0.0, format="%.2f")
                f_com = st.text_input("Commentaire")
                f_file = st.file_uploader("Joindre le justificatif", type=["pdf","png","jpg","jpeg"])
                if st.form_submit_button("Valider l'ajout"):
                    p_file = "Vide"
                    if f_file:
                        p_file = os.path.join("justificatifs", f"{f_date}_{f_file.name}".replace(" ","_"))
                        with open(p_file, "wb") as f: f.write(f_file.getbuffer())
                    new_entry = pd.DataFrame([{"Date": str(f_date), "Type": f_type, "Compte": f_cpt, "Montant": f_mnt, "Commentaire": f_com, "Justificatif": p_file}])
                    df_compta = pd.concat([df_compta, new_entry], ignore_index=True)
                    df_compta.to_csv(COMPTA_FILE, index=False)
                    st.rerun()

        st.divider()
        col_titre, col_zip = st.columns([2, 1])
        with col_titre: st.subheader("📝 Journal des opérations")
        with col_zip:
            files_to_zip = [f for f in df_compta["Justificatif"].tolist() if f != "Vide" and os.path.exists(f)]
            if files_to_zip:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as z:
                    for f in files_to_zip: z.write(f, os.path.basename(f))
                st.download_button("📦 Télécharger tout (ZIP)", buf.getvalue(), "archive_justificatifs.zip", "application/zip")

        df_display = df_compta[["Date", "Type", "Compte", "Montant", "Commentaire", "Justificatif"]].sort_values(by="Date", ascending=False)
        event = st.dataframe(df_display, use_container_width=True, on_select="rerun", selection_mode="single-row",
                            column_config={"Montant": st.column_config.NumberColumn(format="%.2f €")})

        if event.selection.rows:
            idx_sel = event.selection.rows[0]
            ligne = df_display.iloc[idx_sel]
            vrai_idx = df_display.index[idx_sel]
            path_j = str(ligne["Justificatif"])
            st.markdown(f"### 🛠️ Gestion : {ligne['Commentaire']}")
            g1, g2, g3 = st.columns(3)
            with g1:
                if path_j != "Vide" and os.path.exists(path_j):
                    with open(path_j, "rb") as f: st.download_button("📥 Télécharger", f, file_name=os.path.basename(path_j), key=f"dl_{vrai_idx}")
                    if st.button("🗑️ Supprimer fichier", key=f"df_{vrai_idx}"):
                        try: os.remove(path_j)
                        except: pass
                        df_compta.at[vrai_idx, "Justificatif"] = "Vide"
                        df_compta.to_csv(COMPTA_FILE, index=False)
                        st.rerun()
                else: st.warning("Pas de fichier.")
            with g2:
                new_up = st.file_uploader("Remplacer", type=["pdf","png","jpg","jpeg"], key=f"up_{vrai_idx}")
                if st.button("💾 Sauvegarder fichier", key=f"sf_{vrai_idx}"):
                    if new_up:
                        fp = os.path.join("justificatifs", f"ID_{vrai_idx}_{new_up.name}".replace(" ","_"))
                        with open(fp, "wb") as f: f.write(new_up.getbuffer())
                        df_compta.at[vrai_idx, "Justificatif"] = fp
                        df_compta.to_csv(COMPTA_FILE, index=False)
                        st.rerun()
            with g3:
                if st.button("🛑 SUPPRIMER LA LIGNE", type="primary", key=f"del_l_{vrai_idx}"):
                    if path_j != "Vide" and os.path.exists(path_j):
                        try: os.remove(path_j)
                        except: pass
                    df_compta = df_compta.drop(vrai_idx)
                    df_compta.to_csv(COMPTA_FILE, index=False)
                    st.rerun()

    # --- PAGE RÉSERVATIONS ---
    elif page == "Réservations":
        st.title("📅 Gestion & Envois")
        if not os.path.exists(RESA_FILE) or os.path.getsize(RESA_FILE) == 0:
            df_resa = pd.DataFrame(columns=["Date Arrivée", "Date Départ", "Appartement", "Prénom_Nom", "Montant", "Numéro tel", "Mail", "Code Résidence", "Code Studio", "Code Autre", "Guide Envoyé"])
        else:
            df_resa = pd.read_csv(RESA_FILE, dtype=str).fillna("")
        date_paris = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d")
        st.subheader("🚀 Arrivées du jour")
        df_jour = df_resa[df_resa["Date Arrivée"] == date_paris].copy()
        if df_jour.empty:
            st.info(f"Aucune arrivée prévue aujourd'hui ({date_paris}).")
        else:
            client_sel = st.selectbox("Sélectionner le client :", df_jour['Prénom_Nom'].unique())
            if st.button("📤 Envoyer le guide au client sélectionné"):
                st.success("Guide envoyé !")
        st.divider()
        st.subheader("📝 Toutes les réservations")
        df_display = df_resa.sort_values(by="Date Arrivée", ascending=False).copy()
        def add_blue_dot(val):
            if val and str(val) <= date_paris and str(val) != "": return f"🔵 {val}"
            return val
        df_display["Date Arrivée"] = df_display["Date Arrivée"].apply(add_blue_dot)
        empty_row = pd.DataFrame([{col: "" for col in df_display.columns}])
        empty_row["Guide Envoyé"] = "Non"
        df_with_add = pd.concat([empty_row, df_display], ignore_index=True)
        column_config = {"Guide Envoyé": st.column_config.SelectboxColumn(options=["Non", "Oui"], default="Non")}
        edited_resa = st.data_editor(df_with_add, num_rows="dynamic", use_container_width=True, key="editor_final_stable", column_config=column_config)
        if st.button("💾 SAUVEGARDER LES MODIFICATIONS"):
            df_to_save = edited_resa[edited_resa['Prénom_Nom'] != ""].copy()
            df_to_save["Date Arrivée"] = df_to_save["Date Arrivée"].str.replace("🔵 ", "", regex=False)
            def get_code_autre(row):
                res = str(row.get('Code Résidence', ''))
                return res[:-1] if len(res) > 1 else row.get('Code Autre', '')
            df_to_save['Code Autre'] = df_to_save.apply(get_code_autre, axis=1)
            df_to_save = df_to_save.sort_values(by="Date Arrivée", ascending=False)
            df_to_save.to_csv(RESA_FILE, index=False)
            st.success("Sauvegarde réussie !")
            st.rerun()
        st.divider()
        st.subheader("🗓️ Vue Calendrier")
        calendar_events = []
        for _, row in df_resa.iterrows():
            if row['Date Arrivée'] and row['Date Départ']:
                calendar_events.append({"title": f"{row['Prénom_Nom']} ({row['Appartement']})", "start": row['Date Arrivée'], "end": row['Date Départ'], "color": "#FF4B4B" if "14" in str(row['Appartement']) else "#1C83E1"})
        calendar(events=calendar_events, options={"initialView": "dayGridMonth"}, key="cal_final")

    # --- PAGE DÉTAIL 014 ---
    elif page == "Détail 014":
        st.title("🏠 Détail Studio 014")
        
        # --- LOGIQUE MÉNAGES ---
        MENAGE_014_FILE = "menages_manuels_014.csv"
        dict_menages = {}
        has_history = False

        if os.path.exists(MENAGE_014_FILE):
            try:
                df_m_save = pd.read_csv(MENAGE_014_FILE)
                if "Etat" in df_m_save.columns:
                    dict_menages = dict(zip(df_m_save["Date"], df_m_save["Etat"].astype(bool)))
                    has_history = True
            except Exception:
                pass 

        # --- CONFIGURATION OBJECTIFS (Expander) ---
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_year = df_obj_all[df_obj_all["Année"] == sel_year].copy()
        if df_obj_year.empty:
            df_obj_year = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1250.0]*12})
        
        with st.expander("🎯 Configurer les Objectifs"):
            edited_obj = st.data_editor(df_obj_year, use_container_width=True, hide_index=True,
                column_config={"Année": None, "Mois": st.column_config.TextColumn(disabled=True), "Objectif": st.column_config.NumberColumn("Objectif (€)", format="%.2f €")})
            if st.button("💾 Sauvegarder Objectifs"):
                df_obj_others = df_obj_all[df_obj_all["Année"] != sel_year]
                pd.concat([df_obj_others, edited_obj], ignore_index=True).to_csv(OBJ_FILE, index=False)
                st.rerun()
        
        st.divider()

        # --- CALCUL DES DONNÉES (MOIS & ANNÉE CUMULÉE) ---
        # Données de base pour le 014
        resa_014 = df_resa[df_resa["Appartement"].isin(["014", "14", 14])].copy()
        
        # 1. Calcul Annuel Cumulé (du 01/01 au dernier jour du mois sélectionné)
        last_day_selected_month = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        
        # Filtre les résas qui touchent à l'année en cours jusqu'au mois sélectionné
        real_an_cumule = 0.0
        nuits_an_cumule = 0
        
        for _, r in resa_014.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                # On ne compte que les nuitées comprises entre le 01/01 et la fin du mois choisi
                delta = (d_dep - d_arr).days
                if delta > 0:
                    prix_par_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr.year == sel_year and curr <= last_day_selected_month:
                            real_an_cumule += prix_par_nuit
                            nuits_an_cumule += 1
                        curr += timedelta(days=1)

        # Objectif annuel cumulé
        obj_an_cumule = edited_obj.iloc[:sel_month]["Objectif"].sum()

        # 2. Calcul spécifique au Mois Sélectionné
        first_day_m = date(sel_year, sel_month, 1)
        days_list_m = [first_day_m + timedelta(days=i) for i in range((last_day_selected_month - first_day_m).days + 1)]
        month_data = {d: {"montant": 0.0, "client": "", "auto_menage": False} for d in days_list_m}
        
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
                    if d_dep in month_data:
                        month_data[d_dep]["auto_menage"] = True

        real_m = sum(v["montant"] for v in month_data.values())
        obj_m_val = edited_obj.iloc[sel_month-1]["Objectif"]
        nuits_m = sum(1 for v in month_data.values() if v["montant"] > 0)

        # --- AFFICHAGE DES MÉTRIQUES ---
        st.subheader(f"📊 Statistiques Cumulées (Jan. à {mois_noms[sel_month-1]} {sel_year})")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Réalisé Cumulé", f"{real_an_cumule:,.2f} €")
        a2.metric("Objectif Cumulé", f"{obj_an_cumule:,.2f} €")
        a3.metric("% vs Objectif", f"{(real_an_cumule/obj_an_cumule*100 if obj_an_cumule>0 else 0):.1f}%")
        a4.metric("Total Nuits", f"{nuits_an_cumule} j")

        st.write("") # Espacement

        st.subheader(f"📅 Détail du mois : {mois_noms[sel_month-1]}")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Mois", f"{real_m:,.2f} €")
        m2.metric("Objectif", f"{obj_m_val:,.2f} €")
        m3.metric("%", f"{(real_m/obj_m_val*100 if obj_m_val>0 else 0):.1f}%")
        m4.metric("Nuits", f"{nuits_m} j")
        m5.metric("Prix Moy.", f"{(real_m/nuits_m if nuits_m > 0 else 0):,.2f} €")
        m6.metric("% Occ.", f"{(nuits_m/len(days_list_m)*100):.1f}%")

        st.divider()

        # --- TABLEAU UNIQUE INTERACTIF ---
        st.subheader("📋 Suivi Détaillé & Ménages")
        
        rows = []
        for d, v in month_data.items():
            d_str = str(d)
            is_checked = dict_menages.get(d_str, v["auto_menage"]) if has_history else v["auto_menage"]
                
            rows.append({
                "Date_Full": d_str,
                "Date": d.strftime("%d/%m"),
                "Montant": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-",
                "Client": v["client"],
                "Ménage": is_checked
            })
        
        df_display = pd.DataFrame(rows)

        def style_rows(row):
            if row["Ménage"]:
                return ['background-color: #2E8B57; color: white'] * len(row)
            return [''] * len(row)

        edited_df = st.data_editor(
            df_display.style.apply(style_rows, axis=1),
            use_container_width=True,
            hide_index=True,
            disabled=["Date", "Montant", "Client"],
            column_config={
                "Date_Full": None,
                "Ménage": st.column_config.CheckboxColumn("Ménage ?", default=False)
            },
            key="unique_editor_014"
        )

        if st.button("💾 Enregistrer le planning"):
            # 1. Charger l'existant pour ne pas perdre les autres mois
            if os.path.exists(MENAGE_014_FILE):
                df_global = pd.read_csv(MENAGE_014_FILE)
            else:
                df_global = pd.DataFrame(columns=["Date", "Etat"])

            # 2. Préparer les données du mois actuel
            df_month = pd.DataFrame({
                "Date": edited_df["Date_Full"],
                "Etat": edited_df["Ménage"]
            })

            # 3. Fusionner : On enlève les dates du mois en cours de l'historique et on ajoute les nouvelles
            df_global = df_global[~df_global["Date"].isin(df_month["Date"])]
            df_final = pd.concat([df_global, df_month], ignore_index=True)

            # 4. Sauvegarder le tout
            df_final.to_csv(MENAGE_014_FILE, index=False)
            st.success("Modifications enregistrées (Historique conservé) !")
            st.rerun()
            
    # --- PAGE DÉTAIL 119 ---
    elif page == "Détail 119":
        st.title("🏠 Détail Studio 119")
        
        # --- LOGIQUE MÉNAGES SPÉCIFIQUE 119 ---
        MENAGE_119_FILE = "menages_manuels_119.csv"
        dict_menages = {}
        has_history = False

        if os.path.exists(MENAGE_119_FILE):
            try:
                df_m_save = pd.read_csv(MENAGE_119_FILE)
                if "Etat" in df_m_save.columns:
                    dict_menages = dict(zip(df_m_save["Date"], df_m_save["Etat"].astype(bool)))
                    has_history = True
            except Exception:
                pass 

        # --- CONFIGURATION OBJECTIFS ---
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        df_obj_year = df_obj_all[df_obj_all["Année"] == sel_year].copy()
        # On peut adapter l'objectif par défaut si besoin (ex: 1350€ pour le 119)
        if df_obj_year.empty:
            df_obj_year = pd.DataFrame({"Année": [sel_year]*12, "Mois": mois_noms, "Objectif": [1350.0]*12})
        
        with st.expander("🎯 Configurer les Objectifs du 119"):
            edited_obj = st.data_editor(df_obj_year, use_container_width=True, hide_index=True,
                column_config={"Année": None, "Mois": st.column_config.TextColumn(disabled=True), "Objectif": st.column_config.NumberColumn("Objectif (€)", format="%.2f €")})
            if st.button("💾 Sauvegarder Objectifs 119"):
                df_obj_others = df_obj_all[df_obj_all["Année"] != sel_year]
                pd.concat([df_obj_others, edited_obj], ignore_index=True).to_csv(OBJ_FILE, index=False)
                st.rerun()
        
        st.divider()

        # --- CALCUL DES DONNÉES (MOIS & ANNÉE CUMULÉE) ---
        # Filtre spécifique pour le 119
        resa_119 = df_resa[df_resa["Appartement"].isin(["119", 119])].copy()
        
        # 1. Calcul Annuel Cumulé
        last_day_selected_month = (date(sel_year, sel_month % 12 + 1, 1) - timedelta(days=1)) if sel_month < 12 else date(sel_year, 12, 31)
        
        real_an_cumule = 0.0
        nuits_an_cumule = 0
        
        for _, r in resa_119.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                d_arr, d_dep = r["Date Arrivée"], r["Date Départ"]
                delta = (d_dep - d_arr).days
                if delta > 0:
                    prix_par_nuit = float(r["Montant"]) / delta
                    curr = d_arr
                    while curr < d_dep:
                        if curr.year == sel_year and curr <= last_day_selected_month:
                            real_an_cumule += prix_par_nuit
                            nuits_an_cumule += 1
                        curr += timedelta(days=1)

        obj_an_cumule = edited_obj.iloc[:sel_month]["Objectif"].sum()

        # 2. Calcul spécifique au Mois Sélectionné
        first_day_m = date(sel_year, sel_month, 1)
        days_list_m = [first_day_m + timedelta(days=i) for i in range((last_day_selected_month - first_day_m).days + 1)]
        month_data = {d: {"montant": 0.0, "client": "", "auto_menage": False} for d in days_list_m}
        
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
                    if d_dep in month_data:
                        month_data[d_dep]["auto_menage"] = True

        real_m = sum(v["montant"] for v in month_data.values())
        obj_m_val = edited_obj.iloc[sel_month-1]["Objectif"]
        nuits_m = sum(1 for v in month_data.values() if v["montant"] > 0)

        # --- AFFICHAGE DES MÉTRIQUES ---
        st.subheader(f"📊 Statistiques Cumulées (Jan. à {mois_noms[sel_month-1]} {sel_year})")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Réalisé Cumulé", f"{real_an_cumule:,.2f} €")
        a2.metric("Objectif Cumulé", f"{obj_an_cumule:,.2f} €")
        a3.metric("% vs Objectif", f"{(real_an_cumule/obj_an_cumule*100 if obj_an_cumule>0 else 0):.1f}%")
        a4.metric("Total Nuits", f"{nuits_an_cumule} j")

        st.write("") 

        st.subheader(f"📅 Détail du mois : {mois_noms[sel_month-1]}")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Mois", f"{real_m:,.2f} €")
        m2.metric("Objectif", f"{obj_m_val:,.2f} €")
        m3.metric("%", f"{(real_m/obj_m_val*100 if obj_m_val>0 else 0):.1f}%")
        m4.metric("Nuits", f"{nuits_m} j")
        m5.metric("Prix Moy.", f"{(real_m/nuits_m if nuits_m > 0 else 0):,.2f} €")
        m6.metric("% Occ.", f"{(nuits_m/len(days_list_m)*100):.1f}%")

        st.divider()

        # --- TABLEAU UNIQUE INTERACTIF ---
        st.subheader("📋 Suivi Détaillé & Ménages (119)")
        
        rows = []
        for d, v in month_data.items():
            d_str = str(d)
            is_checked = dict_menages.get(d_str, v["auto_menage"]) if has_history else v["auto_menage"]
                
            rows.append({
                "Date_Full": d_str,
                "Date": d.strftime("%d/%m"),
                "Montant": f"{v['montant']:.2f} €" if v['montant'] > 0 else "-",
                "Client": v["client"],
                "Ménage": is_checked
            })
        
        df_display = pd.DataFrame(rows)

        def style_rows(row):
            if row["Ménage"]:
                return ['background-color: #2E8B57; color: white'] * len(row)
            return [''] * len(row)

        edited_df = st.data_editor(
            df_display.style.apply(style_rows, axis=1),
            use_container_width=True,
            hide_index=True,
            disabled=["Date", "Montant", "Client"],
            column_config={
                "Date_Full": None,
                "Ménage": st.column_config.CheckboxColumn("Ménage ?", default=False)
            },
            key="unique_editor_119"
        )

        if st.button("💾 Enregistrer le planning 119"):
            # 1. Charger l'existant
            if os.path.exists(MENAGE_119_FILE):
                df_global = pd.read_csv(MENAGE_119_FILE)
            else:
                df_global = pd.DataFrame(columns=["Date", "Etat"])

            # 2. Préparer les données du mois actuel
            df_month = pd.DataFrame({
                "Date": edited_df["Date_Full"],
                "Etat": edited_df["Ménage"]
            })

            # 3. Fusionner
            df_global = df_global[~df_global["Date"].isin(df_month["Date"])]
            df_final = pd.concat([df_global, df_month], ignore_index=True)

            # 4. Sauvegarder
            df_final.to_csv(MENAGE_119_FILE, index=False)
            st.success("Modifications enregistrées pour le 119 (Historique conservé) !")
            st.rerun()
   
    # MENAGESSS
   # --- PAGE RÉCAPITULATIF COMPLET MÉNAGES 2026 ---
    elif page == "Ménages":
        st.title("🧹 Suivi Annuel des Ménages 2026")
        
        PRIX_MENAGE_UNITAIRE = 20.0 
        PAIEMENTS_FILE = "statut_paiements_menages.csv"
        COURSES_FILE = "frais_courses.csv"
        ENVOYES_FILE = "menages_envoyes.csv" # Fichier pour suivre les notifications

        # 1. Chargement des données
        if os.path.exists(PAIEMENTS_FILE):
            try:
                df_p = pd.read_csv(PAIEMENTS_FILE)
                dict_paye = dict(zip(df_p["Clef"], df_p["Payé"].astype(bool)))
            except: dict_paye = {}
        else: dict_paye = {}

        # Chargement de l'historique des envois WhatsApp
        if os.path.exists(ENVOYES_FILE):
            try: list_envoyes = pd.read_csv(ENVOYES_FILE)["Clef"].tolist()
            except: list_envoyes = []
        else: list_envoyes = []

        all_data = []
        sources = {"Studio 014": "menages_manuels_014.csv", "Studio 119": "menages_manuels_119.csv"}
        
        for appt_name, file_path in sources.items():
            if os.path.exists(file_path):
                df_src = pd.read_csv(file_path)
                col_etat = next((c for c in ["Etat", "Ménage ?", "Ménage"] if c in df_src.columns), None)
                if "Date" in df_src.columns and col_etat:
                    df_checked = df_src[df_src[col_etat] == True].copy()
                    for _, row in df_checked.iterrows():
                        d_str = str(row["Date"])
                        clef = f"{appt_name}_{d_str}"
                        try:
                            d_obj = pd.to_datetime(d_str).date()
                            if d_obj.year == 2026:
                                all_data.append({
                                    "Clef": clef, "Date": d_obj, "Appartement": appt_name,
                                    "Statut": "Passé" if d_obj < date.today() else "À venir",
                                    "Payé": dict_paye.get(clef, False),
                                    "Deja_Envoye": clef in list_envoyes
                                })
                        except: continue

        # 2. Métriques Financières
        if os.path.exists(COURSES_FILE):
            try: montant_courses = pd.read_csv(COURSES_FILE)["montant"].iloc[0]
            except: montant_courses = 0.0
        else: montant_courses = 0.0

        if all_data:
            df_total = pd.DataFrame(all_data).drop_duplicates(subset=['Clef']).sort_values(by="Date", ascending=False)
            df_du = df_total[(df_total["Statut"] == "Passé") & (df_total["Payé"] == False)]
            total_prestations = len(df_du) * PRIX_MENAGE_UNITAIRE
            total_global_du = total_prestations + montant_courses
        else:
            df_total = pd.DataFrame(columns=["Clef", "Date", "Appartement", "Statut", "Payé", "Deja_Envoye"])
            total_prestations = 0.0 ; total_global_du = montant_courses

        m1, m2, m3 = st.columns(3)
        m1.metric("Ménages à régler", len(df_du))
        m2.metric("Total Prestations", f"{total_prestations:.2f} €")
        m3.metric("TOTAL GLOBAL DÛ", f"{total_global_du:.2f} €")

        with st.expander("🛒 Gérer les frais de courses"):
            new_montant = st.number_input("Cumul courses (€)", value=float(montant_courses), step=1.0)
            if st.button("Enregistrer Montant Courses"):
                pd.DataFrame({"montant": [new_montant]}).to_csv(COURSES_FILE, index=False)
                st.rerun()

        # 3. BLOC CODES D'ACCÈS
        st.divider()
        st.subheader("🔑 Codes d'Accès")
        
        temp_resa = df_resa.copy()
        temp_resa['Date Arrivée'] = pd.to_datetime(temp_resa['Date Arrivée'], errors='coerce')
        today = date.today()

        try:
            code_res_val = temp_resa[(temp_resa['Date Arrivée'].dt.month == today.month) & (temp_resa['Code Résidence'].notna())].iloc[0]['Code Résidence']
        except: code_res_val = "À vérifier"

        try:
            next_119 = temp_resa[(temp_resa['Appartement'].astype(str) == "119") & (temp_resa['Date Arrivée'].dt.date >= today)].sort_values(by='Date Arrivée').iloc[0]
            code_119_val = next_119['Code Studio']
            date_119 = next_119['Date Arrivée'].strftime('%d/%m')
        except: code_119_val = "N/A" ; date_119 = "-"

        c_code1, c_code2, c_code3 = st.columns(3)
        c_code1.info(f"**🏢 RÉSIDENCE**\n\n# {code_res_val}")
        c_code2.success(f"**🚪 STUDIO 014**\n\n# 178459")
        c_code3.warning(f"**🔑 STUDIO 119** (le {date_119})\n\n# {code_119_val}")

        # --- 4. BOUTON WHATSAPP AVEC DÉTECTION DES NOUVEAUTÉS ---
        st.write("")
        menages_futurs = df_total[df_total["Statut"] == "À venir"].sort_values(by="Date")
        
        if not menages_futurs.empty:
            texte_menages = ""
            nouvelles_clefs = []
            
            for _, m in menages_futurs.iterrows():
                # On ajoute un marqueur visuel si c'est la première fois qu'on l'envoie
                prefixe = "🆕 " if not m["Deja_Envoye"] else "- "
                texte_menages += f"{prefixe}{m['Appartement']} le {m['Date'].strftime('%d/%m')}\n"
                nouvelles_clefs.append(m["Clef"])
            
            message_whatsapp = (
                f"✨ *PLANNING MÉNAGES À VENIR*\n"
                f"_(🆕 = Nouvelle date ajoutée)_\n\n"
                f"{texte_menages}\n"
                f"🔑 *RAPPEL DES CODES :*\n"
                f"- Résidence : {code_res_val}\n"
                f"- Studio 014 : 178459\n"
                f"- Studio 119 : {code_119_val} (dès le {date_119})\n\n"
                f"Merci ! 🙏"
            )
            
            import urllib.parse
            msg_encoded = urllib.parse.quote(message_whatsapp)
            whatsapp_url = f"https://wa.me/?text={msg_encoded}"
            
            col_wa1, col_wa2 = st.columns([3, 1])
            with col_wa1:
                st.link_button("📲 Envoyer Planning & Codes sur WhatsApp", whatsapp_url, use_container_width=True, type="primary")
            with col_wa2:
                if st.button("✅ Marquer comme notifiés"):
                    # On enregistre toutes les clefs actuelles comme étant "déjà envoyées"
                    pd.DataFrame({"Clef": list(set(list_envoyes + nouvelles_clefs))}).to_csv(ENVOYES_FILE, index=False)
                    st.success("Planning actualisé !")
                    st.rerun()

        # 5. HISTORIQUE
        st.divider()
        st.subheader("📋 Historique des passages")
        # ... (reste du code identique pour l'historique)

        if not df_total.empty:
            df_display = df_total.copy()
            df_display["Date"] = df_display["Date"].apply(lambda x: x.strftime("%d/%m/%Y"))
            
            def style_rows(row):
                if row["Payé"]: return ['background-color: rgba(144, 238, 144, 0.2)'] * len(row)
                if row["Statut"] == "Passé": return ['background-color: rgba(255, 99, 71, 0.2)'] * len(row)
                return [''] * len(row)

            edited_df = st.data_editor(
                df_display.style.apply(style_rows, axis=1),
                column_config={
                    "Payé": st.column_config.CheckboxColumn("Réglé ?"),
                    "Clef": None, "Statut": st.column_config.TextColumn("Échéance")
                },
                disabled=["Date", "Appartement", "Statut"],
                hide_index=True, use_container_width=True, key="editor_menages_final"
            )

            if st.button("💾 Enregistrer les règlements"):
                for _, row in edited_df.iterrows():
                    dict_paye[row["Clef"]] = row["Payé"]
                pd.DataFrame([{"Clef": k, "Payé": v} for k, v in dict_paye.items()]).to_csv(PAIEMENTS_FILE, index=False)
                st.success("Enregistré !")
                st.rerun()

        #RO2026
    elif page == "RO 2026":
        st.title("🚀 RNM IMMO - Cockpit de Pilotage 2026")
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        
        # --- 1. RÉCUPÉRATION DES PARAMÈTRES SOURCES ---
        # Crédits depuis RNM IMMO (Source: Capture 21.14.11)
        CREDIT_119 = 689.72 
        CREDIT_014 = 0.0
        PRIX_MENAGE = 20.0

        try:
            df_compta = pd.read_csv("compta.csv")
            df_obj = pd.read_csv("objectifs_014_v2.csv")
        except:
            df_compta = pd.DataFrame() ; df_obj = pd.DataFrame()

        # --- 2. CALCULS DE PERFORMANCE (DATA ENGINE) ---
        stats = {m: {"014": {}, "119": {}, "RNM": {}} for m in mois_noms}
        df_resa['Date Arrivée'] = pd.to_datetime(df_resa['Date Arrivée'], errors='coerce')
        
        for i, mois in enumerate(mois_noms):
            m_num = i + 1
            # Filtrage Data
            res_m = df_resa[(df_resa['Date Arrivée'].dt.month == m_num) & (df_resa['Date Arrivée'].dt.year == 2026)]
            res_014 = res_m[res_m["Appartement"].astype(str).str.contains("14|014")]
            res_119 = res_m[res_m["Appartement"].astype(str) == "119"]
            
            # Métriques Studio 014
            stats[mois]["014"]["CA"] = res_014["Montant"].sum()
            stats[mois]["014"]["Nuits"] = res_014["Nuits"].sum() if "Nuits" in res_014.columns else len(res_014)
            stats[mois]["014"]["Occ"] = (stats[mois]["014"]["Nuits"] / 31 * 100) # Simplifié
            
            # Métriques Studio 119
            stats[mois]["119"]["CA"] = res_119["Montant"].sum()
            stats[mois]["119"]["Nuits"] = res_119["Nuits"].sum() if "Nuits" in res_119.columns else len(res_119)
            stats[mois]["119"]["Occ"] = (stats[mois]["119"]["Nuits"] / 31 * 100)
            
            # Métriques Global RNM
            stats[mois]["RNM"]["CA"] = stats[mois]["014"]["CA"] + stats[mois]["119"]["CA"]
            stats[mois]["RNM"]["Nuits"] = stats[mois]["014"]["Nuits"] + stats[mois]["119"]["Nuits"]
            stats[mois]["RNM"]["Occ"] = (stats[mois]["RNM"]["Nuits"] / 62 * 100)
            stats[mois]["RNM"]["PMoy"] = (stats[mois]["RNM"]["CA"] / stats[mois]["RNM"]["Nuits"]) if stats[mois]["RNM"]["Nuits"] > 0 else 0
            
            # Charges (Compta) & Crédits
            ch_m = 0.0
            if not df_compta.empty:
                df_compta['Date'] = pd.to_datetime(df_compta['Date'], errors='coerce')
                ch_m = df_compta[(df_compta['Date'].dt.month == m_num) & (df_compta['Type'] == "Dépense")]["Montant"].sum()
            
            stats[mois]["RNM"]["Charges"] = ch_m
            stats[mois]["RNM"]["Credits"] = CREDIT_119 + CREDIT_014
            stats[mois]["RNM"]["Net"] = stats[mois]["RNM"]["CA"] - ch_m - stats[mois]["RNM"]["Credits"]

        # --- 3. AFFICHAGE DES KPI GLOBAUX (Haut de page) ---
        total_ca = sum(m["RNM"]["CA"] for m in stats.values())
        total_net = sum(m["RNM"]["Net"] for m in stats.values())
        occ_moy = sum(m["RNM"]["Occ"] for m in stats.values()) / 12

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 CA Annuel Cumulé", f"{total_ca:,.0f} €")
        c2.metric("📈 Taux d'Occupation Moyen", f"{occ_moy:.1f} %")
        c3.metric("📊 Cash Flow Net (An)", f"{total_net:,.0f} €")
        
        st.divider()

        # --- 4. TABLEAU DE BORD MODERNE (MODALITÉS DE PILOTAGE) ---
        st.subheader("🗓️ Analyse Mensuelle Consolidée")
        
        # Construction d'un DataFrame propre pour l'affichage
        pilotage_data = []
        for m in mois_noms:
            pilotage_data.append({
                "Mois": m,
                "CA RNM": stats[m]["RNM"]["CA"],
                "Occ %": stats[m]["RNM"]["Occ"],
                "Prix Moy.": stats[m]["RNM"]["PMoy"],
                "Charges (Compta)": stats[m]["RNM"]["Charges"],
                "Crédits": stats[m]["RNM"]["Credits"],
                "NET (Cash Flow)": stats[m]["RNM"]["Net"],
                "CA 014": stats[m]["014"]["CA"],
                "CA 119": stats[m]["119"]["CA"]
            })
        
        df_final = pd.DataFrame(pilotage_data).set_index("Mois")
        
        # Affichage avec formatage
        st.dataframe(
            df_final.style.format({
                "CA RNM": "{:,.0f} €", "Occ %": "{:.1f} %", "Prix Moy.": "{:.1f} €",
                "Charges (Compta)": "{:,.0f} €", "Crédits": "{:,.2f} €", 
                "NET (Cash Flow)": "{:,.0f} €", "CA 014": "{:,.0f} €", "CA 119": "{:,.0f} €"
            }), 
            use_container_width=True
        )

        # --- 5. FOCUS PAR APPARTEMENT ---
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Performance Studio 014**")
            st.caption(f"CA Annuel : {sum(m['014']['CA'] for m in stats.values()):,.0f} €")
            st.caption(f"Occupation : {sum(m['014']['Occ'] for m in stats.values())/12:.1f} %")
        with col_b:
            st.write("**Performance Studio 119**")
            st.caption(f"CA Annuel : {sum(m['119']['CA'] for m in stats.values()):,.0f} €")
            st.caption(f"Occupation : {sum(m['119']['Occ'] for m in stats.values())/12:.1f} %")
