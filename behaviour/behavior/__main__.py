"""Run with: python -m behavior path/to/transactions.csv --portfolio-id P001."""

import argparse
import json

from . import analyze_behavior, load_transactions


def main():
    parser = argparse.ArgumentParser(description="FinSight behaviour analysis")
    parser.add_argument("csv_path")
    parser.add_argument("--portfolio-id")
    parser.add_argument("--observation-start")
    parser.add_argument("--observation-end")
    args = parser.parse_args()
    try:
        result = analyze_behavior(
            load_transactions(args.csv_path), portfolio_id=args.portfolio_id,
            observation_start=args.observation_start, observation_end=args.observation_end,
        )
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
