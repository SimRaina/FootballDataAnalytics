"""
Reusable UI components for ISL Dashboard
Eliminates code duplication across pages
"""
from pathlib import Path
import streamlit as st
import pandas as pd

# Absolute project root — ensures logo paths resolve correctly on Cloud
_PROJECT_ROOT = Path(__file__).parent.parent


def _resolve_logo_path(logo_path, league_data_dir=None):
    """Resolve a team logo path relative to the active league data directory."""
    if not logo_path:
        return None

    candidate = Path(logo_path)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    search_roots = []
    if league_data_dir:
        p = Path(league_data_dir)
        # Accept both absolute and project-root-relative league_data_dir
        search_roots.append(p if p.is_absolute() else _PROJECT_ROOT / p)
    # Always search using absolute project-root paths so Cloud CWD doesn't matter
    search_roots.extend([
        _PROJECT_ROOT / "data" / "isl",
        _PROJECT_ROOT / "data" / "epl",
        _PROJECT_ROOT / "data",
        _PROJECT_ROOT,
    ])

    for base in search_roots:
        try:
            resolved = base / candidate
            if resolved.exists():
                return resolved
        except Exception:
            continue

    return None

def display_match_result(match, show_venue=True, show_gameweek=True):
    """
    Display a single match result in standardized format.
    
    Parameters:
    - match: DataFrame row with match data
    - show_venue: Include venue information
    - show_gameweek: Include gameweek number
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**{match['home_team']}** {int(match['home_goals'])} - {int(match['away_goals'])} **{match['away_team']}**")
        
        caption_parts = [str(match['date'])]
        if show_gameweek and pd.notna(match.get('gameweek')):
            caption_parts.append(f"GW {int(match['gameweek'])}")
        if show_venue and pd.notna(match.get('venue')):
            caption_parts.append(str(match['venue']))
        
        st.caption(" | ".join(caption_parts))
    st.divider()

def display_matches_table(matches_df, columns=None, sort_by="date", ascending=False):
    """
    Display matches in a formatted table.
    
    Parameters:
    - matches_df: DataFrame with match data
    - columns: List of columns to display (default: date, home_team, goals, away_team, venue)
    - sort_by: Column to sort by
    - ascending: Sort order
    """
    if columns is None:
        columns = ["date", "gameweek", "home_team", "home_goals", "away_team", "away_goals", "venue"]
    
    if len(matches_df) == 0:
        st.info("No matches to display")
        return
    
    display_df = matches_df[columns].copy()
    
    # Convert date to datetime for proper sorting if it exists
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"], format="%d-%m-%Y", errors='coerce')
        display_df = display_df.sort_values("date", ascending=ascending)
        display_df["date"] = display_df["date"].dt.strftime("%d-%m-%Y")
    
    # Rename columns for display
    display_df.columns = ["Date", "GW", "Home", "HG", "Away", "AG", "Venue"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

def display_team_header(team_info, logo_path=None, show_coach=True, show_stadium=True, league_data_dir=None):
    """
    Display a standardized team header with logo and info.
    
    Parameters:
    - team_info: DataFrame row with team data
    - logo_path: Path to team logo (if None, uses logo_path from team_info)
    - show_coach: Include coach information
    - show_stadium: Include stadium information
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if logo_path is None:
            logo_path = team_info.get("logo_path", "")
        
        if logo_path:
            resolved_logo = _resolve_logo_path(logo_path, league_data_dir=league_data_dir)
            if resolved_logo is not None:
                st.image(str(resolved_logo), width=150)
            else:
                st.write("🏟️ Logo")
                st.caption("(Logo not found)")
    
    with col2:
        st.subheader(team_info["team_name"])
        st.write(f"**City:** {team_info.get('city', 'N/A')}")
        if show_coach:
            st.write(f"**Coach:** {team_info.get('coach', 'N/A')}")
        if show_stadium:
            st.write(f"**Stadium:** {team_info.get('stadium', 'N/A')}")

def display_key_metrics(metrics_dict):
    """
    Display key metrics in a formatted grid.
    
    Parameters:
    - metrics_dict: Dictionary with metric_name: value pairs
    """
    cols = st.columns(len(metrics_dict))
    for i, (name, value) in enumerate(metrics_dict.items()):
        cols[i].metric(name, value)

def display_empty_state(message="No data available", icon="ℹ️"):
    """Display an empty state message."""
    st.info(f"{icon} {message}")

