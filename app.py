import os
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard PCI/WASH - Nord-Kivu", layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Identité visuelle : rapport institutionnel, sobre, lecture par seuils
# ---------------------------------------------------------------------------
INK = "#14212B"
MUTED = "#5B6773"
PAPER = "#F6F7F9"
SURFACE = "#FFFFFF"
LINE = "#E1E5EA"
BLUE = "#1F4FD8"
RED = "#C0392B"
AMBER = "#D08A0E"
GREEN = "#2F855A"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@500;600&display=swap');

    html, body, [class*="css"], .stApp {{ font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif; color: {INK}; }}
    .stApp {{ background: {PAPER}; }}
    .block-container {{ max-width: 1240px; padding-top: 1.5rem; padding-bottom: 4rem; }}
    #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
    section[data-testid="stSidebar"] {{ display: none; }}

    /* En-tête */
    .kicker {{ font-size: 14px; font-weight: 500; color: {BLUE}; margin-bottom: 10px; }}
    .page-title {{ font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 600; font-size: 40px;
                   line-height: 1.15; letter-spacing: -0.01em; margin: 0 0 14px 0; color: {INK}; }}
    .lead {{ font-size: 16px; line-height: 1.6; color: {MUTED}; max-width: 70ch; margin-bottom: 24px; }}

    /* Bandeau de chiffres */
    .kpi-strip {{ display: flex; flex-wrap: wrap; background: {SURFACE}; border: 1px solid {LINE};
                  border-radius: 8px; margin-bottom: 18px; }}
    .kpi {{ flex: 1 1 150px; padding: 16px 20px; border-right: 1px solid {LINE}; }}
    .kpi:last-child {{ border-right: none; }}
    .kpi-label {{ font-size: 13px; color: {MUTED}; margin-bottom: 4px; }}
    .kpi-value {{ font-size: 26px; font-weight: 600; color: {INK}; line-height: 1.2; }}
    .kpi-value.small {{ font-size: 16px; padding-top: 6px; }}
    .kpi-value.ok {{ color: {GREEN}; font-size: 18px; padding-top: 4px; }}

    /* Barre de filtres */
    div[data-testid="stVerticalBlockBorderWrapper"] {{ background: {SURFACE}; border-color: {LINE} !important; border-radius: 8px; }}
    label, .stSelectbox label, .stDateInput label, .stRadio label p {{ font-size: 13px !important; color: {MUTED} !important; font-weight: 500 !important; }}
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{ border-radius: 6px; border-color: {LINE}; background: {PAPER}; }}
    .stButton > button {{ border-radius: 6px; border: 1px solid {LINE}; background: {SURFACE}; color: {INK}; font-weight: 500; }}
    .stButton > button:hover {{ border-color: {BLUE}; color: {BLUE}; }}

    /* Navigation par onglets */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; margin-top: 8px; }}
    .stTabs [data-baseweb="tab"] {{ padding: 10px 16px; font-weight: 500; color: {MUTED}; }}
    .stTabs [aria-selected="true"] {{ color: {BLUE}; font-weight: 600; }}
    .stTabs [data-baseweb="tab-highlight"] {{ background-color: {BLUE}; height: 3px; }}

    /* Sections */
    h3 {{ font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 600; font-size: 22px; letter-spacing: -0.005em; margin-top: 1.4rem; }}
    .stMarkdown p {{ color: {MUTED}; }}
    hr {{ border: none; border-top: 1px solid {LINE}; margin: 2rem 0; }}

    /* Légende des seuils */
    .legend {{ display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; color: {MUTED}; margin: 4px 0 10px 0; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: baseline; }}

    div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] {{
        background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; padding: 4px;
    }}
    button:focus-visible, [role="tab"]:focus-visible, input:focus-visible {{ outline: 2px solid {BLUE}; outline-offset: 2px; }}
    .site-footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid {LINE}; font-size: 13px; color: {MUTED}; }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig):
    fig.update_layout(
        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=13),
        title=dict(font=dict(size=15, color=INK), x=0.01),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        margin=dict(l=20, r=30, t=56, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)", title_text=""),
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="#EEF0F3", zeroline=False, tickfont=dict(color=MUTED))
    return fig


def niveau(taux):
    if taux >= 80:
        return "Satisfaisant (≥ 80 %)"
    if taux >= 50:
        return "Partiel (50–80 %)"
    return "Insuffisant (< 50 %)"


