from typing import Iterable, Tuple
import pandas as pd
import numpy as np

def eddington_number(distances_km: Iterable[float]) -> int:
    # Eddington number E such that at least E days have distance >= E
    d = np.sort(np.array(list(distances_km))[~np.isnan(list(distances_km))])[::-1]
    E = 0
    for i, val in enumerate(d, start=1):
        if val >= i:
            E = i
        else:
            break
    return int(E)

def normalize_activities(df: pd.DataFrame) -> pd.DataFrame:
    # Expect columns from Strava API; make safe transforms and add helpers
    df = df.copy()
    # Distance from meters to km
    if "distance" in df.columns:
        df["distance_km"] = df["distance"] / 1000.0
    # Moving time to hours
    if "moving_time" in df.columns:
        df["moving_hours"] = df["moving_time"] / 3600.0
    # Pace for runs (min/km), speed for rides (km/h)
    df["sport_type"] = df.get("sport_type", df.get("type", "Workout"))
    df["date"] = pd.to_datetime(df["start_date_local"]).dt.date
    df["year"] = pd.to_datetime(df["start_date_local"]).dt.year
    df["week"] = pd.to_datetime(df["start_date_local"]).dt.isocalendar().week.astype(int)
    return df

def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_activities(df)
    grp = df.groupby("date").agg(
        distance_km=("distance_km", "sum"),
        moving_hours=("moving_hours", "sum"),
        activities=("id", "count"),
    ).reset_index()
    return grp

def weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_activities(df)
    wk = df.groupby(["year","week"]).agg(
        distance_km=("distance_km", "sum"),
        moving_hours=("moving_hours", "sum"),
        activities=("id","count"),
    ).reset_index().sort_values(["year","week"])
    return wk

def gear_distance(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_activities(df)
    if "gear_id" not in df.columns:
        return pd.DataFrame(columns=["gear_id","distance_km"])
    g = df.groupby("gear_id").agg(distance_km=("distance_km","sum")).reset_index().sort_values("distance_km", ascending=False)
    return g
