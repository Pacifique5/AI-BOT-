from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
import httpx
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    loaded = []
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value
        loaded.append(key)
    logger.info("Loaded env vars: %s", ", ".join(loaded))
else:
    logger.warning(".env file not found at %s", env_file)

API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

if not API_KEY:
    raise ValueError(f"OPENAI_API_KEY not found. Add it to {env_file}")

logger.info("OpenAI API configured: model=%s, base=%s", MODEL, API_BASE)

app = FastAPI(title="AI Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant | system")
    content: str = Field(..., min_length=1, description="message text")

class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    persona: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    model: Optional[str] = None

class ChatResponse(BaseModel):
    error: bool
    reply: Optional[str] = None
    status: Optional[int] = None
    detail: Optional[dict] = None

class HealthResponse(BaseModel):
    status: str
    api_configured: bool

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "healthy", "api_configured": bool(API_KEY)}

@app.get("/")
async def root():
    return {"message": "AI Chatbot API", "docs": "/docs"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        system_prompt = req.persona or "You are a helpful assistant."
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in req.messages:
            if msg.role != "system":
                api_messages.append({"role": msg.role, "content": msg.content})

        if len(api_messages) == 1:
            raise HTTPException(
                status_code=400,
                detail={"error": True, "status": 400,
                        "detail": {"message": "Include at least one user/assistant message"}}
            )

        payload = {
            "model": req.model or MODEL,
            "messages": api_messages,
            "temperature": req.temperature if req.temperature is not None else TEMPERATURE,
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(TIMEOUT, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        if not data.get("choices"):
            raise HTTPException(
                status_code=500,
                detail={"error": True, "status": 500,
                        "detail": {"message": "OpenAI response missing choices"}}
            )

        message_payload = data["choices"][0].get("message", {})

        def extract_text(payload):
            content = payload.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for chunk in content:
                    if isinstance(chunk, dict):
                        if "text" in chunk:
                            parts.append(chunk["text"])
                        elif chunk.get("type") == "output_text" and "content" in chunk:
                            parts.append(chunk["content"])
                        elif chunk.get("type") == "message" and "text" in chunk:
                            parts.append(chunk["text"])
                        else:
                            parts.append(str(chunk))
                    else:
                        parts.append(str(chunk))
                return "".join(parts)
            if isinstance(content, dict):
                if "text" in content:
                    return content["text"]
                return str(content)
            return ""

        assistant_reply = extract_text(message_payload)
        if not assistant_reply:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": True,
                    "status": 500,
                    "detail": {"message": "OpenAI response missing text content"}
                }
            )
        return {"error": False, "reply": assistant_reply}

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail={"error": True, "status": 504,
                    "detail": {"message": "OpenAI request timed out"}}
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json() if exc.response.content else {"message": exc.response.text}
        raise HTTPException(
            status_code=exc.response.status_code,
            detail={"error": True, "status": exc.response.status_code,
                    "detail": {"message": "OpenAI API error", "error": detail}}
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": True, "status": 503,
                    "detail": {"message": f"Network error: {exc}"}}
        )
    except Exception as exc:
        logger.exception("Unexpected error")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "status": 500,
                    "detail": {"message": f"Internal server error: {exc}"}}
        )
