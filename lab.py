"""ЛР6. ClickHouse + Python. Вариант 20: мебельная фабрика."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import clickhouse_connect
from dotenv import load_dotenv
from prettytable import PrettyTable

from queries import REPORTS
from schema import SCHEMA

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def encode_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Неподдерживаемый тип: {type(value)}")


def format_table(headers, rows):
    table = PrettyTable(headers)
    table.align = "l"
    for row in rows:
        table.add_row(["NULL" if x is None else str(x) for x in row])
    return str(table)


def initialize_database(client, db):
    """Создать таблицы, заполнить пустые; имеющиеся записи сохранить."""
    client.command(f"CREATE DATABASE IF NOT EXISTS {db}")
    samples = json.loads((ROOT / "sample_data.json").read_text(encoding="utf-8"))
    counts = []
    for table, definition in SCHEMA.items():
        client.command(definition.format(db=db))
        before = client.command(f"SELECT count() FROM {db}.{table}")
        added = 0
        if before == 0:
            data = samples[table]
            rows = []
            for source_row in data["rows"]:
                row = list(source_row)
                for i, column in enumerate(data["columns"]):
                    if column in {"order_date", "completed_date"} and row[i] is not None:
                        row[i] = date.fromisoformat(row[i])
                    elif column in {"base_price", "unit_price"}:
                        row[i] = Decimal(row[i])
                rows.append(row)
            client.insert(f"{db}.{table}", rows, column_names=data["columns"])
            added = len(rows)
        after = client.command(f"SELECT count() FROM {db}.{table}")
        counts.append((table, before, added, after))
    return counts


def create_charts(results, output):
    """Построить диаграммы по результатам SQL, полученным от ClickHouse."""
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    money = FuncFormatter(lambda value, _: f"{value:,.0f}".replace(",", " "))
    monthly = results[3]["rows"]
    categories = results[4]["rows"]
    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    bars = ax.bar([str(r[0])[:7] for r in monthly], [float(r[2]) for r in monthly], color="#3c6e8f", width=0.55)
    ax.bar_label(bars, labels=[f"{r[2]:,.0f}".replace(",", " ") for r in monthly], padding=5)
    ax.set(title="Выручка по месяцам завершения заказов", xlabel="Месяц завершения", ylabel="Выручка, руб.")
    ax.yaxis.set_major_formatter(money)
    ax.set_ylim(0, max(float(r[2]) for r in monthly) * 1.2)
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    fig.savefig(output / "revenue_by_month.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
    bars = ax.barh([r[0] for r in categories], [float(r[2]) for r in categories], color="#4b8472")
    ax.bar_label(bars, labels=[f"{r[2]:,.0f}".replace(",", " ") for r in categories], padding=5)
    ax.set(title="Выручка по категориям мебели", xlabel="Выручка, руб.")
    ax.xaxis.set_major_formatter(money)
    ax.set_xlim(0, max(float(r[2]) for r in categories) * 1.23)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    fig.savefig(output / "revenue_by_category.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=os.getenv("CLICKHOUSE_DATABASE", "furniture_factory_lr6"))
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--no-charts", action="store_true", help="Не строить диаграммы")
    args = parser.parse_args()
    # Имя базы используется как SQL-идентификатор, пользовательские значения — как параметры.
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.database):
        parser.error("Имя базы может содержать латинские буквы, цифры и знак подчёркивания")
    args.output.mkdir(parents=True, exist_ok=True)
    client = None
    try:
        client = clickhouse_connect.get_client(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "18123")),
            username=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "0000"),
            connect_timeout=5,
            send_receive_timeout=60,
        )
        version = str(client.command("SELECT version()"))
        print(f"ЛР6. Вариант 20. ClickHouse {version}")
        print(f"База данных: {args.database}\n")
        counts = initialize_database(client, args.database)
        init_text = format_table(["Таблица", "Было", "Добавлено", "Стало"], counts)
        print(init_text)
        results = []
        log = [f"ЛР6. Вариант 20. ClickHouse {version}", f"База данных: {args.database}", init_text]
        for number, (function, title, headers) in enumerate(REPORTS, 1):
            result = function(client, args.database)
            result_text = format_table(headers, result.result_rows)
            print(f"\n{number}. {title}\n{result_text}")
            log.append(f"{number}. {title}\n{result_text}")
            results.append({
                "number": number, "function": function.__name__, "title": title,
                "columns": list(result.column_names), "headers": headers,
                "rows": result.result_rows, "text": result_text,
            })
        payload = {"server_version": version, "database": args.database, "counts": counts, "queries": results}
        (args.output / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=encode_value), encoding="utf-8")
        (args.output / "run.txt").write_text("\n\n".join(log) + "\n", encoding="utf-8")
        if not args.no_charts:
            create_charts(results, args.output)
        print(f"\nРезультаты сохранены в {args.output}")
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Ошибка выполнения: {error}", file=sys.stderr)
        sys.exit(1)
