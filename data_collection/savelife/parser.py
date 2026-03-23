import math
import time
import pandas as pd
from curl_cffi import requests  # using curl_cffi to handle cookies and impersonation (e.g., to avoid Claudflare blocks)
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


DAILY_URL = "https://cba-transapi.savelife.in.ua/wp-json/savelife/reporting/income/filters"
TRANSACTIONS_URL = "https://cba-transapi.savelife.in.ua/wp-json/savelife/reporting/income"


BASE_URL = "https://savelife.in.ua/"

MAX_REQUEST_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = 45
RETRY_BACKOFF_SECONDS = 5
CHUNK_SIZE_DAYS = 3


def _get_session_with_cookies():
    """Fetches cookies from the Savelife website by making a GET request to the base URL."""
    session = requests.Session(impersonate="chrome")
    session.get(BASE_URL)
    return session


def parse_daily_income(date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Fetches daily income data from the Savelife API for the specified date range."""
    print(f"Fetching data from {date_from} to {date_to}...")
    session = _get_session_with_cookies()

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
    r = session.get(DAILY_URL, params=params, headers=headers)
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


def parse_transactions(date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """
    Fetches paginated transaction-level income data for a given date window.

    The API exposes a maximum of 100 rows per page, therefore the requested date range is split into
    smaller three-day slices (see `CHUNK_SIZE_DAYS`). Each slice is downloaded (potentially in parallel),
    normalized, and appended to the final DataFrame.

    Args:
        date_from: Inclusive start datetime (UTC).
        date_to: Inclusive end datetime (UTC).

    Returns:
        Pandas DataFrame where every row represents a transaction with normalized metadata.
    """
    session = _get_session_with_cookies()

    # Stable headers help the request look like a regular browser call and reuse initial cookies.
    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": BASE_URL,
        "referer": BASE_URL,
    }

    def _request_with_retry(params, target_description):
        """
        Makes a GET request with retries and exponential backoff.

        Args:
            params: Query parameters for the API.
            target_description: Human-friendly label used in logs for context.

        Returns:
            `requests.Response` object when successful, otherwise `None`.
        """
        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            try:
                # All requests go through the shared session so cookies and TLS fingerprints match.
                response = session.get(
                    TRANSACTIONS_URL,
                    params=params,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT_SECONDS
                )
                if response.status_code == 200:
                    return response

                print(
                    f"Failed request ({response.status_code}) for {target_description} "
                    f"[attempt {attempt}/{MAX_REQUEST_ATTEMPTS}]"
                )
            except Exception as e:
                print(
                    f"Request error for {target_description} "
                    f"[attempt {attempt}/{MAX_REQUEST_ATTEMPTS}]: {e}"
                )

            if attempt < MAX_REQUEST_ATTEMPTS:
                sleep_time = RETRY_BACKOFF_SECONDS * attempt
                print(f"Retrying {target_description} in {sleep_time} seconds...")
                time.sleep(sleep_time)

        print(f"Giving up on {target_description} after {MAX_REQUEST_ATTEMPTS} attempts.")
        return None

    def _parse_row(rows):
        """
        Converts raw API rows into dictionaries ready for `pd.DataFrame`.

        Args:
            rows: Sequence of dictionaries returned via the API under the "rows" key.

        Returns:
            List of normalized transaction dictionaries.
        """
        transactions = []
        for row in rows:
            try:
                # Normalize types eagerly (float + datetime) and bundle descriptive values in metadata.
                transactions.append({
                    "amount": float(row["amount"]),
                    "date": pd.to_datetime(row["date"]),
                    "metadata": {
                        "source": row["source"],
                        "comment": row["comment"],
                        "project": row.get("project"),
                        "currency": row["currency"]
                    }
                })
            except Exception as e:
                print(f"Error: {e}")
        return transactions

    def fetch_chunk(chunk_from: datetime, chunk_to: datetime):
        """
        Retrieves every page that belongs to a particular inclusive [chunk_from, chunk_to] window.

        Keeping the windows small ensures fast responses and more actionable debug logging.
        """
        chunk_label = f"{chunk_from.date()} - {chunk_to.date()}"
        print(f"\nChunk: {chunk_label}")

        # API treats the `date_to` parameter as exclusive, therefore we add a day to cover the full range.
        exclusive_chunk_to = chunk_to + timedelta(days=1)
        base_params = {
            "date_from": chunk_from.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "date_to": exclusive_chunk_to.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "timeoffset": "7200",
            "per_page": 100,
            "ver": "3",
            "lang": "ua"
        }

        first_page_params = dict(base_params)
        first_page_params["page"] = 1
        response_raw = _request_with_retry(first_page_params, f"chunk {chunk_label} page 1")
        if response_raw is None:
            return []

        # First page contains pagination metadata (total_count) that we use to discover remaining pages.
        response = response_raw.json()
        total_count = response.get("total_count", 0)
        per_page = base_params["per_page"]
        total_pages = math.ceil(total_count / per_page) if total_count else 0

        chunk_transactions = []
        chunk_transactions.extend(_parse_row(response.get("rows", [])))

        # Iterate over the remaining pages sequentially so we do not overwhelm the API.

        for page in range(2, total_pages + 1):
            page_params = dict(base_params)
            page_params["page"] = page
            response_raw = _request_with_retry(page_params, f"chunk {chunk_label} page {page}")
            if response_raw is None:
                continue

            response = response_raw.json()
            chunk_transactions.extend(_parse_row(response.get("rows", [])))
        print(f"Completed chunk {chunk_label} with {len(chunk_transactions)} transactions.")

        return chunk_transactions

    def _generate_chunks(start_date: datetime, end_date: datetime):
        """
        Yields inclusive date windows that are at most `CHUNK_SIZE_DAYS` wide.

        Chunking keeps requests lightweight, avoids timeouts, and surfaces granular logs.
        """
        current = start_date
        while current <= end_date:
            chunk_end = min(current + timedelta(days=CHUNK_SIZE_DAYS), end_date)
            yield current, chunk_end
            current = chunk_end + timedelta(days=1)

    chunks = list(_generate_chunks(date_from, date_to))
    print(f"Prepared {len(chunks)} chunks: {chunks}")

    # Shared accumulator that collects normalized rows returned by chunk workers.
    all_transactions = []

    # Use multiple threads to overlap network-bound operations and speed up parsing.
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_chunk, c[0], c[1]) for c in chunks]

        # Append chunk results as soon as they become available to keep memory usage predictable.
        for future in as_completed(futures):
            all_transactions.extend(future.result())

    print(f"Total transactions fetched: {len(all_transactions)}")

    # Turn the collected dictionaries into the canonical schema expected by downstream jobs.
    df = pd.DataFrame(all_transactions)
    df['fund_name'] = "savelife"
    df['date_from'] = df['date']
    df['date_to'] = df['date']
    df['amount'] = df['amount'].astype(float)

    return df


if __name__ == '__main__':
    date_from = datetime(2026, 1, 1)
    date_to = datetime(2026, 1, 31)
    date_from = pd.to_datetime(date_from, utc=True)
    date_to = pd.to_datetime(date_to, utc=True)

    df = parse_transactions(date_from, date_to)
    print(len(df))
    print(df["date_from"].min(), df["date_from"].max())
    print(df.amount.sum())
