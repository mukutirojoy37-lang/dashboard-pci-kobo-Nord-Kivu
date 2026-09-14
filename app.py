import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Dashboard PCI/WASH - Nord-Kivu", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            padding: 18px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 15px;
        }
        .metric-title { font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; }
        .metric-value { font-size: 24px; font-weight: 700; color: #111827; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Tableau de Bord PCI/WASH — Suivi Opérationnel")
st.markdown("Pilotage en temps réel des indicateurs clés par Hub et par Zone de Santé (KoboToolbox).")

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

with st.spinner("Chargement des données en direct..."):
    df = fetch_kobo_data()

if df.empty:
    st.warning("⚠️ Aucune donnée récupérée pour le moment. Vérifiez vos soumissions sur KoboToolbox.")
else:
    # Détection sécurisée des colonnes Hub et Zone de Santé
    hub_col = next((col for col in df.columns if 'hub' in col.lower() or 'anten' in col.lower()), None)
    zs_col = next((col for col in df.columns if 'zone' in col.lower() or 'zs' in col.lower()), None)

    # --- BARRE LATÉRALE DE FILTRAGE ---
    st.sidebar.header("🔍 Filtres & Paramètres")
    
    df_filtered = df.copy()
    selected_hub = "Tous"
    
    if hub_col:
        hubs = list(df[hub_col].dropna().unique())
        selected_hub = st.sidebar.selectbox("Filtrer par Hub", ["Tous"] + hubs)
        if selected_hub != "Tous":
            df_filtered = df_filtered[df_filtered[hub_col] == selected_hub]

    if zs_col:
        zs_list = list(df_filtered[zs_col].dropna().unique())
        selected_zs = st.sidebar.selectbox("Filtrer par Zone de Santé", ["Toutes"] + zs_list)
        if selected_zs != "Toutes":
            df_filtered = df_filtered[df_filtered[zs_col] == selected_zs]

    # --- EN-TÊTE DE SYNTHÈSE ---
    st.markdown("### 📌 Synthèse Générale")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Rapports</div><div class="metric-value">{len(df_filtered)}</div></div>', unsafe_allow_html=True)
    with c2:
        hubs_count = df_filtered[hub_col].nunique() if hub_col and hub_col in df_filtered.columns else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">Hubs Actifs</div><div class="metric-value">{hubs_count}</div></div>', unsafe_allow_html=True)
    with c3:
        zs_count = df_filtered[zs_col].nunique() if zs_col and zs_col in df_filtered.columns else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">Zones de Santé</div><div class="metric-value">{zs_count}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Connexion API</div><div class="metric-value" style="color: #10b981;">🟢 Active</div></div>', unsafe_allow_html=True)

    # --- CALCUL DES INDICATEURS CLÉS ---
    indicators_mapping = [
        ("Proportion des PPL infectés parmi les cas confirmés d'Ebola", "planifie_ppl", "realise_ppl"),
        ("Proportion d'individus (non PPL) ayant contracté la MVE dans les ESS", "planifie_non_ppl", "realise_non_ppl"),
        ("Proportion d'ESS ayant un score > 80%", "planifie_ess", "realise_ess"),
        ("Proportion d'ESS ayant reçu un Kit PCI", "planifie_kit", "realise_kit"),
        ("Proportion d'ESS unidirectionnel disposant d'un triage", "planifie_triage", "realise_triage"),
        ("Proportion d'ESS ayant accueilli un cas confirmé décontaminé en 48h", "planifie_decont", "realise_decont"),
        ("Pourcentage du personnel de santé cible formé en PCI", "planifie_forme", "realise_forme")
    ]

    table_data = []
    for label, key_p, key_r in indicators_mapping:
        matched_p = next((c for c in df_filtered.columns if key_p in c.lower() or key_p.split('_')[1] in c.lower()), None)
        matched_r = next((c for c in df_filtered.columns if key_r in c.lower() or key_r.split('_')[1] in c.lower()), None)
        
        val_p = float(df_filtered[matched_p].sum()) if matched_p and pd.api.types.is_numeric_dtype(df_filtered[matched_p]) else 0.0
        val_r = float(df_filtered[matched_r].sum()) if matched_r and pd.api.types.is_numeric_dtype(df_filtered[matched_r]) else 0.0
        
        taux = round((val_r / val_p) * 100, 1) if val_p > 0 else 0.0
        
        table_data.append({
            "Indicateur Clé PCI / WASH": label,
            "Cible / Planifié": val_p,
            "Réalisé": val_r,
            "Taux de Réalisation (%)": f"{taux}%"
        })

    df_indicators = pd.DataFrame(table_data)
    
    st.markdown("---")
    st.markdown(f"### 📋 Tableau des Indicateurs Clés ({'Global - Province' if selected_hub == 'Tous' else selected_hub})")
    st.dataframe(df_indicators, use_container_width=True, hide_index=True)

    # --- GRAPHIQUES ANALYTIQUES ---
    st.markdown("---")
    st.markdown("### 📈 Visualisations Graphiques")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if hub_col:
            fig_hub = px.pie(df, names=hub_col, title="Répartition proportionnelle par Hub", hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig_hub, use_container_width=True)
    with col_g2:
        if zs_col:
            fig_zs = px.bar(df_filtered, x=zs_col, color=hub_col if hub_col else None, title="Volume de soumissions par Zone de Santé", color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_zs, use_container_width=True)

    # --- DONNÉES BRUTES ---
    with st.expander("🔍 Afficher les soumissions Kobo brutes détaillées"):
        st.dataframe(df_filtered)
