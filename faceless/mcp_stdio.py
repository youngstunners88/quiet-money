"""The stdio MCP protocol in one place (JSON-RPC 2.0, one message per line): `Server(name, version, tools).serve()`.

`tools` maps a tool name to (function(args) -> JSON-able, description, JSON schema). A tool that raises returns its reason as an error result, never a traceback.
Used by quiet-shop; quiet-planner carries its own copy of the same few lines.
"""

from __future__ import annotations

import json
import sys
import traceback

PROTOCOL = "2024-11-05"


def schema(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


class Server:
    def __init__(self, name: str, version: str, tools: dict):
        self.info, self.tools = {"name": name, "version": version}, tools

    def call(self, name: str, args: dict) -> dict:
        if name not in self.tools:
            return {"content": [{"type": "text", "text": f"unknown tool {name!r}"}], "isError": True}
        try:
            out = self.tools[name][0](args or {})
            return {"content": [{"type": "text", "text": json.dumps(out, indent=1, default=str)}], "isError": False}
        except Exception as e:  # noqa: BLE001 - the agent gets the reason, never a traceback with paths or keys
            print(traceback.format_exc(), file=sys.stderr)
            from faceless import config
            return {"content": [{"type": "text", "text": config.redact(f"{type(e).__name__}: {str(e)[:300]}")}], "isError": True}

    def handle(self, msg: dict) -> dict | None:
        mid, method, params = msg.get("id"), msg.get("method", ""), msg.get("params") or {}
        if mid is None:
            return None
        if method == "initialize":
            result = {"protocolVersion": params.get("protocolVersion") or PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": self.info}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_f, d, s) in self.tools.items()]}
        elif method == "tools/call":
            result = self.call(params.get("name", ""), params.get("arguments") or {})
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def serve(self, stdin=None, stdout=None) -> None:
        stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                reply = self.handle(msg) if isinstance(msg, dict) else {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
            except json.JSONDecodeError:
                reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            if reply is not None:
                stdout.write(json.dumps(reply) + "\n")
                stdout.flush()
