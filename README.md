# RoutePilot AI

**CSE476 — Agentic AI and Intelligent Automation — Project 1 (Topic T14)**
Multi-Stop Route Planner Agent

RoutePilot AI is an agent that plans an efficient order to visit a list of places. Given a goal like "plan a route to visit Red Fort, India Gate, and Lotus Temple," it uses real map data to work out a sensible visiting order — not by guessing, but by actually calling tools, reasoning over their results, and remembering what it has already planned.

---

## What Makes This an Agent, Not a Chatbot

- **Calls real tools** — `get_distance` and `order_stops` are actual Python functions the AI decides to invoke, not text it generates
- **Takes multiple steps** — the agent reasons, calls a tool, reads the result, and decides what to do next, rather than answering in one shot
- **Remembers** — `RouteMemory` tracks visited stops, the latest planned route, and a history of goals across the session

---

## Tools

**`get_distance(place_a, place_b)`**
Returns the real driving distance in kilometers between two named places. It works in two steps: first it converts each place name into coordinates using Nominatim (OpenStreetMap's free geocoding service), then it asks OpenRouteService for the real driving distance between those coordinates.

**`order_stops(stops)`**
Takes a list of place names and returns them in a sensible visiting order, using a nearest-neighbor strategy — starting from one place, it repeatedly moves to whichever unvisited place is currently closest, using `get_distance` to compare options at each step.

---

## Memory

`RouteMemory` (in `memory.py`) tracks three things across the whole session:

- `visited` — every place that has been worked into a route so far
- `full_route` — the most recently planned complete route, in order
- `history` — a timestamped log of every goal handled, with the goal text and the agent's final answer

This memory is read back in later turns — for example, if a second goal asks to add a stop to "today's plan," the agent can build on the route already stored in `memory.full_route` instead of starting from nothing. `memory.summary()` gives a snapshot of all of this at any point, which is also what the demo notebook prints at the end to prove memory persisted across multiple goals.

---

## Honest Failure

While building `get_distance`, the tool kept failing with a `404 Not Found` error from OpenRouteService whenever the route involved large landmarks like Red Fort. The real cause, once we dug into the error response, was that OpenRouteService's default road-matching search only looks within 350 meters of a coordinate — and Nominatim's coordinate for a large monument complex often lands well inside the grounds, farther than 350 meters from the nearest mapped road.

We fixed this two ways: first by widening the search radius to 1000 meters using the `radiuses` parameter, and then by discovering that OpenRouteService's `GET` endpoint silently ignores that parameter — it only works on the `POST` endpoint. Switching `get_distance` to a `POST` request (using the `/geojson` variant so the response shape stayed the same) resolved it completely. We also added a small delay before every Nominatim request, since Nominatim's free tier requires at least one second between calls and was occasionally being rate-limited. All of this is now handled with clear `RuntimeError`/`ValueError` messages instead of silent failures, so if a similar issue comes up again it's immediately diagnosable rather than a black box.

---

## Project Structure

```
RoutePilot-AI/
├── tools/
│   ├── __init__.py
│   └── route_tools.py     # get_distance, order_stops
├── main.py                 # agent loop (plan → act → check → repeat)
├── memory.py                # RouteMemory
├── demo.ipynb               # notebook demo with 2-3 example goals
├── .env                     # GROQ_API_KEY, ORS_API_KEY (not committed)
├── .gitignore
└── README.md
```

---

## Setup

```bash
conda create -n routepilot python=3.11
conda activate routepilot
pip install openai requests python-dotenv jupyter
```

Add your keys to `.env`:
```
GROQ_API_KEY=your_groq_key_here
ORS_API_KEY=your_openrouteservice_key_here
```

## Running It

```bash
# Test the tools on their own, no AI involved
python tools/route_tools.py

# Run the full agent
python main.py

# Open the demo notebook
jupyter notebook
```

---

## Tech Stack

- **Groq** (`openai/gpt-oss-120b`) — the LLM powering the agent's reasoning and tool-calling
- **Nominatim** (OpenStreetMap) — free geocoding, place name → coordinates
- **OpenRouteService** — free real-world driving distances and routing
- **Python** — no agent framework used; the plan-act loop is written from scratch so every step is transparent and explainable

---

## Who Did What

*

- [Anshika raj] — The work was done individually not in a group