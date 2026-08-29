"""
db.py
Database helper module for RoutePilot AI.
This module uses Python's built-in sqlite3 library to handle:
1. Geocoding Cache (place names to latitude/longitude)
2. Route Cache (distances, durations, and geometry between places)
3. Saved Route Plans (itineraries saved by the user)
4. Chat History (log of user prompts and agent responses)

Implement the functions below by replacing the comments with sqlite3 Python code.
"""

import sqlite3
import json
from datetime import datetime

DATABASE_NAME = "routepilot.db"

def get_connection():
    """Helper function to get a connection to the SQLite database."""
    # TODO: Connect to the database file defined by DATABASE_NAME
    # Return the connection object.
    # Hint: Use sqlite3.connect(DATABASE_NAME)
    conn=sqlite3.connect(DATABASE_NAME)
    return conn
    pass


def init_db():
    """Initialize the database and create tables if they don't exist."""
    # TODO: Connect to the database and get a cursor
    conn=get_connection()
    cursor=conn.cursor()
    
    # TODO: Create table 'geocoding_cache'
    # Columns:
    # - place_name: TEXT (Primary Key)
    # - lat: REAL
    # - lon: REAL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geocoding_cache(
        place_name TEXT PRIMARY KEY,
        lat REAL,
        lon REAL);
    """)
    
    
    # TODO: Create table 'route_cache'
    # Columns:
    # - place_a: TEXT
    # - place_b: TEXT
    # - distance: REAL (in km)
    # - duration: REAL (in minutes)
    # - geometry: TEXT (JSON stringified list of [lat, lon] coordinates)
    # Primary Key: (place_a, place_b)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_cache(
        place_a TEXT,
        place_b TEXT,
        distance REAL,
        duration REAL,
        geometry TEXT,
        PRIMARY KEY(place_a,place_b));
    """)
    
    # TODO: Create table 'saved_routes'
    # Columns:
    # - id: INTEGER (Primary Key AUTOINCREMENT)
    # - name: TEXT
    # - created_at: TEXT
    # - stops: TEXT (JSON stringified list of original stops)
    # - ordered_route: TEXT (JSON stringified list of optimized stops)
    # - total_distance: REAL
    # - total_duration: REAL
    # - geometry: TEXT (JSON stringified list of [lat, lon] coordinates for the full route)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_routes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        created_at TEXT,
        stops TEXT,
        ordered_route TEXT,
        total_distance REAL,
        total_duration REAL,
        geometry TEXT);
    """)
    
    # TODO: Create table 'chat_history'
    # Columns:
    # - id: INTEGER (Primary Key AUTOINCREMENT)
    # - timestamp: TEXT
    # - goal: TEXT
    # - response: TEXT
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        goal TEXT,
        response TEXT);
    """)
    
    # TODO: Commit the changes and close the connection
    conn.commit()
    conn.close()


def get_coordinates_from_cache(place_name: str) -> tuple[float, float] | None:
    """Retrieve latitude and longitude for a place name from geocoding_cache."""
    key = place_name.strip().lower()
    # TODO: Connect to database, select lat and lon where place_name matches key
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("""
    SELECT lat,lon FROM geocoding_cache where place_name=?
    """,(key,))
    
    # TODO: Fetch the first result. If found, return (lat, lon)
    row=cursor.fetchone()
    if(row):
        return row[0],row[1]
    
    # TODO: Make sure to close the connection when done
    conn.close()
    
    
    return None


def save_coordinates_to_cache(place_name: str, lat: float, lon: float) -> None:
    """Save place name and its coordinates into geocoding_cache."""
    key = place_name.strip().lower()
    # TODO: Connect to database, insert or replace key, lat, lon into geocoding_cache
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO geocoding_cache(place_name,lat,lon) VALUES(?,?,?)
    """,key,lat,lon)
    
    # TODO: Commit and close the connection
    conn.commit()
    conn.close()
    
    pass


def get_route_from_cache(place_a: str, place_b: str) -> dict | None:
    """
    Retrieve cached route details between place_a and place_b.
    Returns a dict with 'distance', 'duration', and 'geometry' (list of lists) if found, else None.
    """
    # Normalize order so we can query bi-directionally (A->B or B->A)
    # Hint: sort the names alphabetically
    p1 = min(place_a.strip().lower(), place_b.strip().lower())
    p2 = max(place_a.strip().lower(), place_b.strip().lower())
    
    # TODO: Connect to database, select distance, duration, and geometry from route_cache where place_a and place_b match
    
    
    # TODO: Fetch the result. If found, load the geometry JSON string back into a Python list:
    #       geometry_list = json.loads(row[2])
    #       Return a dictionary: {"distance": row[0], "duration": row[1], "geometry": geometry_list}
    
    
    # TODO: Close connection
    
    
    return None


def save_route_to_cache(place_a: str, place_b: str, distance: float, duration: float, geometry_list: list[list[float]]) -> None:
    """Save route details between place_a and place_b into route_cache."""
    # Normalize order
    p1 = min(place_a.strip().lower(), place_b.strip().lower())
    p2 = max(place_a.strip().lower(), place_b.strip().lower())
    
    # Convert geometry list of coordinates to a JSON string
    geometry_json = json.dumps(geometry_list)
    
    # TODO: Connect to database, insert or replace p1, p2, distance, duration, geometry_json into route_cache
    
    
    # TODO: Commit and close the connection
    
    
    pass


def save_route_plan(name: str, stops: list[str], ordered_route: list[str], total_distance: float, total_duration: float, geometry_list: list[list[float]]) -> int:
    """
    Save a completed itinerary plan to saved_routes.
    Returns the ID of the newly inserted route.
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stops_json = json.dumps(stops)
    ordered_route_json = json.dumps(ordered_route)
    geometry_json = json.dumps(geometry_list)
    
    # TODO: Connect to database, insert name, created_at, stops_json, ordered_route_json, total_distance, total_duration, geometry_json into saved_routes
    
    
    # TODO: Get the last inserted ID using cursor.lastrowid
    
    
    # TODO: Commit and close the connection
    
    
    # Return the inserted ID (replace 0 with actual ID variable)
    return 0


def get_saved_routes() -> list[dict]:
    """Retrieve all saved routes from saved_routes ordered by id DESC."""
    # TODO: Connect to database, select all columns from saved_routes sorted by id desc
    
    
    # TODO: Fetch all rows and construct a list of dicts.
    #       Each dict should have keys: 'id', 'name', 'created_at', 'stops' (list), 'ordered_route' (list), 'total_distance', 'total_duration', 'geometry' (list)
    #       Hint: use json.loads() for stops, ordered_route, and geometry strings.
    
    
    # TODO: Close connection
    
    
    return []


def delete_saved_route(route_id: int) -> bool:
    """Delete a saved route by its ID. Returns True if successful."""
    # TODO: Connect to database, delete from saved_routes where id matches route_id
    
    
    # TODO: Check if any row was affected using cursor.rowcount
    
    
    # TODO: Commit and close the connection
    
    
    return False


def log_chat_message(goal: str, response: str) -> None:
    """Log an agent goal and its final answer to chat_history."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # TODO: Connect to database, insert timestamp, goal, response into chat_history
    
    
    # TODO: Commit and close connection
    
    
    pass


def get_chat_history() -> list[dict]:
    """Retrieve all chat logs from chat_history ordered by id ASC."""
    # TODO: Connect to database, select timestamp, goal, response from chat_history ordered by id ASC
    
    
    # TODO: Fetch all and format as list of dicts: [{"timestamp": r[0], "goal": r[1], "response": r[2]}]
    
    
    # TODO: Close connection
    
    
    return []
