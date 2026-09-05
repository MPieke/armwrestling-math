"""Grow a prospective lockbox with one explicitly selected event."""

from __future__ import annotations

import argparse
import json

import psycopg

from prediction import db


def add_prospective_event(
    connection: psycopg.Connection, protocol_name: str, event_slug: str
) -> list[int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select p.id, p.kind, p.spec, f.test_match_ids
            from eval_protocols p
            join eval_folds f on f.protocol_id = p.id and f.fold_index = 0
            where p.name = %s
            for update of p, f
            """,
            (protocol_name,),
        )
        protocol = cursor.fetchone()
        if protocol is None:
            raise ValueError(f"protocol {protocol_name!r} does not exist or has no single fold")
        protocol_id, kind, spec, current_match_ids = protocol
        if kind != "lockbox_prospective":
            raise ValueError(f"protocol {protocol_name!r} is not prospective")

        cursor.execute("select id from events where slug = %s", (event_slug,))
        event = cursor.fetchone()
        if event is None:
            raise ValueError(f"event {event_slug!r} does not exist")
        cursor.execute("select id from matches where event_id = %s order by id", (event[0],))
        event_match_ids = [row[0] for row in cursor.fetchall()]
        added_match_ids = [
            match_id for match_id in event_match_ids if match_id not in current_match_ids
        ]
        if added_match_ids:
            cursor.execute(
                "update eval_folds set test_match_ids = %s where protocol_id = %s and fold_index = 0",
                (current_match_ids + added_match_ids, protocol_id),
            )
        event_slugs = list(spec.get("event_slugs", []))
        event_ids = list(spec.get("event_ids", []))
        if event_slug not in event_slugs:
            event_slugs.append(event_slug)
            event_ids.append(event[0])
            spec["event_slugs"] = event_slugs
            spec["event_ids"] = event_ids
            cursor.execute(
                "update eval_protocols set spec = %s where id = %s",
                (json.dumps(spec), protocol_id),
            )
    return added_match_ids


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Append an event to a prospective lockbox.")
    parser.add_argument("--protocol-name", required=True)
    parser.add_argument("--event-slug", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    connection = db.connect()
    try:
        added_ids = add_prospective_event(connection, args.protocol_name, args.event_slug)
        if args.dry_run:
            connection.rollback()
            print(f"validated protocol update; would add match ids {added_ids}; no changes written")
        else:
            connection.commit()
            print(f"protocol {args.protocol_name!r}: added match ids {added_ids}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
