import os
from datetime import date
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from metrics import normalize_activities, daily_summary

# ----------------- Config page -----------------
st.set_page_config(page_title="Strav'App", layout="wide")

# ----------------- State -----------------
if "sidebar_hidden" not in st.session_state:
    st.session_state.sidebar_hidden = False
if "menu" not in st.session_state:
    st.session_state.menu = "Accueil"

# ----------------- CSS (bandeau + hide sidebar) -----------------
_hide_sidebar_rules = """
/* masque complètement la sidebar */
div[data-testid="stSidebar"] { 
  display: none !important;
}
/* supprime la flèche toggle native */
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
"""

_banner_css = """
<style>
%s
.app-banner {
  width: 100%%;
  padding: 16px 18px;
  border-radius: 12px;
  background: linear-gradient(90deg, #ff6b6b, #f7b267);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  margin-bottom: 10px;
}
.app-banner h1 {
  font-size: 1.25rem;
  font-weight: 800;
  margin: 0;
}
.app-banner .subtitle {
  opacity: 0.95;
  font-size: 0.95rem;
}
</style>
""" % (_hide_sidebar_rules if st.session_state.sidebar_hidden else "")

st.markdown(_banner_css, unsafe_allow_html=True)

# ----------------- Bandeau -----------------
left, right = st.columns([1, 0.22], gap="small")
with left:
    st.markdown(
        f"""
        <div class="app-banner">
          <div>
            <h1>Strav'App — Accueil</h1>
            <div class="subtitle">Vue {date.today().year} • Statistiques & activités</div>
          </div>
          <div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    if st.button(
        "➕ Afficher la barre latérale" if st.session_state.sidebar_hidden else "➖ Réduire la barre latérale",
        use_container_width=True,
    ):
        st.session_state.sidebar_hidden = not st.session_state.sidebar_hidden
        st.rerun()

# ----------------- Sidebar: Menu -----------------
if not st.session_state.sidebar_hidden:
    st.sidebar.header("Navigation")
    st.session_state.menu = st.sidebar.radio(
        "Menu",
        ["Accueil", "Statistiques", "Activités", "Réglages"],
        index=["Accueil", "Statistiques", "Activités", "Réglages"].index(st.session_state.menu),
    )

# ----------------- Données -----------------
DATA_PARQUET = os.path.join("data", "activities.parquet")
DATA_SAMPLE_PARQUET = os.path.join("data", "sample_activities.parquet")
DATA_SAMPLE_CSV = os.path.join("data", "sample_activities.csv")

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_PARQUET):
        return pd.read_parquet(DATA_PARQUET)
    if os.path.exists(DATA_SAMPLE_PARQUET):
        return pd.read_parquet(DATA_SAMPLE_PARQUET)
    if os.path.exists(DATA_SAMPLE_CSV):
        return pd.read_csv(DATA_SAMPLE_CSV)
    return pd.DataFrame()

def ui_filters(df: pd.DataFrame, container) -> tuple[pd.DataFrame, int]:
    with container:
        with st.expander("🔎 Filtres", expanded=True):
            years = sorted(pd.to_datetime(df["start_date_local"]).dt.year.unique())
            default_year = date.today().year if date.today().year in years else (years[-1] if years else date.today().year)
            year = st.selectbox(
                "Année",
                options=years if len(years) else [default_year],
                index=(years.index(default_year) if default_year in years else 0),
            )
            df = df[pd.to_datetime(df["start_date_local"]).dt.year == year]

            sports = sorted(df.get("sport_type", df.get("type", pd.Series([]))).dropna().unique().tolist())
            sport = st.multiselect("Sport", options=sports, default=sports)
            if sport:
                col = "sport_type" if "sport_type" in df.columns else "type"
                df = df[df[col].isin(sport)]

            # Distance (km)
            if "distance" in df.columns:
                df = df.copy()
                df["distance_km"] = df["distance"] / 1000.0
                min_km = float(df["distance_km"].min()) if not df.empty else 0.0
                max_km = float(df["distance_km"].max()) if not df.empty else 0.0
                km_range = st.slider("Distance (km)", min_km, max_km, (min_km, max_km))
                df = df[(df["distance_km"] >= km_range[0]) & (df["distance_km"] <= km_range[1])]

            # Recherche texte dans le nom
            q = st.text_input("Recherche (nom contient)", "")
            if q:
                df = df[df["name"].str.contains(q, case=False, na=False)]

    # Tri récence
    df = df.sort_values("start_date_local", ascending=False)
    return df, year

def yearly_stats(df_year: pd.DataFrame, year: int):
    if df_year.empty:
        st.info("Aucune activité pour cette année.")
        return
    df_norm = normalize_activities(df_year)
    days = daily_summary(df_norm)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distance totale", f"{df_norm['distance_km'].sum():,.0f} km")
    c2.metric("Temps en mvmt", f"{df_norm['moving_hours'].sum():,.1f} h")
    c3.metric("Sorties", f"{len(df_norm):,d}")
    if "total_elevation_gain" in df_norm.columns:
        c4.metric("D+ total", f"{df_norm['total_elevation_gain'].sum():,.0f} m")
    else:
        c4.metric("Jours actifs", f"{len(days):,d}")
    st.caption(
        f"Année affichée : {year} — de {pd.to_datetime(df_norm['start_date_local']).min().date()} "
        f"à {pd.to_datetime(df_norm['start_date_local']).max().date()}"
    )

def activities_table(df_year: pd.DataFrame, title: str = "Dernières activités"):
    # Colonnes utiles
    show_cols = [c for c in ["start_date_local","name","sport_type","distance_km","moving_hours","total_elevation_gain","gear_id"] if c in df_year.columns]
    df_view = df_year.copy()
    if "distance_km" not in df_view.columns and "distance" in df_view.columns:
        df_view["distance_km"] = df_view["distance"] / 1000.0
        if "distance_km" not in show_cols:
            show_cols.append("distance_km")
    if "moving_hours" not in df_view.columns and "moving_time" in df_view.columns:
        df_view["moving_hours"] = df_view["moving_time"] / 3600.0
        if "moving_hours" not in show_cols:
            show_cols.append("moving_hours")

    if "start_date_local" in df_view.columns:
        df_view["start_date_local"] = pd.to_datetime(df_view["start_date_local"]).dt.tz_localize(None)

    st.subheader(title)
    st.dataframe(
        df_view[show_cols] if show_cols else df_view,
        use_container_width=True,
        hide_index=True
    )

# ----------------- Pages -----------------
def page_accueil(df: pd.DataFrame):
    df_filtered, year = ui_filters(df, st.container())
    yearly_stats(df_filtered, year)
    st.markdown("---")
    activities_table(df_filtered, "Dernières activités")

def page_stats(df: pd.DataFrame):
    df_filtered, year = ui_filters(df, st.container())
    yearly_stats(df_filtered, year)

def page_activites(df: pd.DataFrame):
    df_filtered, _ = ui_filters(df, st.container())
    activities_table(df_filtered, "Toutes les activités (filtrées)")

def page_reglages():
    st.subheader("Réglages")
    st.write("Ici vous pourrez définir des préférences (à compléter).")

# ----------------- Main -----------------
def main():
    load_dotenv()
    df = load_data()
    if df.empty:
        st.warning("Aucune donnée trouvée. Utilisez le fichier d'exemple inclus ou importez vos activités Strava.")
        if os.path.exists(DATA_SAMPLE_CSV):
            st.caption("Un fichier d'exemple a été trouvé : data/sample_activities.csv")
        return

    page = st.session_state.menu
    if page == "Accueil":
        page_accueil(df)
    elif page == "Statistiques":
        page_stats(df)
    elif page == "Activités":
        page_activites(df)
    elif page == "Réglages":
        page_reglages()
    else:
        page_accueil(df)

if __name__ == "__main__":
    main()
