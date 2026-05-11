if not df_cfg.empty:
    st.divider()
    st.subheader("📊 Détail par Bien")
    import plotly.express as px
    
    # Préparation des données pour l'affichage des pourcentages
    df_melted = df_cfg.melt(id_vars=['Bien', 'Valeur Actuelle'], 
                           value_vars=['Patrimoine Net', 'Capital Restant'],
                           var_name='variable', value_name='value')
    
    # Calcul du % par rapport à la Valeur Actuelle
    df_melted['pct'] = (df_melted['value'] / df_melted['Valeur Actuelle'] * 100).map('{:.1f}%'.format)
    
    fig = px.bar(df_melted, x="Bien", y="value", color="variable",
                 text="pct", # Affiche le % sur le graph
                 barmode="stack",
                 color_discrete_map={'Patrimoine Net': '#7030A0', 'Capital Restant': '#E1E1E1'})
    
    fig.update_traces(textposition='inside', textfont_size=14)
    fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
    st.plotly_chart(fig, use_container_width=True)
