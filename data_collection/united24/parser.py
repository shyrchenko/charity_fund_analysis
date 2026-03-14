import datetime
import json
import os
import tempfile
from io import BytesIO

import pdfplumber
import re
import pandas as pd
import requests

DATE_PATTERN = r'^\d{2}\.\d{2}\.\d{4}$'
DATA_MAPPING = {
    "military": "https://files.u24.gov.ua/reports/2026/february/27/report-20260227-zsu.pdf",
    "healthcare": "https://files.u24.gov.ua/reports/2026/february/27/report-20260227-health.pdf",
    "rebuild": "https://files.u24.gov.ua/reports/2026/february/27/report-20260227-rebuild.pdf",
    "demining": "https://files.u24.gov.ua/reports/2026/february/27/report-20260227-demining.pdf",
    "education": "https://files.u24.gov.ua/reports/2026/february/27/report-20260227-education.pdf"
}


def parse_pdf(pdf_bytes: bytes, source: str) -> pd.DataFrame:
    data = []
    columns = ["date", "amount", "metadata"]
    page_index = 0

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_index]
        tables = page.extract_tables()
        if not tables:
            raise ValueError("First page doesn't contain table")

        table = tables[0]
        if not bool(re.match(DATE_PATTERN, table[1][0])):
            raise ValueError("Table is not like expected")

        for row in table[1:]:
            amount = float(row[1].replace(" ", "").replace(",", "."))
            if amount > 0:
                dt = datetime.datetime.strptime(row[0], "%d.%m.%Y").date()
                data.append([dt, amount, dict(source=source)])

        page_index += 1

        while page_index < len(pdf.pages):
            page = pdf.pages[page_index]

            tables = page.extract_tables()
            if not tables:
                print(f"Page {page} doesn't contain table")
                break

            table = tables[0]
            if not bool(re.match(DATE_PATTERN, table[0][0])):
                print(f"Table in page {page} not like expected")
                break

            for row in table:
                amount = float(row[1].replace(" ", "").replace(",", "."))
                if amount > 0:
                    dt = datetime.datetime.strptime(row[0], "%d.%m.%Y").date()
                    data.append([dt, amount, dict(source=source)])

            page_index += 1

    df = pd.DataFrame(data, columns=columns)
    df['fund_name'] = "united24"
    df['date_from'] = df['date']
    df['date_to'] = df['date']
    df['metadata'] = df['metadata'].apply(json.dumps)
    return df


def parse_daily_income() -> pd.DataFrame:
    dfs = []
    for source, url in DATA_MAPPING.items():
        print(f"Parsing {source} report from {url}...")
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Failed to fetch PDF from {url}: {r.status_code} - {r.text}")
            continue

        try:
            df = parse_pdf(r.content, source)
            dfs.append(df)
        except Exception as e:
            print(f"Error parsing PDF from {url}: {e}")

    result_df = pd.concat(dfs, ignore_index=True)
    return result_df


if __name__ == '__main__':
    df = parse_daily_income()
    print(df["date_from"].min(), df["date_from"].max())
    print(set(df["metadata"].apply(lambda x: x["source"])))
