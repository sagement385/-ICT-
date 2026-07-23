"""Synchronize Chungbuk HIRA basic hospital records after API configuration."""

import argparse
import asyncio

from app.pipelines.hospital_sync.pipeline import sync_hospitals


def main() -> None:
    """Run the source-backed synchronization command."""

    parser = argparse.ArgumentParser(description="Sync HIRA Chungbuk hospital basic records")
    parser.add_argument("--limit", type=int, help="Maximum number of hospitals to load for a controlled test run")
    parser.add_argument("--page-size", type=int, default=1000, help="HIRA page size, between 1 and 1000")
    args = parser.parse_args()
    loaded = asyncio.run(sync_hospitals(limit=args.limit, page_size=args.page_size))
    print(f"Loaded {loaded} source-backed hospital records.")


if __name__ == "__main__":
    main()
