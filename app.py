import os
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Dashboard PCI/WASH - Nord-Kivu", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Identité visuelle
# ---------------------------------------------------------------------------
INK = "#1B2B30"        # texte principal
MUTED = "#5E6E72"      # texte secondaire
PAPER = "#F2F5F4"      # fond de page
SURFACE = "#FFFFFF"    # cartes
LINE = "#D8E0DE"       # filets
TEAL = "#0E5A63"       # couleur d'action / réalisation
RED = "#B5342B"        # cas PPL
AMBER = "#C47A12"      # cas non PPL
GREEN = "#2E7D5B"      # statut actif

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'Public Sans', -apple-system, 'Segoe UI', sans-serif;
            color: {INK};
        }}
        .stApp, .main {{ background-color: {PAPER}; }}
        .block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }}
        #MainMenu, footer {{ visibility: hidden; }}

        /* Titres */
        h1 {{ font-weight: 700; letter-spacing: -0.02em; color: {INK}; padding-bottom: 0.2rem; }}
        h3 {{ font-weight: 600; letter-spacing: -0.01em; color: {INK}; margin-top: 0.5rem; }}
        .stMarkdown p {{ color: {MUTED}; }}
        hr {{ border: none; border-top: 1px solid {LINE}; margin: 1.6rem 0; }}

        /* Cartes de synthèse */
        .metric-card {{
            background-color: {SURFACE};
            border: 1px solid {LINE};
            border-left: 4px solid {TEAL};
            padding: 16px 18px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .metric-title {{ font-size: 13px; font-weight: 500; color: {MUTED}; }}
        .metric-value {{ font-size: 30px; font-weight: 700; color: {INK}; margin-top: 4px; line-height: 1.1; }}
        .metric-status {{ color: {GREEN}; font-size: 20px; font-weight: 600; margin-top: 10px; }}

        /* Barre latérale */
        section[data-testid="stSidebar"] {{
            background-color: #E6ECEA;
            border-right: 1px solid {LINE};
        }}
        section[data-testid="stSidebar"] h2 {{ font-size: 18px; font-weight: 700; }}
        section[data-testid="stSidebar"] h3 {{ font-size: 15px; font-weight: 600; }}

        /* Onglets */
        .stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {LINE}; }}
        .stTabs [data-baseweb="tab"] {{
            font-weight: 500; color: {MUTED};
            padding: 10px 18px; border-radius: 6px 6px 0 0;
        }}
        .stTabs [aria-selected="true"] {{ color: {TEAL}; font-weight: 600; }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: {TEAL}; height: 3px; }}

        /* Tableaux et graphiques dans un conteneur propre */
        div[data-testid="stDataFrame"] {{
            border: 1px solid {LINE}; border-radius: 6px; overflow: hidden; background: {SURFACE};
        }}
        div[data-testid="stPlotlyChart"] {{
            background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; padding: 8px;
        }}

        /* Focus clavier visible */
        button:focus-visible, [role="tab"]:focus-visible, input:focus-visible {{
            outline: 2px solid {TEAL}; outline-offset: 2px;
        }}
    </style>
