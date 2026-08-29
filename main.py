"""
main.py
The agent loop: sends the goal + tool descriptions to the AI,
executes any tools it requests, feeds results back, and repeats
until a final answer is produced or a safety step-limit is hit.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from tools.route_tools import get_distance, order_stops
from memory import RouteMemory

load_dotenv()

# Fix SSL certificate issues by clearing invalid SSL paths
if os.getenv("SSL_CERT_FILE"):
    cert_file = os.getenv("SSL_CERT_FILE")
    if not os.path.exists(cert_file):
        os.environ.pop("SSL_CERT_FILE", None)
if os.getenv("SSL_CERT_DIR"):
    cert_dir = os.getenv("SSL_CERT_DIR")
    if not os.path.exists(cert_dir):
        os.environ.pop("SSL_CERT_DIR", None)

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

MODEL = "openai/gpt-oss-120b"
MAX_STEPS = 6  # safety limit so a confused agent can't loop forever

memory = RouteMemory()

# Tool schemas: this is how the AI knows what tools exist and what
# arguments each one needs. The AI never runs code itself — it only
# ever asks us to run it, and we stay in full control.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_distance",
            "description": "Get the real driving distance in kilometers between two named places.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_a": {"type": "string", "description": "First place name"},
                    "place_b": {"type": "string", "description": "Second place name"},
                },
                "required": ["place_a", "place_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "order_stops",
            "description": "Decide a sensible, efficient order to visit a list of stops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stops": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of place names to visit",
                    },
                    "start": {
                        "type": "string",
                        "description": "Optional stop to enforce as the starting point of the route"
                    },
                    "end": {
                        "type": "string",
                        "description": "Optional stop to enforce as the final point of the route"
                    }
                },
                "required": ["stops"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "get_distance": get_distance,
    "order_stops": order_stops,
}


def execute_tool_call(tool_call) -> str:
    """
    Run the actual Python function the AI asked for, and always
    return a JSON string — even on failure — so the AI can see
    what went wrong and adjust, instead of the whole program crashing.
    """
    func_name = tool_call.function.name
    func_args = json.loads(tool_call.function.arguments)

    print(f"  -> calling {func_name}({func_args})")

    func = AVAILABLE_FUNCTIONS.get(func_name)
    if func is None:
        print(f"  -> ERROR: Unknown tool: {func_name}")
        return json.dumps({"error": f"Unknown tool: {func_name}"})

    try:
        result = func(**func_args)
    except Exception as e:
        print(f"  -> ERROR: {e}")
        return json.dumps({"error": str(e)})

    print(f"  -> result: {result}")

    if func_name == "order_stops":
        memory.set_full_route(result)

    return json.dumps(result)


def run_agent(user_goal: str) -> str:
    """Run the full plan-act loop for one user goal and return the final answer."""
    system_content = (
        "You are RoutePilot, a route-planning agent. Use the tools available to "
        "plan efficient multi-stop routes. Always call order_stops before giving "
        "a final route to the user, and explain the route briefly in plain language. "
        "If a tool returns an error, do not retry with reworded place names more than "
        "once — report the error to the user clearly instead."
    )

    # Give the AI visibility into what's already been planned, so it can
    # build on earlier goals instead of starting from nothing each time.
    if memory.full_route:
        system_content += (
            f"\n\nContext from earlier in this session: the current planned route is "
            f"{memory.full_route}. If the user asks to add or change stops, combine "
            f"this existing route with the new request before calling order_stops."
        )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_goal},
    ]

    for step in range(1, MAX_STEPS + 1):
        print(f"\n[Step {step}] Thinking...")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            print("\nFinal answer:", message.content)
            memory.log_goal(user_goal, message.content)
            return message.content

        for tool_call in message.tool_calls:
            result_json = execute_tool_call(tool_call)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_json,
            })

    fallback = "Agent could not finish within the step limit — try a simpler goal."
    memory.log_goal(user_goal, fallback)
    return fallback


if __name__ == "__main__":
    goal = "Plan the best order to visit India Gate Delhi, Qutub Minar Delhi, Red Fort Delhi, and Lotus Temple Delhi."
    run_agent(goal)
    print("\nMemory now holds:", memory.summary())


# def run_agent(user_goal: str) -> str:
#     """Run the full plan-act loop for one user goal and return the final answer."""
#     system_content = (
#         "You are RoutePilot, a route-planning agent. Use the tools available to "
#         "plan efficient multi-stop routes. Always call order_stops before giving "
#         "a final route to the user, and explain the route briefly in plain language. "
#         "If a tool returns an error, do not retry with reworded place names more than "
#         "once — report the error to the user clearly instead."
#     )

#     # Give the AI visibility into what's already been planned, so it can
#     # build on earlier goals instead of starting from nothing each time.
#     if memory.full_route:
#         system_content += (
#             f"\n\nContext from earlier in this session: the current planned route is "
#             f"{memory.full_route}. If the user asks to add or change stops, combine "
#             f"this existing route with the new request before calling order_stops."
#         )

#     messages = [
#         {"role": "system", "content": system_content},
#         {"role": "user", "content": user_goal},
#     ]