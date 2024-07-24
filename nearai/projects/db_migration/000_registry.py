"""
Move all elements from registry to registry_v2 using the new convention.
Instead of using the category column, use the tag system.
"""

import json
from typing import List, Tuple

from nearai.db import RegistryEntry, db


def migrate():

    # Get all registry entries that are not hidden
    with db.connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM registry WHERE show_entry=1")

        entries: List[Tuple[RegistryEntry, str]] = []
        for row in cursor.fetchall():
            _, s3_path, category, author, time, description, name, details, show_entry = row

            entry = RegistryEntry(
                id=0,
                path=s3_path,
                name=name,
                author=author,
                time=time,
                description=description,
                details=json.loads(details),
                show_entry=show_entry,
            )

            entries.append((entry, category))

    for entry, category in entries:
        print()
        print(entry)

        if db.get_registry_entry_by_path(entry.path) is not None:
            print()
            print(f"Ignore {entry.path}. Already exists in registry_v2")
            continue

        with db.connection.cursor() as cursor:
            details = entry.details or {}
            cursor.execute(
                f"INSERT INTO registry_v2 (path, name, author, time, description, details, show_entry) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    entry.path,
                    entry.name,
                    entry.author,
                    str(entry.time),
                    entry.description,
                    json.dumps(details),
                    1,
                ),
            )

            last_row_id = cursor.lastrowid

        db.add_tag(registry_id=last_row_id, tag=category)

    db.connection.commit()


if __name__ == "__main__":
    migrate()
