import hashlib
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Exam MCP Server")

# Const configurations assigned by the challenge parameters
NORMALIZED_EMAIL = "21f3001574@ds.study.iitm.ac.in"

# ----------------------------------------------------------------
# Pydantic Schemas for MCP JSON-RPC 2.0 Compliance
# ----------------------------------------------------------------
class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

# ----------------------------------------------------------------
# Protocol Core Routing Hook
# ----------------------------------------------------------------
@app.post("/")
@app.post("/mcp")
async def handle_mcp_request(
    request: Request, 
    rpc_req: JsonRpcRequest,
    x_exam_challenge: Optional[str] = Header(None, alias="X-Exam-Challenge"),
    x_exam_timestamp: Optional[str] = Header(None, alias="X-Exam-Timestamp")
):
    method = rpc_req.method

    # 1. Handle MCP Initialization Handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_req.id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "exam-challenge-solver",
                    "version": "1.0.0"
                }
            }
        }

    # 2. Handle Initialized Notification
    elif method == "notifications/initialized":
        return None  # Notifications do not return a standard JSON-RPC response block

    # 3. Handle Tool Listing Request
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_req.id,
            "result": {
                "tools": [
                    {
                        "name": "solve_challenge",
                        "description": "Exposes the core challenge solver framework for verification.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }

    # 4. Handle Live Tool Executions
    elif method == "tools/call":
        # Extract name targeting our specific endpoint function signature
        params = rpc_req.params or {}
        tool_name = params.get("name")
        
        if tool_name != "solve_challenge":
            return {
                "jsonrpc": "2.0",
                "id": rpc_req.id,
                "error": {
                    "code": -32601,
                    "message": f"Method tool name '{tool_name}' not found."
                }
            }

        # CRITICAL REQ: Read the challenge from HTTP headers, not the JSON body parameters
        if not x_exam_challenge:
            return {
                "jsonrpc": "2.0",
                "id": rpc_req.id,
                "error": {
                    "code": -32000,
                    "message": "Missing required 'X-Exam-Challenge' execution header."
                }
            }

        # Calculate Text Content Block Response: SHA-256("${challenge}:${normalizedEmail}")
        raw_hash_input = f"{x_exam_challenge}:{NORMALIZED_EMAIL}"
        sha256_hash = hashlib.sha256(raw_hash_input.encode('utf-8')).hexdigest()
        
        # Extract strictly the first 16 lowercase hex characters
        truncated_solution = sha256_hash[:16].lower()

        return {
            "jsonrpc": "2.0",
            "id": rpc_req.id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": truncated_solution
                    }
                ]
            }
        }

    # Fallback for unrecognized protocol primitives
    return {
        "jsonrpc": "2.0",
        "id": rpc_req.id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not implemented."
        }
    }
