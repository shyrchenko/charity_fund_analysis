import datetime

from data_collection.prytula.parser import parse_report as parse_prytula_report
from data_collection.united24.parser import parse_daily_income as parse_united24_report
from data_collection.savelife.parser import parse_daily_income as parse_savelife_report
from data_collection.sternenko.parser import parse_report as parse_sternenko_report
from .utils import create_db, insert_data
import duckdb


def main():
    create_db()

    prytula_report = parse_prytula_report()
    united24_report = parse_united24_report()
    savelife_report = parse_savelife_report(
        date_from=datetime.datetime(2022, 4, 1), date_to=datetime.datetime(2026, 2, 28)
    )
    sternenko_report = parse_sternenko_report()

    con = duckdb.connect("charity_reports.duckdb")
    insert_data(con, prytula_report)
    insert_data(con, united24_report)
    insert_data(con, savelife_report)
    insert_data(con, sternenko_report)
    con.close()


if __name__ == "__main__":
    # python -m db.fill_db
    main()
