import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- SÉCURITÉ MULTI-UTILISATEURS ---
def check_password():
    """Retourne True si l'utilisateur est authentifié avec son identifiant propre."""
    def password_entered():
        user = st.session_state["username"]
        pwd = st.session_state["password"]
        
        # Vérification dans les secrets
        if user in st.secrets["passwords"] and pwd == st.secrets["passwords"][user]:
            st.session_state["password_correct"] = True
            st.session_state["user_authenticated"] = user
            del st.session_state["password"] # Sécurité
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🏛️ Accès RNM IMMO")
        st.text_input("Identifiant (Robin, Nathan ou Maxence)", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🏛️ Accès RNM IMMO")
        st.text_input("Identifiant (Robin, Nathan ou Maxence)", key="username")
        st.text_input("Mot de passe", type="password", key="password")
        st.button("Se connecter", on_click=password_entered)
        st.error("🚫 Identifiant ou mot de passe incorrect.")
        return False
    else:
        return True

if check_password():
    # --- LA SUITE DE TON CODE (CONFIG, NAVIGATION, PAGES) RESTE EXACTEMENT LA MÊME ---
    st.sidebar.write(f"👤 Utilisateur : **{st.session_state['user_authenticated']}**")
    
    # ... (Copie ici tout le reste de ton code actuel sans rien changer)
