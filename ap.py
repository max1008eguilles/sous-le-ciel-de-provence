# --- PAGE RÉSERVATIONS (CORRIGÉE : 014 FIX, FORMAT €, TEL) ---
    elif page == "Réservations":
        st.title("📅 Gestion des Réservations")
        
        # Sécurité pour le calcul automatique du Code Autre
        df_resa["Code Résidence"] = df_resa["Code Résidence"].fillna("").astype(str)
        df_resa["Code Autre"] = df_resa["Code Résidence"].apply(lambda x: x[:-1] if len(x) > 1 else "")

        # Configuration des colonnes pour corriger les bugs et ajouter les formats
        edited_resa = st.data_editor(
            df_resa, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "Date Arrivée": st.column_config.DateColumn("Arrivée"),
                "Date Départ": st.column_config.DateColumn("Départ"),
                # Correction 014 : On accepte le texte et le nombre pour être sûr que ça sauvegarde
                "Appartement": st.column_config.SelectboxColumn(
                    "Appartement", 
                    options=["014", "119", "14"] 
                ),
                # Format Monétaire €
                "Montant": st.column_config.NumberColumn(
                    "Montant",
                    format="%.2f €"
                ),
                # Format Téléphone (en texte pour garder le 0 au début)
                "Numéro tel": st.column_config.TextColumn(
                    "Numéro tel",
                    help="Entrez le numéro commençant par 0"
                ),
                "Code Autre": st.column_config.TextColumn("Code Autre", disabled=True)
            }
        )
        
        if st.button("💾 Sauvegarder Réservations"):
            # Avant de sauvegarder, on s'assure que les 14 deviennent des 014 pour la cohérence
            edited_resa["Appartement"] = edited_resa["Appartement"].astype(str).replace("14", "014")
            edited_resa.to_csv(RESA_FILE, index=False)
            st.rerun()

        st.divider()
        st.subheader("🗓️ Calendrier Mensuel")
        evts = []
        for _, r in edited_resa.iterrows():
            if pd.notnull(r["Date Arrivée"]) and pd.notnull(r["Date Départ"]):
                apt_str = str(r["Appartement"])
                # Bleu pour 014, Vert pour 119
                color = "#1E90FF" if "014" in apt_str or apt_str == "14" else "#2E8B57" if "119" in apt_str else "#808080"
                
                evts.append({
                    "title": f"[{apt_str}] {r['Prénom_Nom']}", 
                    "start": str(r["Date Arrivée"]), 
                    "end": str(r["Date Départ"]), 
                    "color": color, 
                    "allDay": True
                })
        
        calendar(events=evts, options={"initialView": "dayGridMonth", "locale": "fr"})
