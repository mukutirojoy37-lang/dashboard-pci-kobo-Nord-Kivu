import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Dashboard PCI/WASH - KoboToolbox", layout="wide")

st.title("📊 Tableau de Bord PCI/WASH en Temps Réel")
st.markdown("Connecté directement à votre base de données KoboToolbox.")

# Paramètres API Kobo pré-intégrés pour votre projet
API_TOKEN = "d64887bad92383b600f2f520c44b0bc7c778c595"
ASSET_ID = "aoJjBQ3vHyR4aPQRhSoJSR"
API_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_ID}/data.json"

# Fonction pour récupérer les données en direct de Kobo
@st.cache_data(ttl=300)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {API_TOKEN}"}
    try:
        response = requests.get(API_URL, headers=headers)
        if response.status_code == 200:
            data = response.json().get('results', [])
            return pd.DataFrame(data)
        else:
            st.error(f"Erreur de connexion à l'API Kobo (Code : {response.status_code})")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur technique : {e}")
        return pd.DataFrame()

# Chargement des données
with st.spinner("Synchronisation des données avec KoboToolbox..."):
    df = fetch_kobo_data()

if df.empty:
    st.warning("⚠️ Aucune donnée n'a encore été soumise sur ce formulaire ou la connexion nécessite d'être vérifiée.")
else:
    st.success(f"Données synchronisées avec succès ! ({len(df)} rapports enregistrés)")

    # Sidebar pour les filtres
    st.sidebar.header("Filtres d'analyse")
    
    if 'hub' in df.columns:
        hubs = list(df['hub'].unique())
        selected_hub = st.sidebar.selectbox("Filtrer par Hub", ["Tous"] + hubs)
        if selected_hub != "Tous":
            df = df[df['hub'] == selected_hub]

    if 'zone_sante' in df.columns:
        zs = list(df['zone_sante'].unique())
        selected_zs = st.sidebar.selectbox("Filtrer par Zone de Santé", ["Toutes"] + zs)
        if selected_zs != "Toutes":
            df = df[df['zone_sante'] == selected_zs]

    # Métriques clés
    st.subheader("Indicateurs Synthétiques")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nombre total de rapports", len(df))
    
    if 'date_rapport' in df.columns:
        col2.metric("Dernier rapport soumis", str(df['date_rapport'].max())[:10])
    
    st.markdown("---")
    st.subheader("Visualisation Graphique")
    if 'zone_sante' in df.columns:
        fig = px.histogram(df, x='zone_sante', color='hub' if 'hub' in df.columns else None, 
                           title="Répartition des rapports par Zone de Santé",
                           labels={'zone_sante': 'Zone de Santé', 'count': 'Nombre de rapports'})
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 Voir les données brutes détaillées"):
        st.dataframe(df)
