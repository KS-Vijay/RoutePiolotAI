"""
route_tools.py
Route-planning tools for distances, durations, path geometries, and stop ordering.
Interfaces with Nominatim and OpenRouteService, and uses db.py for persistent caching.
"""

import os
import time
import requests
from dotenv import load_dotenv

# Try importing the db helper. If not written or raises errors, we fall back to direct APIs.
try:
    import db
except Exception:
    db = None

load_dotenv()

ORS_API_KEY = os.getenv("ORS_API_KEY")

# In-memory caches to avoid duplicate lookups within a single function call
_coord_cache = {}
_route_details_cache = {}
REQUEST_TIMEOUT = 10


def get_coordinates(place_name: str) -> tuple[float, float]:
    """Turn a place name into latitude and longitude using Nominatim, with SQLite caching."""
    key = place_name.strip().lower()
    if key in _coord_cache:
        return _coord_cache[key]

    # Try database cache first
    if db:
        try:
            cached = db.get_coordinates_from_cache(place_name)
            if cached:
                _coord_cache[key] = cached
                return cached
        except Exception as error:
            print(f"[DB Warning] Could not read geocoding cache: {error}")

    # Fallback to network request
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "RoutePilot-AI (production-agent)"}

    try:
        time.sleep(1)  # Nominatim requires max 1 request per second
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not reach Nominatim for '{place_name}': {error}"
        ) from error

    if not data:
        raise ValueError(
            f"Could not find location: '{place_name}'. Try a more specific name."
        )

    coordinates = (float(data[0]["lat"]), float(data[0]["lon"]))
    _coord_cache[key] = coordinates

    # Save to database cache
    if db:
        try:
            db.save_coordinates_to_cache(place_name, coordinates[0], coordinates[1])
        except Exception as error:
            print(f"[DB Warning] Could not write geocoding cache: {error}")

    return coordinates


def get_route_details(place_a: str, place_b: str) -> dict:
    """
    Get detailed route between two place names.
    Returns a dict with keys:
    - distance: float (km)
    - duration: float (minutes)
    - geometry: list of [lat, lon] coordinates
    """
    if place_a.strip().lower() == place_b.strip().lower():
        lat, lon = get_coordinates(place_a)
        return {"distance": 0.0, "duration": 0.0, "geometry": [[lat, lon]]}

    cache_key = tuple(sorted([place_a.strip().lower(), place_b.strip().lower()]))
    if cache_key in _route_details_cache:
        return _route_details_cache[cache_key]

    # Try database cache first
    if db:
        try:
            cached = db.get_route_from_cache(place_a, place_b)
            if cached:
                _route_details_cache[cache_key] = cached
                return cached
        except Exception as error:
            print(f"[DB Warning] Could not read route cache: {error}")

    # Fetch coordinates
    lat1, lon1 = get_coordinates(place_a)
    lat2, lon2 = get_coordinates(place_b)

    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [[lon1, lat1], [lon2, lat2]],
        "radiuses": [1000, 1000],
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        
        feature = data["features"][0]
        segment = feature["properties"]["segments"][0]
        
        meters = segment["distance"]
        duration_seconds = segment["duration"]
        
        # ORS returns [lon, lat] - we flip to [lat, lon] for Leaflet map compatibility
        raw_coords = feature["geometry"]["coordinates"]
        geometry = [[c[1], c[0]] for c in raw_coords]
        
    except requests.HTTPError as error:
        try:
            detail = error.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = error.response.text[:200]
        raise RuntimeError(
            f"OpenRouteService rejected the route '{place_a}' -> '{place_b}': {detail}"
        ) from error
    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not reach OpenRouteService for '{place_a}' -> '{place_b}': {error}"
        ) from error
    except (KeyError, IndexError) as error:
        raise RuntimeError(
            f"OpenRouteService returned no route between '{place_a}' and '{place_b}'."
        ) from error

    distance_km = round(meters / 1000, 2)
    duration_min = round(duration_seconds / 60, 2)
    result = {
        "distance": distance_km,
        "duration": duration_min,
        "geometry": geometry,
    }

    _route_details_cache[cache_key] = result

    # Save to database cache
    if db:
        try:
            db.save_route_to_cache(place_a, place_b, distance_km, duration_min, geometry)
        except Exception as error:
            print(f"[DB Warning] Could not write route cache: {error}")

    return result


def get_distance(place_a: str, place_b: str) -> float:
    """Wrapper function to match the LLM tool signature. Returns distance in km."""
    return get_route_details(place_a, place_b)["distance"]


