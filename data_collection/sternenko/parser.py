import pandas as pd

# TODO: implement parser for Sternenko Foundation reports if needed.
# For now, we just return DataFrame with data collected form site by manual work


def parse_report() -> pd.DataFrame:
    data = [
        ["01.03.2025", "31.03.2025", 257411575],
        ["01.04.2025", "30.04.2025", 181679123],
        ["01.05.2025", "31.05.2025", 215314891],
        ["01.06.2025", "30.06.2025", 298354393],
        ["01.07.2025", "31.07.2025", 248949768],
        ["01.08.2025", "31.08.2025", 205067304],
        ["01.09.2025", "30.09.2025", 208413460],
        ["01.10.2025", "31.10.2025", 317002078],
        ["01.11.2025", "30.11.2025", 330069046],
        ["01.12.2025", "31.12.2025", 293318898],
        ["01.01.2026", "31.01.2026", 266555539],
        ["01.02.2026", "28.02.2026", 180978672],
    ]
    df = pd.DataFrame(data, columns=["date_from", "date_to", "amount"])
    df["date_from"] = pd.to_datetime(df["date_from"], format="%d.%m.%Y").dt.date
    df["date_to"] = pd.to_datetime(df["date_to"], format="%d.%m.%Y").dt.date

    df["metadata"] = {}
    df["fund_name"] = "sternenko"
    return df
