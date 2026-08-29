"""
memory.py
Tracks state across the agent's plan-act loop: which stops have
been visited, the most recent planned route, and a short history
of goals handled in this session, integrated with SQLite.
"""
from datetime import datetime

try:
    import db
except Exception:
    db = None


class RouteMemory:
    def __init__(self):
        self.visited: list[str] = []
        self.full_route: list[str] = []
        self.history: list[dict] = []
        
        # Try loading state from database on startup
        if db:
            try:
                # Load chat logs
                self.history = db.get_chat_history()
                
                # Load saved routes to rebuild visited places
                saved_routes = db.get_saved_routes()
                if saved_routes:
                    # Initialize full_route to the most recently saved route
                    self.full_route = saved_routes[0]["ordered_route"]
                    for route in saved_routes:
                        for place in route["ordered_route"]:
                            self.add_visited(place)
            except Exception as error:
                print(f"[DB Warning] Could not load state from database: {error}")

    def add_visited(self, place: str) -> None:
        """Record a place as visited, without duplicating it."""
        if place not in self.visited:
            self.visited.append(place)

    def set_full_route(self, route: list[str]) -> None:
        """Store the latest planned route and mark every stop as visited."""
        self.full_route = route
        for place in route:
            self.add_visited(place)

    def log_goal(self, goal: str, result: str) -> None:
        """Keep a record of each goal handled, and save it in the database."""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "goal": goal,
            "result": result,
        }
        self.history.append(log_entry)
        
        if db:
            try:
                db.log_chat_message(goal, result)
            except Exception as error:
                print(f"[DB Warning] Could not write goal to database: {error}")

    def has_visited(self, place: str) -> bool:
        return place in self.visited

    def summary(self) -> dict:
        """A snapshot of everything memory currently holds."""
        return {
            "visited_so_far": self.visited,
            "planned_route": self.full_route,
            "goals_handled": len(self.history),
        }
