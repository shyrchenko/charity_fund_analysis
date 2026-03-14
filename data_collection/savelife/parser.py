import pandas as pd
from curl_cffi import requests  # using curl_cffi to handle cookies and impersonation (e.g., to avoid Claudflare blocks)
from datetime import datetime


API_URL = "https://cba-transapi.savelife.in.ua/wp-json/savelife/reporting/income/filters"
BASE_URL = "https://savelife.in.ua/"


def parse_daily_income(date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Fetches daily income data from the Savelife API for the specified date range."""
    print(f"Fetching data from {date_from} to {date_to}...")
    session = requests.Session(impersonate="chrome")

    # get initial cookies by visiting the base URL
    session.get(BASE_URL)

    params = {
        "date_from": date_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "date_to": date_to.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "timeoffset": "7200",
        "ver": "3",
        "lang": "ua"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": BASE_URL,
        "referer": BASE_URL,
    }

    # make the API request with the session to include cookies and impersonation
    r = session.get(API_URL, params=params, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Failed to fetch data: {r.status_code} - {r.text}")

    try:
        data = r.json()
    except Exception as e:
        raise Exception(f"Failed to parse JSON response: {e} from response: {r.text}")

    # data structure: {"2026-01-01": [{"amount": "1000", "source": "donation"}, ...], ...}
    unwrapped_data = []

    for date_str, rows in data["chart"].items():
        for row in rows:
            try:
                processed_row = row.copy()
                processed_row["date"] = date_str
                source = processed_row.pop("source")
                processed_row["metadata"] = dict(source=source)
                unwrapped_data.append(processed_row)
            except Exception as e:
                print(f"Error processing row {row} for date {date_str}: {e}")

    df = pd.DataFrame(unwrapped_data)
    df['fund_name'] = "savelife"
    df['date_from'] = pd.to_datetime(df['date'])
    df['date_to'] = df['date_from']
    df['amount'] = df['amount'].astype(float)
    return df


if __name__ == '__main__':
    date_from = datetime(2024, 4, 1)
    date_to = datetime(2026, 1, 31)
    df = parse_daily_income(date_from, date_to)
    print(len(df))
    print(df["date_from"].min(), df["date_from"].max())
