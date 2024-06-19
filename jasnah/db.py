import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import backoff
import fire
import pymysql

from jasnah.config import CONFIG

# TODO: Once everyone is using the new version of jasnah-cli, we can rename this table to `registry`
#       and rename the old `registry` table to `registry_old` (and later remove it).
#       When the new table is renamed, users will be prompted to update the CLI automatically.
REGISTRY_TABLE = "registry_v2"


def check_renamed_table(fn):
    def gn(*args, **kwargs):
        try:
            output = fn(*args, **kwargs)
            return output
        except pymysql.err.ProgrammingError as e:
            if e.args[0] == 1146:
                print(f"Table {REGISTRY_TABLE} not found. Please update the CLI to the latest version.")
            raise

    return gn


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@dataclass
class Experiment:
    id: int
    name: str
    author: str
    time: datetime
    repository: str
    commit: str
    diff: Optional[str]
    command: str
    num_nodes: int = 1
    status: str = "pending"

    @staticmethod
    def from_db(row) -> "Experiment":
        return Experiment(*row)

    @staticmethod
    def try_from_db(row) -> Optional["Experiment"]:
        if row is None:
            return None
        return Experiment.from_db(row)


@dataclass
class Supervisor:
    id: str
    experiment_id: int
    cluster: str
    endpoint: str
    status: str

    @staticmethod
    def from_db(row) -> "Supervisor":
        return Supervisor(*row)

    @staticmethod
    def try_from_db(row) -> Optional["Supervisor"]:
        if row is None:
            return None
        return Supervisor.from_db(row)


@dataclass
class Log:
    id: int
    origin: str
    time: datetime
    content: str

    @staticmethod
    def from_db(row) -> "Log":
        return Log(*row)

    @staticmethod
    def try_from_db(row) -> Optional["Log"]:
        if row is None:
            return None
        return Log.from_db(row)


@dataclass
class RegistryEntry:
    id: int
    path: str
    name: str
    author: str
    time: datetime
    description: Optional[str]
    details: Optional[dict]
    show_entry: bool

    @staticmethod
    def from_db(row) -> Optional["RegistryEntry"]:
        if row is None:
            return None

        entry = RegistryEntry(*row)

        if entry.details is not None:
            entry.details = json.loads(str(entry.details))

        return entry


@dataclass
class DisplayRegistry:
    id: int
    path: str
    name: str
    author: str
    time: datetime
    description: Optional[str]
    tags: List[str]

    @staticmethod
    def prepare_display_registry_entries_from_db(rows: Tuple[Tuple[Any, ...], ...]) -> List["DisplayRegistry"]:
        entries: Dict[int, DisplayRegistry] = {}
        for id, path, name, author, time, description, tag in rows:
            if not id in entries:
                entries[id] = DisplayRegistry(id, path, name, author, time, description, [])
            entries[id].tags.append(tag)
        return sorted(entries.values(), key=lambda x: -x.id)


@dataclass
class Tag:
    id: int
    registry_id: int
    tag: str

    @staticmethod
    def from_db(row) -> Optional["Tag"]:
        if row is None:
            return None

        return Tag(*row)


