import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Dashboard PCI/WASH - KoboToolbox", layout="wide")

st.title("📊 Tableau de Bord Général & par Hub — PCI/WASH")
st.markdown("Application connectée en temps réel aux données de KoboToolbox (Beni, Katwa, Butembo, Goma, Mutwanga, Mabalako).")

# Paramètres API Kobo
API_TOKEN = "d64887bad92383b600f2f520c44b0bc7c778c595"
ASSET_ID = "aoJjBQ3vHyR4aPQRhSoJSR"
API_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_ID}/data.json"

@st.cache_data(ttl=300)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {API_TOKEN}"}
    try:
        response = requests.get(API_URL, headers=headers)
        if response.status_code == 200:
            data = response.json().get('results', [])
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

with st.spinner("Synchronisation des données en cours..."):
    df = fetch_kobo_data()

if df.empty:
    st.warning("⚠️ Aucune donnée récupérée pour le moment ou vérification de l'API nécessaire.")
else:
    st.success(f"Données synchronisées avec succès ! ({len(df)} rapports enregistrés)")

    # Nettoyage / Harmonisation des noms de colonnes (selon les libellés Kobo)
    # Si vos colonnes Kobo ont des noms spécifiques, adaptez-les ici si besoin
    st.sidebar.header("🔍 Filtres d'Analyse")
    
    # Recherche automatique de la colonne Hub / Zone de santé
    hub_col = next((col for col in df.columns if 'hub' in col.lower() or 'anten' in col.lower()), None)
    zs_col = next((col for col in df.columns if 'zone' in col.lower() or 'zs' in col.lower()), None)

    selected_hub = "Tous"
    if hub_col:
        hubs = list(df[hub_col].dropna().unique())
        selected_hub = st.sidebar.selectbox("Filtrer par Hub", ["Tous"] + hubs)
        if selected_hub != "Tous":
            df = df[df[hub_col] == selected_hub]

    if zs_col:
        zs_list = list(df[zs_col].dropna().unique())
        selected_zs = st.sidebar.selectbox("Filtrer par Zone de Santé", ["Toutes"] + zs_list)
        if selected_zs != "Toutes":
            df = df[df[zs_col] == selected_zs]

    # --- SECTION 1 : MÉTRIQUES GLOBALES ---
    st.markdown("---")
    st.subheader("📈 Synthèse Globale des Indicateurs")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rapports", len(df))
    
    if hub_col:
        col2.metric("Nombre de Hubs Actifs", df[hub_col].nunique())
    if zs_col:
        col3.metric("Zones de Santé Couvertes", df[zs_col].nunique())
    
    col4.metric("Statut de Synchronisation", "En direct 🟢")

    # --- SECTION 2 : VISUALISATIONS GRAPHIQUES ---
    st.markdown("---")
    st.subheader("📊 Analyses Graphiques")
    
    c1, c2 = st.columns(2)
    
    with c1:
        if hub_col:
            fig_hub = px.pie(df, names=hub_col, title="Répartition des rapports par Hub", hole=0.4)
            st.plotly_chart(fig_hub, use_container_width=True)
        else:
            st.info("Colonne 'Hub' non détectée dans les soumissions Kobo.")

    with c2:
        if zs_col:
            fig_zs = px.bar(df, x=zs_col, color=hub_col if hub_col else None, title="Volume de soumissions par Zone de Santé")
            st.plotly_chart(fig_zs, use_container_width=True)
        else:
            st.info("Colonne 'Zone de Santé' non détectée dans les soumissions Kobo.")

    # --- SECTION 3 : DONNÉES BRUTES CONSULTABLES ---
    st.markdown("---")
    with st.expander("📋 Consulter la base de données détaillée (Kobo)"):
        st.dataframe(df)
