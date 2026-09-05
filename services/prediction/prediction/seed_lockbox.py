"""Operator CLI for materializing a named lockbox protocol."""

from __future__ import annotations

import argparse

from prediction import db
from prediction.folds import seed_lockbox


def resolve_event_ids(connection, event_slugs: list[str]) -> list[int]:
    with connection.cursor() as cursor:
        cursor.execute("select slug, id from events where slug = any(%s)", (event_slugs,))
        ids_by_slug = dict(cursor.fetchall())
    missing = [slug for slug in event_slugs if slug not in ids_by_slug]
    if missing:
        raise ValueError(f"unknown event slugs: {missing}")
    return [ids_by_slug[slug] for slug in event_slugs]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed a retrospective or prospective lockbox.")
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--kind", required=True, choices=("lockbox_retrospective", "lockbox_prospective")
    )
    parser.add_argument("--event-slug", required=True, action="append", dest="event_slugs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        event_ids = resolve_event_ids(connection, args.event_slugs)
        if args.dry_run:
            print(f"validated events {args.event_slugs}; no changes written")
            return
        seed_lockbox(connection, name=args.name, kind=args.kind, event_ids=event_ids)
        with connection.cursor() as cursor:
            cursor.execute("select id from eval_protocols where name = %s", (args.name,))
            (protocol_id,) = cursor.fetchone()
        print(f"created protocol {protocol_id}: {args.name!r}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
