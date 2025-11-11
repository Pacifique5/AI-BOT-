from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import os
import httpx
from dotenv import load_dotenv
from pathlib import Path
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load .env file from the backend directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

if not API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

app = FastAPI(
    title="AI Chatbot API",
    description="Backend API for AI Chatbot application",
    version="1.0.0"
)

# Add CORS middleware to handle cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatItem(BaseModel):
    role: str = Field(..., description="Role of the message sender (user, assistant, or system)")
    content: str = Field(..., min_length=1, description="Content of the message")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed_roles = ['user', 'assistant', 'system']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v

class ChatRequest(BaseModel):
    messages: list[ChatItem] = Field(..., min_length=1, description="List of chat messages")
    persona: Optional[str] = Field(None, description="System persona/prompt for the AI")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature for response generation")
    model: Optional[str] = Field(None, description="Model to use for chat completion")

class ChatResponse(BaseModel):
    error: bool
    reply: Optional[str] = None
    status: Optional[int] = None
    detail: Optional[dict] = None

class HealthResponse(BaseModel):
    status: str
    api_configured: bool

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify API status"""
    return {
        "status": "healthy",
        "api_configured": bool(API_KEY)
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Chatbot API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Chat endpoint that processes messages and returns AI responses.
    
    - **messages**: List of chat messages with role and content
    - **persona**: Optional system persona/prompt
    - **temperature**: Optional temperature (0.0-2.0) for response generation
    - **model**: Optional model name to override default
    """
    try:
        # Validate messages
        if not req.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty")
        
        # Prepare system prompt
        system_prompt = req.persona or "You are a helpful assistant."
        
        # Build API messages
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add user messages (filter out system messages from user input)
        for msg in req.messages:
            if msg.role != "system":  # Don't allow system messages in user input
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare payload
        payload = {
            "model": req.model or MODEL,
            "messages": api_messages,
            "temperature": req.temperature if req.temperature is not None else TEMPERATURE,
        }
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Sending request to OpenAI API with model: {payload['model']}")
        
        # Make async HTTP request
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                resp = await client.post(
                    f"{API_BASE}/chat/completions",
                    json=payload,
                    headers=headers
                )
                resp.raise_for_status()
                
            except httpx.TimeoutException:
                logger.error("Request to OpenAI API timed out")
                raise HTTPException(
                    status_code=504,
                    detail="Request to OpenAI API timed out. Please try again."
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
                error_detail = {}
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = {"message": e.response.text}
                
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail={
                        "message": "OpenAI API error",
                        "error": error_detail
                    }
                )
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail="Failed to connect to OpenAI API. Please check your network connection."
                )
        
        # Parse response
        data = resp.json()
        
        if not data.get("choices") or len(data["choices"]) == 0:
            logger.error("No choices in OpenAI response")
            raise HTTPException(
                status_code=500,
                detail="Invalid response from OpenAI API"
            )
        
        assistant_reply = data["choices"][0]["message"]["content"]
        logger.info("Successfully received response from OpenAI API")
        
        return {
            "error": False,
            "reply": assistant_reply
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# Exception handler for validation errors
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": True, "detail": {"message": str(exc)}}
    )