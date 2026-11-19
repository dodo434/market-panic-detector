"""Terminal entry point, with no Qt imports."""

import argparse
from panic_detector.config import load_settings
from panic_detector.models.panic_score import classify_status
from panic_detector.service import snapshot


def main(argv: list[str] | None = None) -> int:
    defaults = load_settings()
    parser = argparse.ArgumentParser(prog="market-panic")
    parser.add_argument("--window", type=int, default=defaults.window)
    parser.add_argument("--tickers", nargs="+", default=list(defaults.universe))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--date", help="Exact historical session, YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        rows = snapshot(args.tickers, args.window, args.refresh)
        if args.date:
            rows = rows[rows["date"] == args.date]
        if not len(rows):
            raise ValueError("No complete window for this date; choose a covered trading session.")
        row = rows[-1]
        print(
            f"{row['date']}   {classify_status(row['level'])}   Panic level {row['level']:.1f}/100"
        )
        print(
            f"Average pair movement {row['average']:.1%} | Leading eigenvalue {row['leading']:.2f} | "
            f"Variance share {row['share']:.1%} | Noise baseline {row['noise']:.2f}"
        )
        missing = sorted(
            set(s.upper().strip() for s in args.tickers) - set(row["symbols"].dtype.names)
        )
        if missing:
            print("Insufficient history: " + ", ".join(missing))
        return 0
    except ValueError as error:
        print(str(error))
    except Exception:
        print("Could not read the stock history; check your cache and retry with --refresh.")
    return 1
