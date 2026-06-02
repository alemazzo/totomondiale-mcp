#!/usr/bin/env python3
"""MCP Server for Totomondiale — AI agents can view and submit predictions."""
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.client import login, submit_group_bets, submit_prolific_total
from src.client import submit_qualification, submit_special_bets, get_formation
from src.client import list_players, get_player_formation
from src.models import MATCHES, TEAMS, PLAYERS

app = Server("totomondiale-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="totomondiale_login",
            description="Log into the Totomondiale website with email and password. Must be called first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Login email"},
                    "password": {"type": "string", "description": "Login password"},
                },
                "required": ["email", "password"],
            },
        ),
        Tool(
            name="totomondiale_get_formation",
            description="View your current formation: all group bets, qualifications, special bets, and prolific total.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="totomondiale_list_matches",
            description="List all match IDs organized by group.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="totomondiale_list_teams",
            description="List all team names and their IDs.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="totomondiale_list_players",
            description="List all players on the leaderboard with their rank and points.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="totomondiale_get_player_formation",
            description="View another player's formation (bets). Provide the exact username from the leaderboard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Exact username from the leaderboard (e.g. 'ArtuMazz')"},
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="totomondiale_submit_group_bets",
            description="Submit group stage score predictions for a single group (6 scores + prolific index 0-5).",
            inputSchema={
                "type": "object",
                "properties": {
                    "group": {"type": "string", "description": "Group letter (A-L)", "enum": list(MATCHES.keys())},
                    "scores": {"type": "array", "description": "6 predicted scores as 'H-A' strings", "items": {"type": "string"}, "minItems": 6, "maxItems": 6},
                    "prolific_index": {"type": "integer", "description": "Index (0-5) of the most prolific match in this group", "minimum": 0, "maximum": 5},
                },
                "required": ["group", "scores", "prolific_index"],
            },
        ),
        Tool(
            name="totomondiale_submit_prolific_total",
            description="Submit the tournament's overall most prolific group stage match (Pt).",
            inputSchema={
                "type": "object",
                "properties": {
                    "group": {"type": "string", "description": "Group letter", "enum": list(MATCHES.keys())},
                    "match_index": {"type": "integer", "description": "Index (0-5) of the match within the group", "minimum": 0, "maximum": 5},
                },
                "required": ["group", "match_index"],
            },
        ),
        Tool(
            name="totomondiale_submit_qualification",
            description="Submit which teams qualify for a knockout phase. Fase 16 requires 32 teams advancing from groups, fase 8 requires 16, fase 4 requires 8, fase 2 requires 4, fase 1 requires 2.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fase": {"type": "integer", "description": "Knockout phase: 16=Sedicesimi(32 teams), 8=Ottavi(16), 4=Quarti(8), 2=Semifinali(4), 1=Finalisti(2)", "enum": [16, 8, 4, 2, 1]},
                    "teams": {"type": "array", "description": "Team names (exact from list)", "items": {"type": "string"}},
                },
                "required": ["fase", "teams"],
            },
        ),
        Tool(
            name="totomondiale_submit_special_bets",
            description="Submit special bets: tournament winner and top scorer (Capocannoniere).",
            inputSchema={
                "type": "object",
                "properties": {
                    "winner": {"type": "string", "description": "Team name of the World Cup winner"},
                    "capocannoniere_name": {"type": "string", "description": f"Player name for top scorer. Known: {list(PLAYERS.keys())}"},
                },
                "required": ["winner", "capocannoniere_name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "totomondiale_login":
            result = login(arguments["email"], arguments["password"])

        elif name == "totomondiale_get_formation":
            result = get_formation()

        elif name == "totomondiale_list_matches":
            result = {f"Group {g}": ids for g, ids in MATCHES.items()}

        elif name == "totomondiale_list_teams":
            result = dict(sorted(TEAMS.items(), key=lambda x: x[0].lower()))

        elif name == "totomondiale_list_players":
            result = list_players()

        elif name == "totomondiale_get_player_formation":
            result = get_player_formation(arguments["username"])

        elif name == "totomondiale_submit_group_bets":
            result = submit_group_bets(
                arguments["group"].upper(),
                arguments["scores"],
                arguments["prolific_index"],
            )

        elif name == "totomondiale_submit_prolific_total":
            result = submit_prolific_total(
                arguments["group"].upper(),
                arguments["match_index"],
            )

        elif name == "totomondiale_submit_qualification":
            result = submit_qualification(
                arguments["fase"],
                arguments["teams"],
            )

        elif name == "totomondiale_submit_special_bets":
            result = submit_special_bets(
                arguments["winner"],
                arguments["capocannoniere_name"],
            )

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        result = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
