from pathlib import Path
import pyreadr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "complete_journey"

EXPECTED_ROWS = {
    "products.rda": 92331,
    "transactions.rds": 1469307,
}


def main():
    for filename, expected_rows in EXPECTED_ROWS.items():
        path = DATA_DIR / filename

        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy: {path}")

        result = pyreadr.read_r(str(path))

        if len(result) != 1:
            raise ValueError(f"{filename}: cần đúng một đối tượng dữ liệu")

        df = next(iter(result.values()))
        rows, columns = df.shape

        if rows != expected_rows:
            raise ValueError(
                f"{filename}: có {rows:,} dòng, "
                f"kỳ vọng {expected_rows:,}"
            )

        print(f"PASS | {filename} | {rows:,} dòng | {columns} cột")
        print("Tên cột:", ", ".join(df.columns))

        del df, result

    print("Đọc RDA/RDS thành công.")


if __name__ == "__main__":
    main()