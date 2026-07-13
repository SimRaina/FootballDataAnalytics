import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st

# Constant encoding for all CSV files
CSV_ENCODING = "latin-1"

# Absolute project root — works regardless of working directory (fixes Cloud path issues)
_PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = _PROJECT_ROOT / "config" / "league_config.json"


def _is_cloud_env() -> bool:
    """Return True when running on Streamlit Community Cloud."""
    return os.environ.get("STREAMLIT_SHARING_MODE", "").lower() == "streamlit"


def _read_config_file():
    if not CONFIG_PATH.exists():
        return {}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def get_available_leagues():
    """Return all configured leagues from the JSON file."""
    loaded = _read_config_file()
    leagues = loaded.get("leagues", {})
    if isinstance(leagues, dict) and leagues:
        return [
            get_configured_league(league_name=name)
            for name in leagues.keys()
        ]
    return [get_configured_league()]


def render_league_selector(location="top"):
    """Show a selector for configured leagues and return the selected config."""
    available_leagues = get_available_leagues()
    if not available_leagues:
        return get_configured_league()

    names = [league["league_name"] for league in available_leagues]
    if "selected_league" not in st.session_state:
        st.session_state.selected_league = get_configured_league()["league_name"]

    if location == "sidebar":
        selected_name = st.sidebar.selectbox(
            "Choose League & Season",
            names,
            index=names.index(st.session_state.selected_league) if st.session_state.selected_league in names else 0,
            key="selected_league",
        )
    else:
        selected_name = st.selectbox(
            "Choose League & Season",
            names,
            index=names.index(st.session_state.selected_league) if st.session_state.selected_league in names else 0,
            key="selected_league",
        )
    return next((league for league in available_leagues if league["league_name"] == selected_name), available_leagues[0])


def get_configured_league(league_name=None, season=None, data_dir=None):
    """Return the active league configuration, falling back to defaults."""
    default_config = {
        "league_name": "ISL",
        "season": "2025-26",
        "default_season": "2025-26",
        "data_dir": "data",
        "metadata": {
            "display_name": "Indian Super League",
            "page_title": "ISL Dashboard",
            "emoji": "⚽",
            "subtitle": "Your complete platform for Indian Super League data analysis, team evaluation, and professional scouting.",
        },
    }

    loaded = _read_config_file()
    selected_league_name = league_name
    if selected_league_name is None and "selected_league" in st.session_state:
        selected_league_name = st.session_state.selected_league

    if isinstance(loaded.get("leagues"), dict) and loaded.get("leagues"):
        current_key = selected_league_name or loaded.get("current_league") or next(iter(loaded["leagues"].keys()))
        current_cfg = loaded["leagues"].get(current_key, {})
        if isinstance(current_cfg, dict):
            config = dict(default_config)
            config.update({
                "league_name": current_cfg.get("league_name", current_key),
                "season": current_cfg.get("season", current_cfg.get("default_season", default_config["season"])),
                "default_season": current_cfg.get("default_season", current_cfg.get("season", default_config["default_season"])),
                "data_dir": current_cfg.get("data_dir", default_config["data_dir"]),
            })
            metadata = dict(default_config["metadata"])
            metadata.update(current_cfg.get("metadata", {}) or {})
            config["metadata"] = metadata
            config["display_name"] = metadata.get("display_name", config["league_name"])
            config["page_title"] = metadata.get("page_title", f"{config['league_name']} Dashboard")
            config["emoji"] = metadata.get("emoji", "⚽")
            config["subtitle"] = metadata.get("subtitle", f"Your complete platform for {config['display_name']} data analysis, team evaluation, and professional scouting.")
            if season is not None:
                config["season"] = season
            if data_dir is not None:
                config["data_dir"] = data_dir
            return config
    else:
        config = dict(default_config)
        config.update({
            "league_name": loaded.get("league_name", default_config["league_name"]),
            "season": loaded.get("season", loaded.get("default_season", default_config["season"])),
            "default_season": loaded.get("default_season", loaded.get("season", default_config["default_season"])),
            "data_dir": loaded.get("data_dir", default_config["data_dir"]),
        })
        metadata = dict(default_config["metadata"])
        metadata.update(loaded.get("metadata", {}) or {})
        config["metadata"] = metadata
        config["display_name"] = metadata.get("display_name", config["league_name"])
        config["page_title"] = metadata.get("page_title", f"{config['league_name']} Dashboard")
        config["emoji"] = metadata.get("emoji", "⚽")
        config["subtitle"] = metadata.get("subtitle", f"Your complete platform for {config['display_name']} data analysis, team evaluation, and professional scouting.")
        if season is not None:
            config["season"] = season
        if data_dir is not None:
            config["data_dir"] = data_dir
        return config

    config = dict(default_config)
    config["league_name"] = league_name or config["league_name"]
    if season is not None:
        config["season"] = season
    if data_dir is not None:
        config["data_dir"] = data_dir
    return config


