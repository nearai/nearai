import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union

import backoff
import fire
import pymysql

from nearai.config import CONFIG

# TODO: Once everyone is using the new version of nearai, we can rename this table to `registry`
#       and rename the old `registry` table to `registry_old` (and later remove it).
#       When the new table is renamed, users will be prompted to update the CLI automatically.
REGISTRY_TABLE = "registry_v2"


def check_renamed_table(fn: Any) -> Any:
    def gn(*args: Any, **kwargs: Any) -> Any:
        try:
            output = fn(*args, **kwargs)
            return output
        except pymysql.err.ProgrammingError as e:
            if e.args[0] == 1146:
                print(f"Table {REGISTRY_TABLE} not found. Please update the CLI to the latest version.")
            raise

    return gn


def datetime_serializer(obj: Any) -> Union[str, datetime]:
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
    def from_db(row: Any) -> "Experiment":  # noqa: D102
        return Experiment(*row)

    @staticmethod
    def try_from_db(row: Any) -> Optional["Experiment"]:  # noqa: D102
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
    def from_db(row: Any) -> "Supervisor":  # noqa: D102
        return Supervisor(*row)

    @staticmethod
    def try_from_db(row: Any) -> Optional["Supervisor"]:  # noqa: D102
        if row is None:
            return None
        return Supervisor.from_db(row)


@dataclass
class Log:
    id: int
    origin: str
    time: datetime
    target: str
    content: str

    @staticmethod
    def from_db(row: Any) -> "Log":  # noqa: D102
        return Log(*row)

    @staticmethod
    def try_from_db(row: Any) -> Optional["Log"]:  # noqa: D102
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
    def from_db(row: Any) -> Optional["RegistryEntry"]:  # noqa: D102
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
    def prepare_display_registry_entries_from_db(rows: Tuple[Tuple[Any, ...], ...]) -> List["DisplayRegistry"]:  # noqa: D102
        entries: Dict[int, DisplayRegistry] = {}
        for id, path, name, author, time, description, tag in rows:
            if id not in entries:
                entries[id] = DisplayRegistry(id, path, name, author, time, description, [])
            entries[id].tags.append(tag)
        return sorted(entries.values(), key=lambda x: -x.id)


@dataclass
class Tag:
    id: int
    registry_id: int
    tag: str

    @staticmethod
    def from_db(row: Any) -> Optional["Tag"]:  # noqa: D102
        if row is None:
            return None

        return Tag(*row)