class DB:
    def __init__(self, *, host, port, user, password, database):
        self._connection = pymysql.connect(host=host, port=port, user=user, password=password, database=database)

    @property
    def connection(self):
        self._connection.ping(reconnect=True)
        return self._connection

    def close(self):
        self.connection.close()

    def log(self, *, origin: str, target: str, content: Dict[Any, Any]):
        content_str = json.dumps(content, default=datetime_serializer)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (origin, target, content) VALUES (%s, %s, %s)",
                (origin, target, content_str),
            )
        self.connection.commit()

    def add_experiment(
        self,
        *,
        name: str,
        author: str,
        repository: str,
        commit: str,
        diff: Optional[str],
        command: str,
        num_nodes: int,
    ) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO experiments (name, author, repository, commit, diff, command, num_nodes, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    name,
                    author,
                    repository,
                    commit,
                    diff,
                    command,
                    num_nodes,
                    "pending",
                ),
            )
            self.connection.commit()
            return cursor.lastrowid

    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM experiments WHERE id=%s LIMIT 1", (experiment_id,))
            return Experiment.from_db(cursor.fetchone())

    def get_assignment(self, supervisor_id: str) -> Optional[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT experiment_id FROM supervisors WHERE id=%s AND status='assigned'",
                (supervisor_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            experiment_id = row[0]

            cursor.execute("SELECT * FROM experiments WHERE id=%s LIMIT 1", (experiment_id,))

            return Experiment.from_db(cursor.fetchone())

    def last_experiments(self, total: int) -> List[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT %s", (total,))
            return [Experiment.from_db(row) for row in cursor.fetchall()]

    def available_supervisors(self, total: int = 1) -> List[Supervisor]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM supervisors WHERE available=1 LIMIT %s", (total,))
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def add_supervisors(self, supervisors: List[Supervisor]):
        with self.connection.cursor() as cursor:
            supervisors_d = [(s.id, s.endpoint, s.cluster, s.status) for s in supervisors]
            cursor.executemany(
                "INSERT IGNORE INTO supervisors (id, endpoint, cluster, status) VALUES (%s, %s, %s, %s)",
                supervisors_d,
            )
        self.connection.commit()

    def num_nodes(self, experiment_id) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT num_nodes FROM experiments WHERE id=%s LIMIT 1",
                (experiment_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    def set_experiment_status(self, *, experiment_id: Union[str, int], status: str):
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE experiments SET status=%s WHERE id=%s", (status, str(experiment_id)))
        self.connection.commit()

    def set_supervisor_status(self, *, supervisor_id: str, status: str):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE supervisors SET status=%s WHERE id=%s",
                (status, supervisor_id),
            )
        self.connection.commit()

    def get_assigned_supervisors(self, experiment_id: int) -> List[Supervisor]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM supervisors WHERE experiment_id=%s AND status='assigned' ORDER BY id",
                (experiment_id,),
            )
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def set_all_supervisors_unavailable(self):
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE supervisors SET status='unavailable' WHERE status='available'")
        self.connection.commit()

    @backoff.on_predicate(backoff.expo, lambda x: x is None, max_tries=7)
    def lock_supervisors(self, *, experiment_id: int, total: int, cluster: str) -> Optional[List[Supervisor]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM supervisors WHERE status='available' AND cluster=%s ORDER BY id LIMIT %s OFFSET %s",
                (cluster, 1, total - 1),
            )
            result = cursor.fetchone()

            if result is None:
                # There are not enough supervisors. Don't backoff
                return []

            supervisor_id = result[0]

            cursor.execute(
                "UPDATE supervisors SET experiment_id=%s, status='preassigned' WHERE status='available' AND cluster=%s AND id <= %s",
                (
                    experiment_id,
                    cluster,
                    supervisor_id,
                ),
            )

            self.connection.commit()

            cursor.execute(
                "SELECT * FROM supervisors WHERE experiment_id=%s AND status='preassigned'",
                (experiment_id,),
            )

            selected = cursor.fetchall()

            if len(selected) == total:
                cursor.execute(
                    "UPDATE supervisors SET status='assigned' WHERE experiment_id=%s",
                    (experiment_id,),
                )
                self.connection.commit()
                return [Supervisor.from_db(row) for row in selected]

            else:
                cursor.execute(
                    "UPDATE supervisors SET status='available' WHERE experiment_id=%s",
                    (experiment_id,),
                )
                self.connection.commit()
                return None

    @check_renamed_table
    def exists_in_registry(self, path: str) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {REGISTRY_TABLE} WHERE path=%s",
                (path,),
            )
            return cursor.fetchone() is not None

    @check_renamed_table
    def update_registry_entry(
        self,
        *,
        id: int,
        author: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ):
        new_values = dict(
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
        )

        with self.connection.cursor() as cursor:
            for key, value in new_values.items():
                if value is None:
                    continue

                if key == "details":
                    value = json.dumps(value)

                cursor.execute(f"UPDATE {REGISTRY_TABLE} SET {key}=%s WHERE id=%s", (value, id))

            self.connection.commit()

    @check_renamed_table
    def add_to_registry(
        self,
        *,
        s3_path: str,
        name: str,
        author: str,
        description: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: bool = True,
        tags: List[str] = [],
    ):
        with self.connection.cursor() as cursor:
            details = details or {}
            cursor.execute(
                f"INSERT INTO {REGISTRY_TABLE} (path, name, author, description, details, show_entry) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    s3_path,
                    name,
                    author,
                    description,
                    json.dumps(details),
                    show_entry,
                ),
            )

            registry_id = cursor.lastrowid

        self.connection.commit()

        for tag in tags:
            self.add_tag(registry_id=registry_id, tag=tag)

    @check_renamed_table
    def list_registry_entries(self, *, total: int, show_all: bool, tags: List[str]) -> List[DisplayRegistry]:
        with self.connection.cursor() as cursor:
            show_all_int = 1 - int(show_all)

            if len(tags) == 0:
                cursor.execute(
                    f"""WITH FilteredRegistry AS (
                    SELECT registry.id FROM {REGISTRY_TABLE} registry
                    WHERE show_entry >= %s
                    ORDER BY registry.id DESC
                    LIMIT %s)

                    SELECT registry.id, registry.path, registry.name, registry.author, registry.time, registry.description, tags.tag FROM FilteredRegistry filtered
                    JOIN {REGISTRY_TABLE} registry ON filtered.id = registry.id
                    JOIN tags ON registry.id = tags.registry_id
                    ORDER BY registry.id DESC
                """,
                    (show_all_int, total),
                )
            else:
                cursor.execute(
                    f"""WITH FilteredRegistry AS (
                    SELECT registry.id FROM {REGISTRY_TABLE} registry
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE show_entry >= %s AND tags.tag IN ({','.join(['%s']*len(tags))})
                    GROUP BY registry.id
                    HAVING COUNT(DISTINCT tags.tag) = {len(tags)}
                    ),
                    RankedRegistry AS (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS rank
                        FROM FilteredRegistry
                    )

                    SELECT registry.id, registry.path, registry.name, registry.author, registry.time, registry.description, tags.tag FROM RankedRegistry ranked
                    JOIN {REGISTRY_TABLE} registry ON ranked.id = registry.id
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE ranked.rank <= %s
                    ORDER BY registry.id DESC
                """,
                    (show_all_int, *tags, total),
                )

            return DisplayRegistry.prepare_display_registry_entries_from_db(cursor.fetchall())

    @check_renamed_table
    def get_registry_entry_by_path(self, path: str, version = None) -> Optional[RegistryEntry]:
        assert version != None, "Can not select version when path provided"
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {REGISTRY_TABLE} WHERE path=%s ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1", (path,))
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_name(self, name: str, version: Optional[str] = None) -> Optional[RegistryEntry]:
        """Retrieves restriy item by name and version if provided."""
        with self.connection.cursor() as cursor:
            if not version:
                cursor.execute(f"SELECT * FROM {REGISTRY_TABLE} WHERE name=%s ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1", (name,))
            else:
                print("SELECT * FROM {REGISTRY_TABLE} WHERE name='%s' AND {REGISTRY_TABLE}.path LIKE '%%/v%s' ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1" % (name, version))
                cursor.execute(f"SELECT * FROM {REGISTRY_TABLE} WHERE name=%s AND {REGISTRY_TABLE}.path LIKE '%%%s' ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1", (name, version))
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_id(self, id: int) -> Optional[RegistryEntry]:
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {REGISTRY_TABLE} WHERE id=%s LIMIT 1", (id,))
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_identifier(
        self, identifier: Union[str, int], version: Optional[str] = None, fail_if_not_found=True
    ) -> Optional[RegistryEntry]:
        try:
            identifier = int(identifier)
            entry = self.get_registry_entry_by_id(identifier)
        except ValueError:
            for get_fn in (self.get_registry_entry_by_name, self.get_registry_entry_by_path):
                entry = get_fn(identifier, version=version)
                if entry:
                    break

        if entry is None and fail_if_not_found:
            raise ValueError(f"{identifier} not found in the registry")

        return entry

    def add_tag(self, *, registry_id: int, tag: str):
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO tags (registry_id, tag) VALUES (%s, %s)", (registry_id, tag))
        self.connection.commit()

    def remove_tag(self, *, registry_id: int, tag: str):
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM tags WHERE registry_id=%s AND tag=%s", (registry_id, tag))
        self.connection.commit()

    def get_tags(self, registry_id: int) -> List[str]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT tag FROM tags WHERE registry_id=%s", (registry_id,))
            return [row[0] for row in cursor.fetchall()]

    def _create(self):
        """Create tables if they don't exist"""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS supervisors(
                            id VARCHAR(255) NOT NULL PRIMARY KEY,
                            experiment_id INT,
                            cluster VARCHAR(255) NOT NULL,
                            endpoint VARCHAR(255) NOT NULL,
                            status VARCHAR(255) NOT NULL
                            )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS experiments(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            author VARCHAR(255) NOT NULL,
                            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            repository VARCHAR(255) NOT NULL,
                            commit VARCHAR(255) NOT NULL,
                            diff TEXT,
                            command TEXT NOT NULL,
                            num_nodes INT NOT NULL,
                            status VARCHAR(255) NOT NULL
                            )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS logs(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            origin VARCHAR(255) NOT NULL,
                            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            target VARCHAR(255) NOT NULL,
                            content JSON NOT NULL
                            )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS registry(
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        category VARCHAR(255) NOT NULL,
                        author VARCHAR(255) NOT NULL,
                        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT,
                        alias VARCHAR(255),
                        details JSON,
                        show_entry BOOLEAN NOT NULL DEFAULT TRUE
                        )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS registry_v2(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    path VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    author VARCHAR(255) NOT NULL,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    details JSON,
                    show_entry BOOLEAN NOT NULL DEFAULT TRUE
                )
                """
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS tags(
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        registry_id INT NOT NULL,
                        tag VARCHAR(255) NOT NULL
                        )"""
            )

        self.connection.commit()

    def _check_all(self):
        """Check all tables"""
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM supervisors LIMIT 16")
            print("\nSupervisors:")
            for supervisor in map(Supervisor.from_db, cursor.fetchall()):
                print(supervisor)

            print("\nExperiments:")
            cursor.execute("SELECT * FROM experiments LIMIT 16")
            for experiment in map(Experiment.from_db, cursor.fetchall()):
                print(experiment)

            print("\nLogs:")
            cursor.execute("SELECT * FROM logs LIMIT 16")
            for log in map(Log.from_db, cursor.fetchall()):
                print(log)
            print()


