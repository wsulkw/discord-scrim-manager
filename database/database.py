import sqlite3
from typing import Dict, List, Optional

import discord


class Database:
    def __init__(self, db_path: str = "scrim_bot.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scrims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    game_mode TEXT NOT NULL,
                    max_players INTEGER NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    creator_id INTEGER NOT NULL,
                    player_count INTEGER DEFAULT 0,
                    team1_vc_id INTEGER,
                    team2_vc_id INTEGER,
                    category_id INTEGER,
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scrim_players (
                    scrim_id INTEGER,
                    player_id INTEGER,
                    player_name TEXT,
                    team INTEGER,
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (scrim_id, player_id)
                );
            """)

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    # Inserters
    def insert_scrim(self,
                     title: str,
                     game_mode: str,
                     time: str,
                     max_players: int,
                     user: discord.User
                     ) -> int:
        return self.execute_insert("""
            INSERT INTO scrims (title, game_mode, max_players, scheduled_time, creator_id)
            VALUES (?, ?, ?, ?, ?)
            """, (title, game_mode, max_players, time, user.id))

    def insert_scrim_player(self,
                            scrim_id: int,
                            player: discord.User
                            ) -> bool:
        self.update_scrim_player_count(scrim_id, 1)
        return bool(self.execute_insert("""
            INSERT INTO scrim_players (scrim_id, player_id, player_name)
            VALUES (?, ?, ?)
            """, (scrim_id, player.id, player.name)))

    # UPDATERS
    def update_scrim_status(self, scrim_id: int, status: str) -> bool:
        return bool(self.execute_insert("""
            UPDATE scrims
            SET status = ?
            WHERE id = ?
            """, (status, scrim_id)))

    def update_scrim_player_count(self, scrim_id: int, delta: int) -> bool:
        return bool(self.execute_insert("""
            UPDATE scrims
            SET player_count = player_count + ?
            WHERE id = ?
            """, (delta, scrim_id)))

    def update_scrim_channels(self, scrim_id: int, category_id: int, team1_vc_id: int, team2_vc_id: int) -> bool:
        return bool(self.execute_insert("""
            UPDATE scrims
            SET category_id = ?,
                team1_vc_id = ?,
                team2_vc_id = ?
            WHERE id = ?
            """, (category_id, team1_vc_id, team2_vc_id, scrim_id)))

    def update_player_team(self, scrim_id: int, player_id: int, team: int) -> bool:
        return bool(self.execute_insert("""
            UPDATE scrim_players
            SET team = ?
            WHERE (scrim_id = ?) AND (player_id = ?)
            """, (team, scrim_id, player_id,)))

    # DELETERS
    def delete_scrim_player(self, scrim_id: int, player_id: int) -> bool:
        self.update_scrim_player_count(scrim_id, -1)
        return bool(self.execute_insert("""
            DELETE FROM scrim_players 
            WHERE scrim_id = ? AND player_id = ?
            """, (scrim_id, player_id)))

    def delete_old_scrims(self) -> int:
        count_result = self.execute_query("""
            SELECT COUNT(*) as count FROM scrims
            WHERE datetime(created_at) < datetime('now', '-30 days')
            """)

        delete_count = count_result[0]['count'] if count_result else 0

        self.execute_insert("""
                    DELETE FROM scrims
                    WHERE datetime(created_at) < datetime('now', '-30 days')
                    """)

        self.execute_insert("""
            DELETE FROM scrim_players
            WHERE scrim_id NOT IN (SELECT id FROM scrims)
            """)

        return delete_count

    # GETTERS
    def get_scrim_by_id(self, scrim_id: int) -> Optional[Dict]:
        result = self.execute_query("SELECT * FROM scrims WHERE id = ?", (scrim_id,))
        return result[0] if result else None

    def get_scrim_player_count(self, scrim_id: int) -> int:
        return self.get_scrim_by_id(scrim_id)['player_count']

    def get_active_scrims(self) -> List[Dict]:
        return self.execute_query("""
            SELECT * FROM scrims WHERE status IN ('open', 'full', 'active')
            """)

    def get_scrim_players(self, scrim_id: int) -> List[Dict]:
        return self.execute_query("""
                SELECT * FROM scrim_players WHERE (scrim_id = ?)
                """, (scrim_id,))

    def get_scrims_by_user(self, user_id: int) -> List[Dict]:
        return self.execute_query("""
            SELECT * FROM scrim_players WHERE player_id = ?
            """, (user_id,))

    # VALIDATORS
    def is_user_in_scrim(self, scrim_id: int, user_id: int) -> bool:
        return bool(self.execute_query("""
        SELECT * FROM scrim_players WHERE (scrim_id = ?) AND (player_id = ?)
        """, (scrim_id, user_id)))
