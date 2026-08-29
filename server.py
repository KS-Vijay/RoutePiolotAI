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