def order_stops(stops: list[str], start: str | None = None, end: str | None = None) -> list[str]:
    """
    Solve the Traveling Salesperson Problem (TSP) to find the most efficient route.
    Supports start and end location pinning.
    Uses exact permutation solver for N <= 9 stops and 2-opt heuristic for larger stop sets.
    """
    if not stops:
        return []
    
    # Strip whitespace and clean stops list
    stops = [s.strip() for s in stops if s.strip()]
    if not stops:
        return []

    # Handle single or duplicate stop case
    unique_stops = []
    for s in stops:
        if s not in unique_stops:
            unique_stops.append(s)
            
    if len(unique_stops) <= 1:
        return unique_stops

    # Handle pinned stops presence in the list
    if start:
        start = start.strip()
        if start not in unique_stops:
            unique_stops.insert(0, start)
    if end:
        end = end.strip()
        if end not in unique_stops:
            unique_stops.append(end)

    n = len(unique_stops)
    
    # Build distance matrix
    dist_matrix = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                dist_matrix[(i, j)] = 0.0
            else:
                try:
                    dist_matrix[(i, j)] = get_distance(unique_stops[i], unique_stops[j])
                except Exception:
                    # In case of routing failures, assign a high default penalty to avoid crashing
                    dist_matrix[(i, j)] = 999.0

    # Determine index positions of fixed start and end points
    start_idx = unique_stops.index(start) if start in unique_stops else None
    end_idx = unique_stops.index(end) if end in unique_stops else None

    best_path = None
    best_dist = float("inf")

    # If N <= 9, use exact brute-force search over all permutations
    if n <= 9:
        import itertools
        indices = list(range(n))
        permute_indices = [idx for idx in indices if idx != start_idx and idx != end_idx]
        
        for perm in itertools.permutations(permute_indices):
            path = list(perm)
            if start_idx is not None:
                path.insert(0, start_idx)
            if end_idx is not None:
                path.append(end_idx)
                
            # Compute total distance
            d = sum(dist_matrix[(path[k], path[k+1])] for k in range(n - 1))
            if d < best_dist:
                best_dist = d
                best_path = path
    else:
        # For larger N, use a Greedy Nearest-Neighbor initial route followed by 2-opt refinement
        remaining = list(range(n))
        
        if start_idx is not None:
            current = start_idx
            remaining.remove(start_idx)
        elif end_idx is not None and end_idx == remaining[0]:
            current = remaining[1] if len(remaining) > 1 else remaining[0]
            remaining.remove(current)
        else:
            current = remaining.pop(0)

        path = [current]
        
        has_end = end_idx is not None
        if has_end and end_idx in remaining:
            remaining.remove(end_idx)

        while remaining:
            nearest = min(remaining, key=lambda idx: dist_matrix[(current, idx)])
            path.append(nearest)
            remaining.remove(nearest)
            current = nearest

        if has_end:
            path.append(end_idx)

        # 2-opt local search refinement
        best_dist = sum(dist_matrix[(path[k], path[k+1])] for k in range(n - 1))
        improved = True
        while improved:
            improved = False
            start_swap = 1 if start_idx is not None else 0
            end_swap = n - 1 if end_idx is not None else n

            for i in range(start_swap, end_swap - 1):
                for j in range(i + 1, end_swap):
                    new_path = path[:]
                    new_path[i:j+1] = list(reversed(path[i:j+1]))
                    
                    new_dist = sum(dist_matrix[(new_path[k], new_path[k+1])] for k in range(n - 1))
                    if new_dist < best_dist:
                        path = new_path
                        best_dist = new_dist
                        improved = True
        best_path = path

    return [unique_stops[idx] for idx in best_path]


if __name__ == "__main__":
    test_stops = ["India Gate Delhi", "Qutub Minar Delhi", "Red Fort Delhi", "Lotus Temple Delhi"]
    print("Testing get_route_details...")
    details = get_route_details(test_stops[0], test_stops[1])
    print(f"Route: {test_stops[0]} -> {test_stops[1]}")
    print(f"  Distance: {details['distance']} km")
    print(f"  Duration: {details['duration']} minutes")
    print(f"  Geometry points: {len(details['geometry'])}")
    
    print("\nTesting order_stops (TSP)...")
    optimized = order_stops(test_stops, start="Red Fort Delhi")
    print(f"Optimal order starting from Red Fort: {optimized}")
