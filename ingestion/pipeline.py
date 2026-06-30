# Main ingestion loop with smart polling
import json
import logging
import os
from datetime import datetime, timezone
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Send a get request to a specified URL and return the JSON response
gamesUrl = "http://worldcup26.ir:3050/get/games"


def get_games(games_url):
    try:
        response = requests.get(games_url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching games: {e}")
        return None


def posgres_connection():
    try:
        # Connect to the PostgreSQL database using environment variables
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            port=os.getenv("POSTGRES_PORT"),
        )
        return conn
    except psycopg2.Error as e:
        logging.error(f"Error connecting to PostgreSQL: {e}")
        return None


def _coerce_int(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(float(stripped))
        except ValueError:
            return default
    return default


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y", "finished", "ft", "full-time", "full time"}
    return False


def _coerce_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None

        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.strptime(stripped, "%m/%d/%Y %H:%M")
            except ValueError:
                return stripped

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed

    return str(value)


## Transforming the games data into a format suitable for database insertion
def transform_games_data(games_data):
    if isinstance(games_data, dict):
        games_payload = games_data.get("games", [])
    elif isinstance(games_data, list):
        games_payload = games_data
    else:
        return []

    transformed_data = []
    for game in games_payload:
        if not isinstance(game, dict):
            continue

        transformed_game = {
            "id": game.get("id") or game.get("_id"),
            "home_team_id": _coerce_int(game.get("home_team_id")),
            "away_team_id": _coerce_int(game.get("away_team_id")),
            "stadium_id": _coerce_int(game.get("stadium_id")),
            "home_score": _coerce_int(game.get("home_score"), default=0),
            "away_score": _coerce_int(game.get("away_score"), default=0),
            "time_elapsed": _coerce_int(game.get("time_elapsed"), default=0),
            "group": game.get("group"),
            "matchday": _coerce_int(game.get("matchday")),
            "type": game.get("type"),
            "date": _coerce_datetime(game.get("local_date")),
            "finished": _coerce_bool(game.get("finished")),
            
        }
        transformed_data.append(transformed_game)
    return transformed_data


# inserting game dta into the database
def insert_games_into_db(conn, games):
    if not conn or not games:
        logging.error("Invalid database connection or empty games data.")
        return

    try:
        with conn.cursor() as cursor:
            for game in games:
                cursor.execute(
                    """
                    INSERT INTO games (
                        id,
                        home_team_id,
                        away_team_id,
                        stadium_id,
                        home_score,
                        away_score,
                        time_elapsed,
                        "group",
                        matchday,
                        type,
                        date,
                        finished
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        home_team_id = EXCLUDED.home_team_id,
                        away_team_id = EXCLUDED.away_team_id,
                        stadium_id = EXCLUDED.stadium_id,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        time_elapsed = EXCLUDED.time_elapsed,
                        "group" = EXCLUDED."group",
                        matchday = EXCLUDED.matchday,
                        type = EXCLUDED.type,
                        date = EXCLUDED.date,
                        finished = EXCLUDED.finished
                    """,
                    (
                        game["id"],
                        game["home_team_id"],
                        game["away_team_id"],
                        game["stadium_id"],
                        game["home_score"],
                        game["away_score"],
                        game["time_elapsed"],
                        game["group"],
                        game["matchday"],
                        game["type"],
                        game["date"],
                        game["finished"],
                        
                    ),
                )
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Error occurred while inserting games into the database: {e}")
        raise

if __name__ == "__main__":
    # 1. Test API
    games_data = get_games(gamesUrl)
    
    # 2. Test transform
    if games_data is not None:
        transformed_games = transform_games_data(games_data)
        print(json.dumps(transformed_games[0], indent=4, default=str))

        # 3. Upsert into DB
        conn = posgres_connection()
        if conn:
            try:
                insert_games_into_db(conn, transformed_games)
                conn.commit()
                print("BET Games upserted successfully!")
            except Exception as exc:
                conn.rollback()
                logging.error(f"Failed to upsert games: {exc}")
            finally:
                conn.close()
        else:
            print("FAWK Failed to connect.")