class DB:
    def __init__(self, *, host: str, port: int, user: Optional[str], password: Optional[str], database: str):  # noqa: D107
        self.kwargs = dict(host=host, port=port, user=user, password=password, database=database)
        self._connection = pymysql.connect(**self.kwargs)

    @property
    def connection(self) -> pymysql.Connection:  # noqa: D102
        try:
            self._connection.ping(reconnect=True)
        except pymysql.err.OperationalError:
            self._connection = pymysql.connect(**self.kwargs)
        return self._connection

    def close(self) -> None:  # noqa: D102
        self.connection.close()

    def log(self, *, origin: str, target: str, content: Dict[Any, Any]) -> None:  # noqa: D102
        content_str = json.dumps(content, default=datetime_serializer)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (origin, target, content) VALUES (%s, %s, %s)",
                (origin, target, content_str),
            )
        self.connection.commit()

    def add_experiment(  # noqa: D102
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
                "INSERT INTO experiments (name, author, repository, commit, diff, command, num_nodes, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",  # noqa: E501
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
            return int(cursor.lastrowid)

    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM experiments WHERE id=%s LIMIT 1", (experiment_id,))
            return Experiment.from_db(cursor.fetchone())

    def get_assignment(self, supervisor_id: str) -> Optional[Experiment]:  # noqa: D102
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

    def last_experiments(self, total: int) -> List[Experiment]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT %s", (total,))
            return [Experiment.from_db(row) for row in cursor.fetchall()]

    def available_supervisors(self, total: int = 1) -> List[Supervisor]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM supervisors WHERE available=1 LIMIT %s", (total,))
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def add_supervisors(self, supervisors: List[Supervisor]) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            supervisors_d = [(s.id, s.endpoint, s.cluster, s.status) for s in supervisors]
            cursor.executemany(
                "INSERT IGNORE INTO supervisors (id, endpoint, cluster, status) VALUES (%s, %s, %s, %s)",
                supervisors_d,
            )
        self.connection.commit()

    def num_nodes(self, experiment_id: int) -> int:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT num_nodes FROM experiments WHERE id=%s LIMIT 1",
                (experiment_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    def set_experiment_status(self, *, experiment_id: Union[str, int], status: str) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE experiments SET status=%s WHERE id=%s", (status, str(experiment_id)))
        self.connection.commit()

    def set_supervisor_status(self, *, supervisor_id: str, status: str) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE supervisors SET status=%s WHERE id=%s",
                (status, supervisor_id),
            )
        self.connection.commit()

    def get_assigned_supervisors(self, experiment_id: int) -> List[Supervisor]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM supervisors WHERE experiment_id=%s AND status='assigned' ORDER BY id",
                (experiment_id,),
            )
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def set_all_supervisors_unavailable(self) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE supervisors SET status='unavailable' WHERE status='available'")
        self.connection.commit()

    @backoff.on_predicate(backoff.expo, lambda x: x is None, max_tries=7)
    def lock_supervisors(self, *, experiment_id: int, total: int, cluster: str) -> Optional[List[Supervisor]]:  # noqa: D102
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
                "UPDATE supervisors SET experiment_id=%s, status='preassigned' WHERE status='available' AND cluster=%s AND id <= %s",  # noqa: E501
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
    def exists_in_registry(self, path: str) -> bool:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {REGISTRY_TABLE} WHERE path=%s",
                (path,),
            )
            return cursor.fetchone() is not None

    @check_renamed_table
    def update_registry_entry(  # noqa: D102
        self,
        *,
        id: int,
        author: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ) -> None:
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
    def add_to_registry(  # noqa: D102
        self,
        *,
        s3_path: str,
        name: str,
        author: str,
        description: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: bool = True,
        tags: Optional[List[str]] = None,
    ) -> int:
        if tags is None:
            tags = []
        with self.connection.cursor() as cursor:
            details = details or {}
            cursor.execute(
                f"INSERT INTO {REGISTRY_TABLE} (path, name, author, description, details, show_entry) VALUES (%s, %s, %s, %s, %s, %s)",  # noqa: E501
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
        return int(registry_id)

    @check_renamed_table
    def list_registry_entries(self, *, total: int, show_all: bool, tags: List[str]) -> List[DisplayRegistry]:  # noqa: D102
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
                """,  # noqa: E501
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
                """,  # noqa: E501
                    (show_all_int, *tags, total),
                )

            return DisplayRegistry.prepare_display_registry_entries_from_db(cursor.fetchall())

    @check_renamed_table
    def get_registry_entry_by_path(self, path: str) -> Optional[RegistryEntry]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {REGISTRY_TABLE} WHERE path=%s ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1", (path,)
            )
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_name(self, name: str, version: Optional[str] = None) -> Optional[RegistryEntry]:
        """Retrieves registry item by name and version if provided."""
        with self.connection.cursor() as cursor:
            if not version:
                cursor.execute(
                    f"SELECT * FROM {REGISTRY_TABLE} WHERE name=%s ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1", (name,)
                )
            else:
                print(
                    "SELECT * FROM {REGISTRY_TABLE} WHERE name='%s' AND {REGISTRY_TABLE}.path LIKE '%%/v%s' ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1"  # noqa: E501
                    % (name, version)
                )
                cursor.execute(
                    f"SELECT * FROM {REGISTRY_TABLE} WHERE name=%s AND {REGISTRY_TABLE}.path LIKE '%%%s' ORDER BY {REGISTRY_TABLE}.id DESC LIMIT 1",  # noqa: E501
                    (name, version),
                )
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_id(self, id: int) -> Optional[RegistryEntry]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {REGISTRY_TABLE} WHERE id=%s LIMIT 1", (id,))
            result = cursor.fetchone()
            if not result:
                return None
            return RegistryEntry.from_db(result)

    def get_registry_entry_by_identifier(  # noqa: D102
        self, identifier: Union[str, int], version: Optional[str] = None, fail_if_not_found: bool = True
    ) -> Optional[RegistryEntry]:
        try:
            identifier = int(identifier)
            entry = self.get_registry_entry_by_id(identifier)
        except ValueError:
            for get_fn in (self.get_registry_entry_by_name, self.get_registry_entry_by_path):
                entry = get_fn(str(identifier), version=version)
                if entry:
                    break

        if entry is None and fail_if_not_found:
            raise ValueError(f"{identifier} not found in the registry")

        return entry

    def get_benchmark_id(self, dataset: str, strategy: str, force: bool, **kwargs: Any) -> int:  # noqa: D102
        # Sorted arguments to ensure consistency
        args = json.dumps(OrderedDict(sorted(kwargs.items())))

        # Check if exists
        if not force:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM benchmark WHERE name=%s AND solver=%s AND args=%s ORDER BY id DESC LIMIT 1",
                    (dataset, strategy, args),
                )
                row = cursor.fetchone()

                if row is not None:
                    return int(row[0])

        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO benchmark (name, solver, args) VALUES (%s, %s, %s)", (dataset, strategy, args))
            return int(cursor.lastrowid)

    def get_benchmark_results(self, benchmark_id: int) -> Dict[int, Tuple[bool, str]]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT dataset_index, result, info FROM benchmark_datum WHERE benchmark_id=%s", (benchmark_id,)
            )
            return {index: (result, info) for index, result, info in cursor.fetchall()}

    def get_benchmark_status(self, benchmark_id: int) -> Dict[int, bool]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT dataset_index, result FROM benchmark_datum WHERE benchmark_id=%s", (benchmark_id,))
            return dict(cursor.fetchall())

    def update_benchmark_result(self, benchmark_id: int, index: int, result: bool, info: str) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO benchmark_datum (benchmark_id, dataset_index, result, info) VALUES (%s, %s, %s, %s)",
                (benchmark_id, index, result, info),
            )
        self.connection.commit()

    def add_tag(self, *, registry_id: int, tag: str) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO tags (registry_id, tag) VALUES (%s, %s)", (registry_id, tag))
        self.connection.commit()

    def remove_tag(self, *, registry_id: int, tag: str) -> None:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM tags WHERE registry_id=%s AND tag=%s", (registry_id, tag))
        self.connection.commit()

    def get_tags(self, registry_id: int) -> List[str]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT tag FROM tags WHERE registry_id=%s", (registry_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_logs(self, target: str, start_id: int, limit: int) -> List[Log]:  # noqa: D102
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM logs WHERE target=%s AND id >= %s ORDER BY id ASC LIMIT %s",
                (target, start_id, limit),
            )
            return [Log.from_db(row) for row in cursor.fetchall()]

    def _create(self) -> None:
        """Create tables if they don't exist."""
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

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS benchmark(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    solver VARCHAR(255) NOT NULL,
                    args TEXT NOT NULL
                )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS benchmark_datum(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    benchmark_id INT NOT NULL,
                    dataset_index INT NOT NULL,
                    result BOOLEAN NOT NULL,
                    info TEXT
                )"""
            )

        self.connection.commit()

    def _check_all(self) -> None:
        """Check all tables."""
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


T = TypeVar("T")


class LazyObject(Generic[T]):
    def __init__(self, ctor: Callable[..., T], *args: Any, **kwargs: Any) -> None:  # noqa: D107
        self._initialized = False
        self._obj: T | None = None
        self._ctor = partial(ctor, *args, **kwargs)

    def _init(self) -> None:
        if self._initialized:
            return
        self._obj = self._ctor()
        self._initialized = True

    def __getattr__(self, name: str) -> Any:  # noqa: D105
        self._init()
        assert self._obj is not None  # This assertion helps type checking
        return getattr(self._obj, name)


db: LazyObject[DB] = LazyObject(connect)


class CLI:
    def create(self) -> None:  # noqa: D102
        db._create()

    def ping(self) -> None:  # noqa: D102
        db.log(origin="test", target="test", content={"content": "this is a test"})

    def test(self) -> None:  # noqa: D102
        show_all = True
        total = 5
        tags = ("datasets",)

        with db.connection.cursor() as cursor:
            show_all_next = 1 - int(show_all)

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
                """,  # noqa: E501
                (show_all_next, *tags, total),
            )

            for x in cursor.fetchall():
                print(x)


if __name__ == "__main__":
    fire.Fire(CLI)
