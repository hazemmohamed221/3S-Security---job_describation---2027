"""Create a verified UTC-stamped backup without starting the application."""
import argparse
from pathlib import Path
from backups import backup_database
from scripts.migrate_passwords import DEFAULT_DB


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print(backup_database(args.database))
