from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parent.parent
SQL_FILE = ROOT / "data" / "raw" / "Hepatitis_std.sql"
OUTPUT_DIR = ROOT / "data" / "processed"

EXPECTED_ROWS = {
    "Bio": 32,
    "dispat": 500,
    "indis": 5691,
    "inf": 196,
    "rel11": 621,
    "rel12": 5691,
    "rel13": 196,
}


def extract_columns(sql, table):
    pattern = rf"CREATE TABLE `{re.escape(table)}` \((.*?)\) ENGINE="
    match = re.search(pattern, sql, flags=re.DOTALL)

    if not match:
        raise ValueError(f"Could not find schema for table {table}")

    return re.findall(r"^\s+`([^`]+)`\s+", match.group(1), flags=re.MULTILINE)


def parse_values(statement):
    # parse "(..),(..)" rows
    rows = []
    i = 0

    while i < len(statement):
        if statement[i].isspace() or statement[i] == ",":
            i += 1
            continue

        if statement[i] != "(":
            raise ValueError(f"Unexpected character at position {i}: {statement[i]!r}")

        i += 1
        row = []

        while True:
            while i < len(statement) and statement[i].isspace():
                i += 1

            if i >= len(statement):
                raise ValueError("Unexpected end of SQL while parsing a row")

            if statement[i] == "'":
                i += 1
                value = []

                while i < len(statement):
                    char = statement[i]

                    if char == "'":
                        if i + 1 < len(statement) and statement[i + 1] == "'":
                            value.append("'")
                            i += 2
                            continue
                        i += 1
                        break

                    if char == "\\":
                        if i + 1 < len(statement):
                            value.append(statement[i + 1])
                            i += 2
                            continue

                    value.append(char)
                    i += 1
                else:
                    raise ValueError("Unterminated quoted SQL value")

                row.append("".join(value))

            else:
                start = i
                while i < len(statement) and statement[i] not in ",)":
                    i += 1

                token = statement[start:i].strip()
                row.append(None if token.upper() == "NULL" else token)

            while i < len(statement) and statement[i].isspace():
                i += 1

            if i >= len(statement):
                raise ValueError("Unexpected end of SQL inside a row")

            if statement[i] == ",":
                i += 1
                continue

            if statement[i] == ")":
                i += 1
                break

            raise ValueError(f"Unexpected character inside row: {statement[i]!r}")

        rows.append(row)

    return rows


def main():
    if not SQL_FILE.exists():
        raise FileNotFoundError(SQL_FILE)

    sql = SQL_FILE.read_text(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True

    for table, expected_count in EXPECTED_ROWS.items():
        columns = extract_columns(sql, table)

        insert_pattern = (
            rf"INSERT INTO `{re.escape(table)}` VALUES\s*(.*?);"
        )
        match = re.search(insert_pattern, sql, flags=re.DOTALL)

        if not match:
            raise ValueError(f"Could not find INSERT statement for {table}")

        rows = parse_values(match.group(1))

        for row_number, row in enumerate(rows, start=1):
            if len(row) != len(columns):
                raise ValueError(
                    f"{table}, row {row_number}: "
                    f"expected {len(columns)} values, got {len(row)}"
                )

        output_file = OUTPUT_DIR / f"{table}.csv"

        with output_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            writer.writerows(rows)

        actual_count = len(rows)
        status = "OK" if actual_count == expected_count else "MISMATCH"

        if status != "OK":
            all_ok = False

        print(
            f"{table:8} | rows: {actual_count:5} | "
            f"expected: {expected_count:5} | {status}"
        )

    print(f"\nCSV files saved in: {OUTPUT_DIR.resolve()}")

    if not all_ok:
        raise SystemExit("Row-count verification failed.")


if __name__ == "__main__":
    main()
