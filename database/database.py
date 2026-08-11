import sqlite3
from datetime import datetime
from pathlib import Path

from models import (
    Position,
    PositionSource,
    TideEvent,
    TideEventType,
    TidePoint,
)

from .schema import CREATE_TABLES_SQL, SCHEMA_VERSION


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "marine.db"
)


class MarineDatabase:
    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
    ) -> None:
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA busy_timeout = 5000"
        )

        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

            connection.execute(
                "PRAGMA synchronous = NORMAL"
            )

            connection.executescript(
                CREATE_TABLES_SQL
            )

            connection.execute(
                """
                INSERT INTO metadata (key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (str(SCHEMA_VERSION),),
            )

    # -------------------------------------------------------------------------
    # POSITIONS
    # -------------------------------------------------------------------------

    def insert_position(
        self,
        position: Position,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO positions (
                    timestamp,
                    latitude,
                    longitude,
                    source,
                    valid,
                    speed_knots,
                    course_deg,
                    altitude_m
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.timestamp.isoformat(),
                    position.latitude,
                    position.longitude,
                    position.source.value,
                    int(position.valid),
                    position.speed_knots,
                    position.course_deg,
                    position.altitude_m,
                ),
            )

            if cursor.lastrowid is None:
                raise RuntimeError(
                    "Impossible de récupérer "
                    "l'identifiant de la position."
                )

            return int(cursor.lastrowid)

    def get_latest_position(
        self,
    ) -> Position | None:
        """
        Retourne la dernière position enregistrée,
        valide ou non.
        """

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    timestamp,
                    latitude,
                    longitude,
                    source,
                    valid,
                    speed_knots,
                    course_deg,
                    altitude_m
                FROM positions
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()

        return self._row_to_position(
            row
        )

    def get_latest_valid_position(
        self,
    ) -> Position | None:
        """
        Retourne la dernière position valide.
        """

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    timestamp,
                    latitude,
                    longitude,
                    source,
                    valid,
                    speed_knots,
                    course_deg,
                    altitude_m
                FROM positions
                WHERE valid = 1
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()

        return self._row_to_position(
            row
        )

    @staticmethod
    def _row_to_position(
        row: sqlite3.Row | None,
    ) -> Position | None:
        if row is None:
            return None

        return Position(
            latitude=row["latitude"],
            longitude=row["longitude"],
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            source=PositionSource(
                row["source"]
            ),
            valid=bool(
                row["valid"]
            ),
            speed_knots=row["speed_knots"],
            course_deg=row["course_deg"],
            altitude_m=row["altitude_m"],
        )

    def clear_positions(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM positions"
            )

    # -------------------------------------------------------------------------
    # TIDE POINTS
    # -------------------------------------------------------------------------

    def upsert_tide_points(
        self,
        points: list[TidePoint],
    ) -> int:
        """
        Insère ou met à jour des hauteurs de marée.
        """

        if not points:
            return 0

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO tide_points (
                    target_id,
                    timestamp,
                    height_m
                )
                VALUES (?, ?, ?)

                ON CONFLICT(
                    target_id,
                    timestamp
                )
                DO UPDATE SET
                    height_m = excluded.height_m
                """,
                [
                    (
                        point.station_id,
                        point.timestamp.isoformat(),
                        point.height_m,
                    )
                    for point in points
                ],
            )

        return len(points)

    def get_tide_points(
        self,
        target_id: str,
        start: datetime,
        end: datetime,
    ) -> list[TidePoint]:
        """
        Retourne les hauteurs de marée
        comprises entre start et end.
        """

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    target_id,
                    timestamp,
                    height_m
                FROM tide_points

                WHERE target_id = ?
                  AND timestamp >= ?
                  AND timestamp < ?

                ORDER BY timestamp ASC
                """,
                (
                    target_id,
                    start.isoformat(),
                    end.isoformat(),
                ),
            ).fetchall()

        return [
            TidePoint(
                timestamp=datetime.fromisoformat(
                    row["timestamp"]
                ),
                height_m=row["height_m"],
                station_id=row["target_id"],
            )
            for row in rows
        ]

    # -------------------------------------------------------------------------
    # TIDE EVENTS
    # -------------------------------------------------------------------------

    def upsert_tide_events(
        self,
        events: list[TideEvent],
    ) -> int:
        """
        Insère ou met à jour les événements
        de pleine et basse mer.
        """

        if not events:
            return 0

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO tide_events (
                    target_id,
                    timestamp,
                    event_type,
                    height_m,
                    coefficient
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(
                    target_id,
                    timestamp,
                    event_type
                )
                DO UPDATE SET
                    height_m = excluded.height_m,
                    coefficient = excluded.coefficient
                """,
                [
                    (
                        event.station_id,
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.height_m,
                        event.coefficient,
                    )
                    for event in events
                ],
            )

        return len(events)

    def get_tide_events(
        self,
        target_id: str,
        start: datetime,
        end: datetime,
    ) -> list[TideEvent]:
        """
        Retourne les événements de marée
        compris entre start et end.
        """

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    target_id,
                    timestamp,
                    event_type,
                    height_m,
                    coefficient
                FROM tide_events

                WHERE target_id = ?
                  AND timestamp >= ?
                  AND timestamp < ?

                ORDER BY timestamp ASC
                """,
                (
                    target_id,
                    start.isoformat(),
                    end.isoformat(),
                ),
            ).fetchall()

        return [
            TideEvent(
                timestamp=datetime.fromisoformat(
                    row["timestamp"]
                ),
                event_type=TideEventType(
                    row["event_type"]
                ),
                height_m=row["height_m"],
                station_id=row["target_id"],
                coefficient=row["coefficient"],
            )
            for row in rows
        ]

    # -------------------------------------------------------------------------
    # TIDE CLEANUP
    # -------------------------------------------------------------------------

    def clear_tides(
        self,
        target_id: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """
        Supprime les données de marée
        d'une cible sur un intervalle donné.
        """

        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM tide_points

                WHERE target_id = ?
                  AND timestamp >= ?
                  AND timestamp < ?
                """,
                (
                    target_id,
                    start.isoformat(),
                    end.isoformat(),
                ),
            )

            connection.execute(
                """
                DELETE FROM tide_events

                WHERE target_id = ?
                  AND timestamp >= ?
                  AND timestamp < ?
                """,
                (
                    target_id,
                    start.isoformat(),
                    end.isoformat(),
                ),
            )

    def get_tide_point_before(
            self,
            target_id: str,
            timestamp: datetime,
    ) -> TidePoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    target_id,
                    timestamp,
                    height_m

                FROM tide_points

                WHERE target_id = ?
                  AND timestamp <= ?

                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (
                    target_id,
                    timestamp.isoformat(),
                ),
            ).fetchone()

        if row is None:
            return None

        return TidePoint(
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            height_m=row["height_m"],
            station_id=row["target_id"],
        )

    def get_tide_point_after(
            self,
            target_id: str,
            timestamp: datetime,
    ) -> TidePoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    target_id,
                    timestamp,
                    height_m

                FROM tide_points

                WHERE target_id = ?
                  AND timestamp >= ?

                ORDER BY timestamp ASC
                LIMIT 1
                """,
                (
                    target_id,
                    timestamp.isoformat(),
                ),
            ).fetchone()

        if row is None:
            return None

        return TidePoint(
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            height_m=row["height_m"],
            station_id=row["target_id"],
        )

    def get_next_tide_event(
            self,
            target_id: str,
            timestamp: datetime,
            event_type: TideEventType,
    ) -> TideEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    target_id,
                    timestamp,
                    event_type,
                    height_m,
                    coefficient

                FROM tide_events

                WHERE target_id = ?
                  AND timestamp >= ?
                  AND event_type = ?

                ORDER BY timestamp ASC
                LIMIT 1
                """,
                (
                    target_id,
                    timestamp.isoformat(),
                    event_type.value,
                ),
            ).fetchone()

        if row is None:
            return None

        return TideEvent(
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            event_type=TideEventType(
                row["event_type"]
            ),
            height_m=row["height_m"],
            station_id=row["target_id"],
            coefficient=row["coefficient"],
        )

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    def get_schema_version(
        self,
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT value
                FROM metadata
                WHERE key = 'schema_version'
                """
            ).fetchone()

        if row is None:
            return 0

        return int(
            row["value"]
        )