""", unsafe_allow_html=True)


def style_fig(fig):
    """Applique un style homogène à tous les graphiques."""
    fig.update_layout(
        font=dict(family="Public Sans, sans-serif", color=INK, size=13),
        title=dict(font=dict(size=16, color=INK), x=0.01),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        margin=dict(l=20, r=20, t=60, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#E9EEEC", zeroline=False, tickfont=dict(color=MUTED))
    return fig


def metric_card(title, value_html, value_class="metric-value"):
    return (f'<div class="metric-card"><div class="metric-title">{title}</div>'
            f'<div class="{value_class}">{value_html}</div></div>')


st.title("📊 Nord/Kivu — Tableau de Bord PCI/WASH — Suivi Opérationnel")
st.markdown("Pilotage en temps réel des indicateurs clés par Hub, par Zone de Santé et par Période.")

# Paramètres API Kobo (préférez st.secrets ou une variable d'environnement)
API_TOKEN = st.secrets.get("KOBO_TOKEN", os.environ.get("KOBO_TOKEN", "d64887bad92383b600f2f520c44b0bc7c778c595"))
ASSET_ID = "aoJjBQ3vHyR4aPQRhSoJSR"
API_URL = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_ID}/data.json"

@st.cache_data(ttl=300)
def fetch_kobo_data():
    headers = {"Authorization": f"Token {API_TOKEN}"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
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

    # Détection automatique des colonnes clés (Hub, Zone de Santé, Date)
    hub_col = next((col for col in df.columns if 'hub' in col.lower() or 'anten' in col.lower()), None)
    zs_col = next((col for col in df.columns if 'zone' in col.lower() or 'zs' in col.lower()), None)
    date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or '_submission_time' in col.lower()), None)

    # Conversion de la colonne de date en datetime si elle existe
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # --- BARRE LATÉRALE DE FILTRAGE ---
    st.sidebar.header("🔍 Filtres & Paramètres")

    df_filtered = df.copy()

    # 1. Filtre par Période (Date Range)
    if date_col and df[date_col].notnull().sum() > 0:
        min_date = df[date_col].min().date()
        max_date = df[date_col].max().date()

        st.sidebar.subheader("📅 Période d'Évaluation")
        date_range = st.sidebar.date_input(
            "Sélectionnez l'intervalle",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df_filtered[
                (df_filtered[date_col].dt.date >= start_date) &
                (df_filtered[date_col].dt.date <= end_date)
            ]

    # 2. Filtre par Hub
    selected_hub = "Tous"
    if hub_col:
        hubs = list(df_filtered[hub_col].dropna().unique())
        selected_hub = st.sidebar.selectbox("Filtrer par Hub", ["Tous"] + hubs)
        if selected_hub != "Tous":
            df_filtered = df_filtered[df_filtered[hub_col] == selected_hub]

    # 3. Filtre par Zone de Santé
    if zs_col:
        zs_list = list(df_filtered[zs_col].dropna().unique())
        selected_zs = st.sidebar.selectbox("Filtrer par Zone de Santé", ["Toutes"] + zs_list)
        if selected_zs != "Toutes":
            df_filtered = df_filtered[df_filtered[zs_col] == selected_zs]

    # --- EN-TÊTE DE SYNTHÈSE ---
    st.markdown("### 📌 Synthèse Générale")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Total Rapports", len(df_filtered)), unsafe_allow_html=True)
    with c2:
        hubs_count = df_filtered[hub_col].nunique() if hub_col and hub_col in df_filtered.columns else 0
        st.markdown(metric_card("Hubs Actifs", hubs_count), unsafe_allow_html=True)
    with c3:
        zs_count = df_filtered[zs_col].nunique() if zs_col and zs_col in df_filtered.columns else 0
        st.markdown(metric_card("Zones de Santé", zs_count), unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Connexion API", "🟢 Active", "metric-status"), unsafe_allow_html=True)

    # --- CALCUL DES INDICATEURS CLÉS ---
    indicators_mapping = [
        ("Nbre PPL Infecté (Ebola)", "ppl", False),
        ("Nbre non PPL Infecté (MVE)", "non_ppl", False),
        ("Score ESS > 80%", "score", True),
        ("Dotation en Kit PCI", "kit", True),
        ("Triage fonctionnel", "triage", True),
        ("ESS Décontaminés (48h)", "decont", True),
        ("PPL Formé", "forme", True)
    ]

    table_data = []
    chart_data = []

    for short_label, keyword, has_target in indicators_mapping:
        matching_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if keyword in c.lower()]

        val_p, val_r = 0.0, 0.0
        if has_target:
            if len(matching_cols) >= 2:
                val_p = float(df_filtered[matching_cols[0]].sum())
                val_r = float(df_filtered[matching_cols[1]].sum())
            elif len(matching_cols) == 1:
                val_r = float(df_filtered[matching_cols[0]].sum())

            taux = round((val_r / val_p) * 100, 1) if val_p > 0 else 0.0

            table_data.append({
                "Indicateur Clé PCI / WASH": short_label,
                "Cible / Planifié": int(val_p),
                "Réalisé": int(val_r),
                "Taux de Réalisation (%)": f"{taux}%"
            })
            chart_data.append({"Indicateur": short_label, "Valeur": taux, "Type": "Pourcentage"})
        else:
            if len(matching_cols) >= 2:
                val_r = float(df_filtered[matching_cols[1]].sum())
            elif len(matching_cols) == 1:
                val_r = float(df_filtered[matching_cols[0]].sum())

            table_data.append({
                "Indicateur Clé PCI / WASH": short_label,
                "Cible / Planifié": "—",
                "Réalisé": int(val_r),
                "Taux de Réalisation (%)": "N/A (Cas constatés)"
            })
            chart_data.append({"Indicateur": short_label, "Valeur": int(val_r), "Type": "Cas Constatés"})

    df_indicators = pd.DataFrame(table_data)
    df_chart = pd.DataFrame(chart_data)

    # --- NAVIGATION PAR ONGLETS ---
    tab1, tab2, tab3 = st.tabs(["📋 Tableaux & Synthèse", "📈 Graphiques Avancés", "🔍 Données Brutes"])

    with tab1:
        st.markdown(f"### 📋 Tableau Détaillé des Indicateurs ({'Global' if selected_hub == 'Tous' else selected_hub})")
        st.dataframe(df_indicators, use_container_width=True, hide_index=True)

    with tab2:
        # 1. Graphique des Taux (%)
        st.markdown("### 📊 Synthèse des Taux de Réalisation (%)")
        df_pct = df_chart[df_chart["Type"] == "Pourcentage"]

        fig_hist_pct = px.bar(
            df_pct,
            x="Indicateur",
            y="Valeur",
            text="Valeur",
            color_discrete_sequence=[TEAL],
            title="Taux de Réalisation Global par Indicateur (%)"
        )
        fig_hist_pct.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0, cliponaxis=False)
        fig_hist_pct.update_layout(
            xaxis_tickangle=0,
            xaxis_title="Indicateurs Logistiques PCI / WASH",
            yaxis_title="Pourcentage (%)",
            yaxis_range=[0, max(110, df_pct["Valeur"].max() + 15)],
            bargap=0.35,
            showlegend=False
        )
        st.plotly_chart(style_fig(fig_hist_pct), use_container_width=True)

        st.markdown("---")

        # 2. Graphique séparé pour les Cas Constatés
        st.markdown("### 🦠 Dénombrement des Cas Constatés (PPL & Non-PPL Infectés)")
        df_cas = df_chart[df_chart["Type"] == "Cas Constatés"]

        fig_hist_cas = px.bar(
            df_cas,
            x="Indicateur",
            y="Valeur",
            text="Valeur",
            color="Indicateur",
            color_discrete_sequence=[RED, AMBER],
            title="Nombre Total de Cas Constatés sur la Période"
        )
        fig_hist_cas.update_traces(texttemplate='%{text}', textposition='outside', marker_line_width=0, cliponaxis=False)
        fig_hist_cas.update_layout(
            xaxis_tickangle=0,
            xaxis_title="Indicateurs Épidémiologiques",
            yaxis_title="Nombre de Cas",
            yaxis_range=[0, max(10, df_cas["Valeur"].max() + 5)],
            bargap=0.5,
            showlegend=False
        )
        st.plotly_chart(style_fig(fig_hist_cas), use_container_width=True)

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if hub_col:
                fig_hub = px.pie(df_filtered, names=hub_col, title="Répartition proportionnelle par Hub", hole=0.55,
                                 color_discrete_sequence=[TEAL, "#3D8B93", "#7FB5BA", "#B5D5D8", "#5E6E72", "#98A8AC"])
                fig_hub.update_traces(marker=dict(line=dict(color=SURFACE, width=2)))
                st.plotly_chart(style_fig(fig_hub), use_container_width=True)
        with col_g2:
            if zs_col:
                fig_zs = px.bar(df_filtered, x=zs_col, color=hub_col if hub_col else None, title="Volume de soumissions par Zone de Santé",
                                color_discrete_sequence=[TEAL, AMBER, "#7FB5BA", RED, "#5E6E72", "#2E7D5B"])
                st.plotly_chart(style_fig(fig_zs), use_container_width=True)

    with tab3:
        st.markdown("### 🔍 Base de Données Kobo Détaillée (Filtrée)")
        st.dataframe(df_filtered, use_container_width=True)
