"""
Transform rawData.csv (FBref-style scraped stats) into players.csv format
(player_id, name, team, position, goals, assists, minutes, nationality, age).

Rules applied:
- Keep a player only if MP > 0 AND minutes played > 0 (this naturally
  includes any new players present in rawData who weren't in the old
  players.csv, and drops anyone with no game time).
- minutes comes straight from rawData's Min column 
- For multi-position players (e.g. "DF,MF"), always take the first
  listed position (DF,MF -> Defender).
- Nation code (e.g. "in IND") is split and mapped to a full country name.
"""

import pandas as pd

# ----------------------------------------------------------------------
# CONFIG - edit these to match your actual squad decisions
# ----------------------------------------------------------------------

TEAM_NAME = "Mohun Bagan Super Giants"

# Country code (as it appears before the 3-letter code in "Nation", e.g.
# "in" in "in IND") -> full country name
NATION_MAP = {
    "in": "India",
    "ps": "Palestine",
    "br": "Brazil",
    "es": "Spain",
    "ar": "Argentina",
    "dk": "Denmark",
    "au": "Australia",
    "sct": "Scotland",
    "pt": "Portugal",
    "fi": "Finland",
    "uz": "Uzbekistan",
    "cm": "Cameroon",
    "rs": "Serbia",
    "ng": "Nigeria",
    "fr": "France",
    "jp": "Japan",
}

# Position abbreviation -> full name
POSITION_MAP = {
    "GK": "Goalkeeper",
    "DF": "Defender",
    "MF": "Midfielder",
    "FW": "Forward",
}

# For players with MULTIPLE listed positions (e.g. "DF,MF"), always take
# the first one listed (per your instruction: "DF,MF" -> Defender).

# ----------------------------------------------------------------------
# TRANSFORM
# ----------------------------------------------------------------------

def clean_number(val):
    """Strip thousands-separator commas and convert to int, treating blank/NaN as 0."""
    if pd.isna(val) or val == "":
        return 0
    if isinstance(val, str):
        val = val.replace(",", "")
    return int(float(val))


def resolve_position(pos_field: str) -> str:
    first_code = pos_field.split(",")[0].strip()
    return POSITION_MAP.get(first_code, first_code)


def resolve_nationality(nation_field: str) -> str:
    code, _iso3 = nation_field.split()
    return NATION_MAP.get(code, code)


def load_raw(raw_path: str) -> pd.DataFrame:
    if raw_path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(raw_path)
    return pd.read_csv(raw_path)


def transform(raw_path: str, out_path: str) -> pd.DataFrame:
    df = load_raw(raw_path)

    # Clean minutes first since blanks need to become 0 before filtering
    df["Min"] = df["Min"].apply(clean_number)

    # Keep only players who have actually played this season:
    # matches played > 0 AND minutes played > 0
    df = df[(df["MP"] > 0) & (df["Min"] > 0)].copy()

    out = pd.DataFrame()
    out["player_id"] = range(1, len(df) + 1)
    out["name"] = df["Player"].values
    out["team"] = TEAM_NAME
    out["position"] = [resolve_position(pos) for pos in df["Pos"]]
    out["goals"] = df["Gls"].apply(clean_number).values
    out["assists"] = df["Ast"].apply(clean_number).values
    out["minutes"] = df["Min"].values
    out["nationality"] = df["Nation"].apply(resolve_nationality).values
    out["age"] = df["Age"].values

    out.to_csv(out_path, index=False)
    return out


if __name__ == "__main__":
    result = transform("rawData.xlsx", "players_transformed.csv")
    print(result.to_string(index=False))
