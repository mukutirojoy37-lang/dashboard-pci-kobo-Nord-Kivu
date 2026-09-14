import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="Dashboard PCI/WASH - Nord-Kivu", layout="wide", initial_sidebar_state="expanded")

# Design CSS professionnel et épuré
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
    # Nettoyage et conversion numérique automatique
    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.notnull().sum() > 0:
                df[col] = converted
        except Exception:
            pass

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

    # --- CALCUL DES INDICATEURS CLÉS (Avec des libellés clairs et courts pour l'axe X) ---
    indicators_mapping = [
        ("PPL Infecté à la MVE", "Proportion des PPL infectés (Ebola)", "ppl"),
        ("Non PPL MVE", "Proportion non PPL (MVE dans ESS)", "non_ppl"),
        ("Score ESS > 80%", "Proportion ESS score > 80%", "score"),
        ("Dotation en Kit PCI", "Proportion ESS avec Kit PCI", "kit"),
        ("Triage fonctionnel", "Proportion ESS triage unidirectionnel", "triage"),
        ("ESS Décontaminés dans le 48h", "Cas confirmés décontaminés en 48h", "decont"),
        ("PPL Formé", "Personnel de santé formé en PCI", "forme")
    ]

    table_data = []
    for short_label, full_label, keyword in indicators_mapping:
        matching_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if keyword in c.lower()]
        
        val_p, val_r = 0.0, 0.0
        if len(matching_cols) >= 2:
            val_p = float(df_filtered[matching_cols[0]].sum())
            val_r = float(df_filtered[matching_cols[1]].sum())
        elif len(matching_cols) == 1:
            val_r = float(df_filtered[matching_cols[0]].sum())

        taux = round((val_r / val_p) * 100, 1) if val_p > 0 else 0.0
        
        table_data.append({
            "Indicateur Clé PCI / WASH": full_label,
            "Label Court": short_label,
            "Cible / Planifié": val_p,
            "Réalisé": val_r,
            "Taux (%)": taux
        })

    df_indicators = pd.DataFrame(table_data)

    # --- NAVIGATION PAR ONGLETS ---
    tab1, tab2, tab3 = st.tabs(["📋 Tableaux & Synthèse", "📈 Graphiques Avancés", "🔍 Données Brutes"])

    with tab1:
        st.markdown(f"### 📋 Tableau Détaillé des Indicateurs ({'Global' if selected_hub == 'Tous' else selected_hub})")
        df_display = df_indicators.copy()
        df_display["Taux de Réalisation (%)"] = df_display["Taux (%)"].astype(str) + "%"
        st.dataframe(df_display[["Indicateur Clé PCI / WASH", "Cible / Planifié", "Réalisé", "Taux de Réalisation (%)"]], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 📊 Synthèse Globale des Taux de Réalisation (%)")
        
        # Histogramme avec axe X parfaitement droit et lisible (tickangle=0)
        fig_hist = px.bar(
            df_indicators, 
            x="Label Court", 
            y="Taux (%)", 
            text="Taux (%)",
            color="Taux (%)",
            color_continuous_scale="Blues",
            title="Taux de Réalisation Global par Indicateur Clé (%)"
        )
        fig_hist.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_hist.update_layout(
            xaxis_tickangle=0,  # Texte bien droit et horizontal
            xaxis_title="Indicateurs Clés PCI / WASH",
            yaxis_title="Pourcentage (%)",
            yaxis_range=[0, max(110, df_indicators["Taux (%)"].max() + 15)]
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if hub_col:
                fig_hub = px.pie(df, names=hub_col, title="Répartition proportionnelle par Hub", hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig_hub, use_container_width=True)
        with col_g2:
            if zs_col:
                fig_zs = px.bar(df_filtered, x=zs_col, color=hub_col if hub_col else None, title="Volume de soumissions par Zone de Santé", color_discrete_sequence=px.colors.qualitative.Prism)
                st.plotly_chart(fig_zs, use_container_width=True)

    with tab3:
        st.markdown("### 🔍 Base de Données Kobo Détaillée")
        st.dataframe(df_filtered, use_container_width=True)
