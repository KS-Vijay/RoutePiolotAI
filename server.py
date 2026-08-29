"""
server.py
FastAPI web server for RoutePilot AI dashboard.
Exposes REST APIs for agent interaction, routing calculations, and database records.
"""

import io
import sys
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

# Try loading SQLite database helper
try:
    import db
except Exception:
    db = None

from main import run_agent, memory
from tools.route_tools import order_stops, get_route_details

app = FastAPI(title="RoutePilot AI Web Server")

# Initialize SQLite database on startup
@app.on_event("startup")
def on_startup():
    if db:
        try:
            db.init_db()
            print("[DB] SQLite database initialized successfully.")
        except Exception as error:
            print(f"[DB Warning] Could not initialize SQLite database: {error}. Proceeding in-memory.")

# Request models
class ChatRequest(BaseModel):
    message: str

class OptimizeRequest(BaseModel):
    stops: List[str]
    start: Optional[str] = None
    end: Optional[str] = None

class SaveRouteRequest(BaseModel):
    name: str
    stops: List[str]
    ordered_route: List[str]
    total_distance: float
    total_duration: float
    geometry: List[List[float]]

# Serve frontend landing page
@app.get("/")
def get_dashboard():
    static_index = os.path.join("static", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return {"message": "RoutePilot AI API active. Create static/index.html to view dashboard."}

# Endpoint to geocode a single place name → coordinates (used by frontend for marker placement)
@app.get("/api/geocode")
def get_geocode(place: str):
    try:
        from tools.route_tools import get_coordinates
        lat, lon = get_coordinates(place)
        return {"place": place, "lat": lat, "lon": lon}
    except Exception as error:
        raise HTTPException(status_code=404, detail=str(error))

# Endpoint to get LLM-suggested nearby POIs along the optimized route
class SuggestionsRequest(BaseModel):
    ordered_route: List[str]

@app.post("/api/suggestions")
def post_suggestions(data: SuggestionsRequest):
    import json as _json
    from openai import OpenAI
    from tools.route_tools import get_coordinates

    route = data.ordered_route
    if not route or len(route) < 1:
        return []

    # Ask LLM for worthy nearby places along this route
    try:
        llm = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )
        route_str = " → ".join(route)
        prompt = (
            f"A traveller is visiting: {route_str}.\n\n"
            "Suggest exactly 4 additional worthy places to visit that are near or along this route "
            "(museums, monuments, parks, viewpoints, local markets, etc). "
            "Do NOT include the places already in the route.\n\n"
            "Reply ONLY with a valid JSON array of objects, no markdown, no explanation. "
            'Each object must have exactly these three string fields: "name", "category", "reason".\n'
            'Example: [{"name": "Humayun\'s Tomb, Delhi", "category": "Monument", "reason": "Close to India Gate, stunning Mughal architecture"}]'
        )
        response = llm.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        suggestions_raw = _json.loads(raw)
    except Exception as e:
        print(f"[Suggestions] LLM error: {e}")
        return []

    # Geocode each suggestion; skip ones Nominatim can't find
    results = []
    for item in suggestions_raw[:5]:
        try:
            name = item.get("name", "").strip()
            if not name:
                continue
            lat, lon = get_coordinates(name)
            results.append({
                "name": name,
                "category": item.get("category", "Place"),
                "reason": item.get("reason", ""),
                "lat": lat,
                "lon": lon,
            })
        except Exception:
            pass  # skip un-geocodable suggestions silently

    return results

# Endpoint to chat with RoutePilot agent
@app.post("/api/chat")
def post_chat(data: ChatRequest):
    # Capture standard output to stream agent steps to the frontend
    old_stdout = sys.stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output
    
    try:
        # Run agent loop
        response = run_agent(data.message)
        logs = captured_output.getvalue()
    except Exception as error:
        logs = captured_output.getvalue()
        response = f"An error occurred: {str(error)}"
    finally:
        sys.stdout = old_stdout
        
    return {
        "response": response,
        "logs": logs
    }

# Endpoint to optimize a route directly (TSP solver)
@app.post("/api/optimize")
def post_optimize(data: OptimizeRequest):
    try:
        # Clear empty inputs
        stops = [s.strip() for s in data.stops if s.strip()]
        if not stops:
            raise HTTPException(status_code=400, detail="Stops list cannot be empty")
            
        ordered = order_stops(stops, start=data.start, end=data.end)
        
        segments = []
        full_geometry = []
        total_distance = 0.0
        total_duration = 0.0
        
        for i in range(len(ordered) - 1):
            p_a = ordered[i]
            p_b = ordered[i+1]
            details = get_route_details(p_a, p_b)
            
            segments.append({
                "from": p_a,
                "to": p_b,
                "distance": details["distance"],
                "duration": details["duration"],
                "geometry": details["geometry"]
            })
            total_distance += details["distance"]
            total_duration += details["duration"]
            
            # Combine polylines to form a continuous route on the map
            if not full_geometry:
                full_geometry.extend(details["geometry"])
            else:
                full_geometry.extend(details["geometry"][1:])
                
        return {
            "ordered_route": ordered,
            "segments": segments,
            "total_distance": round(total_distance, 2),
            "total_duration": round(total_duration, 2),
            "geometry": full_geometry
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

# Database route: Save an optimized route plan
@app.post("/api/routes")
def post_save_route(data: SaveRouteRequest):
    if not db:
        raise HTTPException(status_code=501, detail="SQLite database layer not implemented or unavailable.")
    try:
        route_id = db.save_route_plan(
            name=data.name,
            stops=data.stops,
            ordered_route=data.ordered_route,
            total_distance=data.total_distance,
            total_duration=data.total_duration,
            geometry_list=data.geometry
        )
        return {"id": route_id, "message": "Route saved successfully."}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Database error: {str(error)}")

# Database route: Fetch all saved route plans
@app.get("/api/routes")
def get_routes():
    if not db:
        return []
    try:
        return db.get_saved_routes()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Database error: {str(error)}")

# Database route: Delete a saved route plan
@app.delete("/api/routes/{route_id}")
def delete_route(route_id: int):
    if not db:
        raise HTTPException(status_code=501, detail="SQLite database layer not implemented or unavailable.")
    try:
        success = db.delete_saved_route(route_id)
        if not success:
            raise HTTPException(status_code=404, detail="Route not found")
        return {"message": "Route deleted successfully."}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Database error: {str(error)}")

# Database route: Get chat log history
@app.get("/api/history")
def get_chat_history():
    if not db:
        # Fall back to in-memory history tracker
        return memory.history
    try:
        return db.get_chat_history()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Database error: {str(error)}")

# Database route: Get current memory summary
@app.get("/api/memory")
def get_memory_summary():
    return memory.summary()


# Serve remaining static folders (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