@st.cache_data
def load_data(force_csv=False, league_config=None):
    """Load all data from CSV files with caching and type optimization.

    If a preprocessed pickle exists it will be loaded for speed. Use
    `force_csv=True` to re-create the processed cache from CSVs.
    """
    if league_config is None:
        league_config = get_configured_league()

    # Resolve data_dir to an absolute path so it works on Cloud regardless of CWD
    raw_data_dir = Path(league_config.get("data_dir", "data"))
    data_dir = raw_data_dir if raw_data_dir.is_absolute() else _PROJECT_ROOT / raw_data_dir

    # Validate required files exist before attempting to read them
    required_files = ["teams.csv", "players.csv", "matches.csv", "seasons.csv"]
    missing = [f for f in required_files if not (data_dir / f).exists()]
    if missing:
        st.error(
            f"Required data files not found in `{data_dir}`: {', '.join(missing)}. "
            "Please check the data directory configuration."
        )
        st.stop()

    # Pickle cache is skipped on Cloud (ephemeral filesystem + category-dtype
    # serialization issues) and relied on only locally for speed.
    use_pickle = not _is_cloud_env()
    processed_cache = data_dir / "processed.pkl"

    if use_pickle and processed_cache.exists() and not force_csv:
        try:
            data = pd.read_pickle(processed_cache)
            return (
                data["teams"],
                data["players"],
                data["matches"],
                data["seasons"],
                data.get("teams_socials", pd.DataFrame()),
            )
        except Exception:
            # Fall back to CSV if pickle is corrupted or version-mismatched
            pass

    # Read CSVs with basic parsing
    try:
        teams = pd.read_csv(data_dir / "teams.csv", encoding=CSV_ENCODING, low_memory=False)
        players = pd.read_csv(data_dir / "players.csv", encoding=CSV_ENCODING, low_memory=False)
        matches = pd.read_csv(data_dir / "matches.csv", encoding=CSV_ENCODING, low_memory=False, parse_dates=["date"], dayfirst=True)
        seasons = pd.read_csv(data_dir / "seasons.csv", encoding=CSV_ENCODING, low_memory=False)
        teams_socials_path = data_dir / "teams_socials.csv"
        teams_socials = (
            pd.read_csv(teams_socials_path, encoding=CSV_ENCODING, low_memory=False)
            if teams_socials_path.exists()
            else pd.DataFrame()
        )
    except Exception as exc:
        st.error(f"Failed to load data files: {exc}")
        st.stop()

    # Normalize numeric columns safely
    numeric_match_cols = ["home_goals", "away_goals", "gameweek"]
    for col in numeric_match_cols:
        if col in matches.columns:
            matches[col] = pd.to_numeric(matches[col], errors="coerce").fillna(0).astype(int)

    numeric_player_cols = ["goals", "assists", "age", "minutes"]
    for col in numeric_player_cols:
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors="coerce").fillna(0)
            if col != "minutes":
                players[col] = players[col].astype(int)

    # Convert low-cardinality text columns to category to save memory.
    # Skipped on Cloud because category dtypes can fail to serialize across
    # different Pandas/Python versions (pickle compatibility issue).
    if not _is_cloud_env():
        if "team_name" in teams.columns:
            teams["team_name"] = teams["team_name"].astype("category")
        for col in ["team", "position", "nationality"]:
            if col in players.columns:
                players[col] = players[col].astype("category")
        for col in ["home_team", "away_team", "match_status", "season", "venue"]:
            if col in matches.columns:
                matches[col] = matches[col].astype("category")

    # Save processed cache locally for faster subsequent loads (skipped on Cloud)
    if use_pickle:
        try:
            processed = {
                "teams": teams,
                "players": players,
                "matches": matches,
                "seasons": seasons,
                "teams_socials": teams_socials,
            }
            pd.to_pickle(processed, processed_cache)
        except Exception:
            # silently continue if we cannot write cache
            pass

    return teams, players, matches, seasons, teams_socials


def get_current_season(league_config=None):
    """Get the current season from config or default."""
    if league_config is None:
        league_config = get_configured_league()
    return league_config.get("default_season") or league_config.get("season", "2025-26")


@st.cache_data
def get_available_seasons(matches_df):
    """Get list of available seasons from matches data."""
    return sorted(matches_df["season"].unique().tolist())


@st.cache_data
def get_season_matches(matches_df, season):
    """Get matches for a specific season (cached)."""
    return matches_df[matches_df["season"] == season].copy()


@st.cache_data
def get_completed_matches(matches_df, season):
    """Get completed matches for a specific season (cached)."""
    matches = matches_df[matches_df["season"] == season]
    return matches[matches["match_status"] == "completed"].copy()


@st.cache_data
def get_upcoming_matches(matches_df, season):
    """Get upcoming matches for a specific season (cached)."""
    matches = matches_df[matches_df["season"] == season]
    return matches[matches["match_status"] == "upcoming"].copy()