def connect() -> "DB":
    return DB(
        host=CONFIG.db_host,
        port=CONFIG.db_port,
        user=CONFIG.db_user,
        password=CONFIG.db_password,
        database=CONFIG.db_name,
    )


# TODO: Move this to a better place. Currently when not configured properly, the CLI will fail to connect to the database.
try:
    db = connect()
except Exception as e:
    print("Could not connect to the database")
    print(e)
    db = None


class CLI:
    def create(self):
        assert db is not None
        db._create()

    def test(self):
        show_all = True
        total = 5
        tags = ("datasets",)

        assert db is not None
        with db.connection.cursor() as cursor:
            show_all = 1 - int(show_all)

            cursor.execute(
                f"""WITH FilteredRegistry AS (
                    SELECT registry.id FROM {REGISTRY_TABLE} registry
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE show_entry >= %s AND tags.tag IN ({','.join(['%s']*len(tags))})
                    GROUP BY registry.id
                    HAVING COUNT(DISTINCT tags.tag) = {len(tags)}
                    ),
                    RankedRegistry AS (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY id DESC) AS rank
                        FROM FilteredRegistry
                    )

                    SELECT registry.id, registry.path, registry.name, registry.author, registry.time, registry.description, tags.tag FROM RankedRegistry ranked
                    JOIN {REGISTRY_TABLE} registry ON ranked.id = registry.id
                    JOIN tags ON registry.id = tags.registry_id
                    WHERE ranked.rank <= %s
                    ORDER BY registry.id DESC
                """,
                (show_all, *tags, total),
            )

            for x in cursor.fetchall():
                print(x)


if __name__ == "__main__":
    fire.Fire(CLI)