LEVEL_COLORS = {
    "Insuffisant (< 50 %)": RED,
    "Partiel (50–80 %)": AMBER,
    "Satisfaisant (≥ 80 %)": GREEN,
}

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="kicker">Nord/Kivu — Riposte PCI/WASH</div>
<h1 class="page-title">📊 Nord/Kivu — Tableau de Bord PCI/WASH — Suivi Opérationnel</h1>
<p class="lead">Pilotage en temps réel des indicateurs clés par Hub, par Zone de Santé et par Période.</p>
""", unsafe_allow_html=True)

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
            return pd.DataFrame(response.json().get('results', []))
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


with st.spinner("Chargement des données en direct..."):
    df = fetch_kobo_data()

if df.empty:
    st.warning("⚠️ Aucune donnée récupérée pour le moment. Vérifiez vos soumissions sur KoboToolbox.")
else:
    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.notnull().sum() > 0:
                df[col] = converted
        except Exception:
            pass

    hub_col = next((col for col in df.columns if 'hub' in col.lower() or 'anten' in col.lower()), None)
    zs_col = next((col for col in df.columns if 'zone' in col.lower() or 'zs' in col.lower()), None)
    date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower() or '_submission_time' in col.lower()), None)

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # -----------------------------------------------------------------------
    # BARRE DE FILTRES (en haut de page)
    # -----------------------------------------------------------------------
    df_filtered = df.copy()
    selected_hub = "Tous"

    def reset_filters():
        for k in ("f_date", "f_quick", "f_hub", "f_zs"):
            st.session_state.pop(k, None)

    with st.container(border=True):
        st.markdown("**🔍 Filtres & Paramètres**")
        f1, f2, f3, f4, f5 = st.columns([2.2, 1.8, 1.6, 1.6, 0.9])

        with f1:
            if date_col and df[date_col].notnull().sum() > 0:
                min_date = df[date_col].min().date()
                max_date = df[date_col].max().date()
                date_range = st.date_input("📅 Période d'Évaluation — sélectionnez l'intervalle",
                                           value=(min_date, max_date), min_value=min_date,
                                           max_value=max_date, key="f_date")
            else:
                date_range = None
        with f2:
            quick = st.radio("Raccourcis", ["Tout", "7 j", "14 j", "30 j"], horizontal=True, key="f_quick")

        # Application de la période
        if date_col and date_range is not None:
            if quick != "Tout":
                days = int(quick.split()[0])
                start_date, end_date = max_date - timedelta(days=days - 1), max_date
                df_filtered = df_filtered[(df_filtered[date_col].dt.date >= start_date) &
                                          (df_filtered[date_col].dt.date <= end_date)]
            elif len(date_range) == 2:
                start_date, end_date = date_range
                df_filtered = df_filtered[(df_filtered[date_col].dt.date >= start_date) &
                                          (df_filtered[date_col].dt.date <= end_date)]

        with f3:
            if hub_col:
                hubs = list(df_filtered[hub_col].dropna().unique())
                selected_hub = st.selectbox("Filtrer par Hub", ["Tous"] + hubs, key="f_hub")
                if selected_hub != "Tous":
                    df_filtered = df_filtered[df_filtered[hub_col] == selected_hub]
        with f4:
            if zs_col:
                zs_list = list(df_filtered[zs_col].dropna().unique())
                selected_zs = st.selectbox("Filtrer par Zone de Santé", ["Toutes"] + zs_list, key="f_zs")
                if selected_zs != "Toutes":
                    df_filtered = df_filtered[df_filtered[zs_col] == selected_zs]
        with f5:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            st.button("Réinitialiser", on_click=reset_filters)

    # -----------------------------------------------------------------------
    # SYNTHÈSE : bandeau de chiffres
    # -----------------------------------------------------------------------
    hubs_count = df_filtered[hub_col].nunique() if hub_col and hub_col in df_filtered.columns else 0
    zs_count = df_filtered[zs_col].nunique() if zs_col and zs_col in df_filtered.columns else 0

    if date_col and df_filtered[date_col].notnull().sum() > 0:
        periode = f"{df_filtered[date_col].min():%d/%m/%Y} → {df_filtered[date_col].max():%d/%m/%Y}"
    else:
        periode = "—"

    st.markdown("### 📌 Synthèse Générale")
    st.markdown(f"""
    <div class="kpi-strip">
        <div class="kpi"><div class="kpi-label">Total Rapports</div><div class="kpi-value">{len(df_filtered)}</div></div>
        <div class="kpi"><div class="kpi-label">Hubs Actifs</div><div class="kpi-value">{hubs_count}</div></div>
        <div class="kpi"><div class="kpi-label">Zones de Santé</div><div class="kpi-value">{zs_count}</div></div>
        <div class="kpi"><div class="kpi-label">Période</div><div class="kpi-value small">{periode}</div></div>
        <div class="kpi"><div class="kpi-label">Connexion API</div><div class="kpi-value ok">🟢 Active</div></div>
        <div class="kpi"><div class="kpi-label">Généré le</div><div class="kpi-value small">{datetime.now():%d/%m/%Y %H:%M}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # CALCUL DES INDICATEURS (inchangé)
    # -----------------------------------------------------------------------
    indicators_mapping = [
        ("Nbre PPL Infecté (Ebola)", "ppl", False),
        ("Nbre non PPL Infecté (MVE)", "non_ppl", False),
        ("Score ESS > 80%", "score", True),
        ("Dotation en Kit PCI", "kit", True),
        ("Triage fonctionnel", "triage", True),
        ("ESS Décontaminés (48h)", "decont", True),
        ("PPL Formé", "forme", True)
    ]

    table_data, chart_data = [], []

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

    # -----------------------------------------------------------------------
    # ONGLETS
    # -----------------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["📋 Tableaux & Synthèse", "📈 Graphiques Avancés", "🔍 Données Brutes"])

    with tab1:
        st.markdown(f"### 📋 Tableau Détaillé des Indicateurs ({'Global' if selected_hub == 'Tous' else selected_hub})")
        st.dataframe(df_indicators, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 📊 Synthèse des Taux de Réalisation (%)")
        st.markdown(
            f'<div class="legend">'
            f'<span><span class="dot" style="background:{RED}"></span>Insuffisant (&lt; 50 %)</span>'
            f'<span><span class="dot" style="background:{AMBER}"></span>Partiel (50–80 %)</span>'
            f'<span><span class="dot" style="background:{GREEN}"></span>Satisfaisant (≥ 80 %)</span></div>',
            unsafe_allow_html=True)

        df_pct = df_chart[df_chart["Type"] == "Pourcentage"].copy()
        df_pct["Niveau"] = df_pct["Valeur"].apply(niveau)

        fig_hist_pct = px.bar(
            df_pct, x="Indicateur", y="Valeur", text="Valeur",
            color="Niveau", color_discrete_map=LEVEL_COLORS,
            category_orders={"Niveau": list(LEVEL_COLORS.keys())},
            title="Taux de Réalisation Global par Indicateur (%)"
        )
        fig_hist_pct.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0, cliponaxis=False)
        fig_hist_pct.add_hline(y=50, line_dash="dot", line_color="#9AA5B1", line_width=1)
        fig_hist_pct.add_hline(y=80, line_dash="dot", line_color="#9AA5B1", line_width=1)
        fig_hist_pct.update_layout(
            xaxis_tickangle=0,
            xaxis_title="Indicateurs Logistiques PCI / WASH",
            yaxis_title="Pourcentage (%)",
            yaxis_range=[0, max(110, df_pct["Valeur"].max() + 15)],
            bargap=0.4, showlegend=False
        )
        st.plotly_chart(style_fig(fig_hist_pct), use_container_width=True)

        st.markdown("---")

        st.markdown("### 🦠 Dénombrement des Cas Constatés (PPL & Non-PPL Infectés)")
        df_cas = df_chart[df_chart["Type"] == "Cas Constatés"]

        fig_hist_cas = px.bar(
            df_cas, x="Indicateur", y="Valeur", text="Valeur",
            color="Indicateur", color_discrete_sequence=[RED, AMBER],
            title="Nombre Total de Cas Constatés sur la Période"
        )
        fig_hist_cas.update_traces(texttemplate='%{text}', textposition='outside', marker_line_width=0, cliponaxis=False)
        fig_hist_cas.update_layout(
            xaxis_tickangle=0,
            xaxis_title="Indicateurs Épidémiologiques",
            yaxis_title="Nombre de Cas",
            yaxis_range=[0, max(10, df_cas["Valeur"].max() + 5)],
            bargap=0.55, showlegend=False
        )
        st.plotly_chart(style_fig(fig_hist_cas), use_container_width=True)

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if hub_col:
                fig_hub = px.pie(df_filtered, names=hub_col, title="Répartition proportionnelle par Hub", hole=0.58,
                                 color_discrete_sequence=[BLUE, "#5B82E6", "#9DB5F0", "#CBD7F8", "#5B6773", "#A9B3BD"])
                fig_hub.update_traces(marker=dict(line=dict(color=SURFACE, width=2)))
                st.plotly_chart(style_fig(fig_hub), use_container_width=True)
        with col_g2:
            if zs_col:
                fig_zs = px.bar(df_filtered, x=zs_col, color=hub_col if hub_col else None,
                                title="Volume de soumissions par Zone de Santé",
                                color_discrete_sequence=[BLUE, "#5B82E6", "#9DB5F0", "#5B6773", "#A9B3BD", "#CBD7F8"])
                st.plotly_chart(style_fig(fig_zs), use_container_width=True)

    with tab3:
        st.markdown("### 🔍 Base de Données Kobo Détaillée (Filtrée)")
        st.dataframe(df_filtered, use_container_width=True)

    st.markdown('<div class="site-footer">Nord/Kivu — Riposte PCI/WASH 2026</div>', unsafe_allow_html=True)
