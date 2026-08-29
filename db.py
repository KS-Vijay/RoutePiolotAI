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
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT lat,lon FROM geocoding_cache WHERE place_name=?
        """, (key,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
    finally:
        conn.close()
    return None


def save_coordinates_to_cache(place_name: str, lat: float, lon: float) -> None:
    """Save place name and its coordinates into geocoding_cache."""
    key = place_name.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO geocoding_cache(place_name,lat,lon) VALUES(?,?,?)
        """, (key, lat, lon))
        conn.commit()
    finally:
        conn.close()


def get_route_from_cache(place_a: str, place_b: str) -> dict | None:
    """
    Retrieve cached route details between place_a and place_b.
    Returns a dict with 'distance', 'duration', and 'geometry' (list of lists) if found, else None.
    """
    p1 = min(place_a.strip().lower(), place_b.strip().lower())
    p2 = max(place_a.strip().lower(), place_b.strip().lower())
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT distance, duration, geometry FROM route_cache WHERE place_a=? AND place_b=?
        """, (p1, p2))
        row = cursor.fetchone()
        if row:
            geometry_list = json.loads(row[2])
            return {"distance": row[0], "duration": row[1], "geometry": geometry_list}
    finally:
        conn.close()
    return None


def save_route_to_cache(place_a: str, place_b: str, distance: float, duration: float, geometry_list: list[list[float]]) -> None:
    """Save route details between place_a and place_b into route_cache."""
    p1 = min(place_a.strip().lower(), place_b.strip().lower())
    p2 = max(place_a.strip().lower(), place_b.strip().lower())
    geometry_json = json.dumps(geometry_list)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO route_cache(place_a,place_b,distance,duration,geometry) VALUES(?,?,?,?,?)
        """, (p1, p2, distance, duration, geometry_json))
        conn.commit()
    finally:
        conn.close()


def save_route_plan(name: str, stops: list[str], ordered_route: list[str], total_distance: float, total_duration: float, geometry_list: list[list[float]]) -> int:
    """
    Save a completed itinerary plan to saved_routes.
    Returns the ID of the newly inserted route.
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stops_json = json.dumps(stops)
    ordered_route_json = json.dumps(ordered_route)
    geometry_json = json.dumps(geometry_list)
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO saved_routes(name,created_at,stops,ordered_route,total_distance,total_duration,geometry)
        VALUES(?,?,?,?,?,?,?)
        """, (name, created_at, stops_json, ordered_route_json, total_distance, total_duration, geometry_json))
        route_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()
        
    return route_id


def get_saved_routes() -> list[dict]:
    """Retrieve all saved routes from saved_routes ordered by id DESC."""
    # TODO: Connect to database, select all columns from saved_routes sorted by id desc
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("""
    SELECT * FROM saved_routes ORDER BY id DESC
    """)
    
    
    # TODO: Fetch all rows and construct a list of dicts.
    #       Each dict should have keys: 'id', 'name', 'created_at', 'stops' (list), 'ordered_route' (list), 'total_distance', 'total_duration', 'geometry' (list)
    #       Hint: use json.loads() for stops, ordered_route, and geometry strings.
    rows=cursor.fetchall()
    route_dict=[]
    for row in rows:
        route_dict.append({
            "id":row[0],
            "name":row[1],
            "created_at":row[2],
            "stops":json.loads(row[3]),
            "ordered_route":json.loads(row[4]),
            "total_distance":row[5],
            "total_duration":row[6],
            "geometry":json.loads(row[7])
        })
    
    # TODO: Close connection
    
    conn.close()
    return route_dict


def delete_saved_route(route_id: int) -> bool:
    """Delete a saved route by its ID. Returns True if successful."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM saved_routes WHERE id=?
        """, (route_id,))
        rowcount = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return bool(rowcount)


def log_chat_message(goal: str, response: str) -> None:
    """Log an agent goal and its final answer to chat_history."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # TODO: Connect to database, insert timestamp, goal, response into chat_history
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("""
    INSERT INTO chat_history(timestamp,goal,response)
    VALUES (?,?,?)
    """,(timestamp,goal,response))
    
    # TODO: Commit and close connection
    conn.commit()
    conn.close()


def get_chat_history() -> list[dict]:
    """Retrieve all chat logs from chat_history ordered by id ASC."""
    # TODO: Connect to database, select timestamp, goal, response from chat_history ordered by id ASC
    conn=get_connection()
    cursor=conn.cursor()
    cursor.execute("""
    SELECT timestamp,goal,response FROM chat_history ORDER BY id ASC
    """)
    
    # TODO: Fetch all and format as list of dicts: [{"timestamp": r[0], "goal": r[1], "response": r[2]}]
    rows=cursor.fetchall()
    chat_list=[]
    for row in rows:
        chat_list.append({
            "timestamp":row[0],
            "goal":row[1],
            "response":row[2]
        })
    
    # TODO: Close connection
    conn.close()
    
    return chat_list
