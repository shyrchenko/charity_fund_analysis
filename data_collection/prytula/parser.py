import pandas as pd

# TODO: implement parser for Prytula Foundation reports if needed.
# For now, we just return DataFrame with data collected form site by manual work


def parse_report() -> pd.DataFrame:
    data = [
        ["01.01.2025", "31.01.2025", 89351180],
        ["01.02.2025", "28.02.2025", 164209513],
        ["01.03.2025", "31.03.2025", 128210315],
        ["01.04.2025", "30.04.2025", 91615937],
        ["01.05.2025", "31.05.2025", 135079858],
        ["01.06.2025", "30.06.2025", 183856874],
        ["01.07.2025", "31.07.2025", 272579041],
        ["01.08.2025", "31.08.2025", 129325828],
        ["01.09.2025", "30.09.2025", 226989664],
        ["01.10.2025", "31.10.2025", 136408436],
        ["01.11.2025", "30.11.2025", 286644390],
        ["01.12.2025", "31.12.2025", 599388014],
    ]
    df = pd.DataFrame(data, columns=["date_from", "date_to", "amount"])
    df["date_from"] = pd.to_datetime(df["date_from"], format="%d.%m.%Y").dt.date
    df["date_to"] = pd.to_datetime(df["date_to"], format="%d.%m.%Y").dt.date

    df["metadata"] = {}
    df["fund_name"] = "prytula"
    return df
