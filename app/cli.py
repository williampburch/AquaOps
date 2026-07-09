from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.core.config import get_settings
from app.demo.seed import seed_demo_data
from app.infrastructure.db.session import SessionLocal


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aquaops")
    subcommands = parser.add_subparsers(dest="command", required=True)

    seed_demo_parser = subcommands.add_parser(
        "seed-demo",
        help="Create a refreshable demo login with realistic aquarium data.",
    )
    seed_demo_parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Allow seeding when APP_ENV=production.",
    )

    args = parser.parse_args(argv)
    if args.command == "seed-demo":
        settings = get_settings()
        with SessionLocal() as session:
            result = seed_demo_data(
                session,
                settings,
                allow_production=args.allow_production,
            )
        print("Demo data seeded.")
        print(f"Login: {result.email}")
        print(f"Password: {result.password}")
        print(f"Tanks: {result.tank_count}")
        print(f"Events: {result.event_count}")
        print(f"Reminders: {result.reminder_count}")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
