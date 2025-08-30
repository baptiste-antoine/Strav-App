import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from strava_client import StravaClient
from metrics import normalize_activities

DATA_PATH = os.path.join("data", "activities.parquet")

def str_to_epoch(s: str) -> int:
    return int(pd.Timestamp(s).timestamp())

def main():
    load_dotenv()
    after = os.getenv("IMPORT_AFTER") or None
    before = os.getenv("IMPORT_BEFORE") or None
    after_epoch = str_to_epoch(after) if after else None
    before_epoch = str_to_epoch(before) if before else None

    client = StravaClient()
    rows = list(client.activities(after=after_epoch, before=before_epoch))
    if not rows:
        print("No activities returned.")
        return
    df = pd.DataFrame(rows)
    df = normalize_activities(df)

    os.makedirs("data", exist_ok=True)
    df.to_parquet(DATA_PATH, index=False)
    print(f"Saved {len(df)} activities to {DATA_PATH}")

if __name__ == "__main__":
    main()
