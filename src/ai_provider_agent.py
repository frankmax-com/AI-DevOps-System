#!/usr/bin/env python3
"""
AI Provider Agent Service - Enterprise Meta-AI Router
=====================================================

Centralized AI service that intelligently routes requests to optimal AI providers
with automatic failover, cost optimization, and task-specific model selection.

Features:
- Multi-provider support (OpenAI, Anthropic, Google, Cohere, local models)
- Intelligent model selection based on task type
- Automatic failover and rate limit handling
- Cost tracking and budget management
- GitHub Copilot integration as premium fallback
- Request caching and optimization
- Enterprise governance and audit trails

Usage:
    python ai_provider_agent.py
    # Starts FastAPI service on port 8080
    
Environment Variables:
    AI_PROVIDER_CONFIG_PATH - Path to provider configuration file
    OPENAI_API_KEY - OpenAI API key
    ANTHROPIC_API_KEY - Anthropic API key
    GOOGLE_API_KEY - Google API key
    HUGGINGFACE_API_KEY - HuggingFace API key
    GITHUB_TOKEN - GitHub token for Copilot integration
"""

import asyncio
import json
import logging
import time
import hashlib
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from datetime import datetime, timedelta
import aiohttp
import subprocess
import sys
from pathlib import Path

# Optional imports - will gracefully degrade if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_provider_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TaskType(Enum):
    """AI task types for intelligent model selection"""
    THINKING = "thinking"          # Complex reasoning, analysis
    CODING = "coding"              # Code generation, debugging
    WRITING = "writing"            # Documentation, communication
    ANALYSIS = "analysis"          # Data analysis, insights
    TRANSLATION = "translation"    # Language translation
    SUMMARIZATION = "summarization" # Text summarization
    CLASSIFICATION = "classification" # Text/data classification
    CONVERSATION = "conversation"   # General chat, Q&A
    REVIEW = "review"              # Code/document review
    PLANNING = "planning"          # Project planning, requirements

class ProviderType(Enum):
    """AI provider types"""
    OPENAI_FREE = "openai_free"
    ANTHROPIC_FREE = "anthropic_free"
    GOOGLE_FREE = "google_free"
    COHERE_FREE = "cohere_free"
    HUGGINGFACE_FREE = "huggingface_free"
    LOCAL_MODEL = "local_model"
    GITHUB_COPILOT = "github_copilot"
    FALLBACK = "fallback"

@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: List[str] = field(default_factory=list)
    daily_limit: int = 1000  # requests per day
    rate_limit: int = 60     # requests per minute
    cost_per_token: float = 0.0
    priority: int = 1        # 1=highest, 10=lowest
    enabled: bool = True
    task_types: List[TaskType] = field(default_factory=list)

@dataclass
class AIRequest:
    """AI request with metadata"""
    task_type: TaskType
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    context: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    priority: int = 5  # 1=urgent, 10=background
    agent_id: Optional[str] = None  # Which agent is making the request

@dataclass
class AIResponse:
    """AI response with metadata"""
    content: str
    provider: ProviderType
    model: str
    tokens_used: int
    cost: float
    latency: float
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = ""

class RateLimiter:
    """Rate limiting for AI providers"""
    
    def __init__(self):
        self.requests = {}  # provider -> [(timestamp, count)]
    
    async def can_make_request(self, provider: ProviderType, limit: int) -> bool:
        """Check if request can be made within rate limits"""
        now = time.time()
        minute_ago = now - 60
        
        if provider not in self.requests:
            self.requests[provider] = []
        
        # Clean old requests
        self.requests[provider] = [
            (ts, count) for ts, count in self.requests[provider] 
            if ts > minute_ago
        ]
        
        # Count current minute requests
        current_count = sum(count for _, count in self.requests[provider])
        
        return current_count < limit
    
    async def record_request(self, provider: ProviderType):
        """Record a request for rate limiting"""
        now = time.time()
        if provider not in self.requests:
            self.requests[provider] = []
        self.requests[provider].append((now, 1))

class ModelSelector:
    """Intelligent model selection based on task type"""
    
    def __init__(self):
        # Task-specific model preferences
        self.task_models = {
            TaskType.THINKING: [
                ("claude-3-sonnet", ProviderType.ANTHROPIC_FREE),
                ("gpt-4o-mini", ProviderType.OPENAI_FREE),
                ("gemini-pro", ProviderType.GOOGLE_FREE)
            ],
            TaskType.CODING: [
                ("gpt-4o-mini", ProviderType.OPENAI_FREE),
                ("claude-3-haiku", ProviderType.ANTHROPIC_FREE),
                ("codellama-7b", ProviderType.HUGGINGFACE_FREE)
            ],
            TaskType.WRITING: [
                ("claude-3-haiku", ProviderType.ANTHROPIC_FREE),
                ("gpt-3.5-turbo", ProviderType.OPENAI_FREE),
                ("gemini-pro", ProviderType.GOOGLE_FREE)
            ],
            TaskType.ANALYSIS: [
                ("gpt-4o-mini", ProviderType.OPENAI_FREE),
                ("claude-3-sonnet", ProviderType.ANTHROPIC_FREE),
                ("gemini-pro", ProviderType.GOOGLE_FREE)
            ],
            TaskType.REVIEW: [
                ("claude-3-sonnet", ProviderType.ANTHROPIC_FREE),
                ("gpt-4o-mini", ProviderType.OPENAI_FREE)
            ],
            TaskType.PLANNING: [
                ("gpt-4o-mini", ProviderType.OPENAI_FREE),
                ("claude-3-sonnet", ProviderType.ANTHROPIC_FREE)
            ],
            TaskType.CONVERSATION: [
                ("gpt-3.5-turbo", ProviderType.OPENAI_FREE),
                ("claude-3-haiku", ProviderType.ANTHROPIC_FREE),
                ("gemini-pro", ProviderType.GOOGLE_FREE)
            ]
        }
    
    def select_model(self, task_type: TaskType, available_providers: List[ProviderConfig]) -> Optional[tuple]:
        """Select the best model for a task type"""
        preferences = self.task_models.get(task_type, [])
        
        for model, provider_type in preferences:
            # Find available provider
            for provider in available_providers:
                if (provider.provider_type == provider_type and 
                    provider.enabled and 
                    (not provider.models or model in provider.models)):
                    return (model, provider)
        
        # Fallback to any available provider
        if available_providers:
            provider = available_providers[0]
            model = provider.models[0] if provider.models else "default"
            return (model, provider)
        
        return None

class AIProviderAgent:
    """Main AI Provider Agent Service"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.providers = {}
        self.rate_limiter = RateLimiter()
        self.model_selector = ModelSelector()
        self.request_cache = {}  # Simple in-memory cache
        self.usage_stats = {}
        
        # Load configuration
        if not config_path:
            config_path = os.getenv('AI_PROVIDER_CONFIG_PATH', 'ai_providers_config.json')
        
        self.load_config(config_path)
        
        # Initialize clients
        self._initialize_clients()
    
    def load_config(self, config_path: str):
        """Load AI provider configurations"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                for provider_data in config_data.get('providers', []):
                    provider = ProviderConfig(
                        provider_type=ProviderType(provider_data['type']),
                        api_key=provider_data.get('api_key'),
                        base_url=provider_data.get('base_url'),
                        models=provider_data.get('models', []),
                        daily_limit=provider_data.get('daily_limit', 1000),
                        rate_limit=provider_data.get('rate_limit', 60),
                        cost_per_token=provider_data.get('cost_per_token', 0.0),
                        priority=provider_data.get('priority', 5),
                        enabled=provider_data.get('enabled', True),
                        task_types=[TaskType(t) for t in provider_data.get('task_types', [])]
                    )
                    self.providers[provider.provider_type] = provider
            else:
                self.logger.warning(f"Config file {config_path} not found, using defaults")
                self._load_default_config()
                
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default free provider configuration"""
        default_providers = [
            ProviderConfig(
                provider_type=ProviderType.OPENAI_FREE,
                models=["gpt-3.5-turbo", "gpt-4o-mini"],
                daily_limit=200,  # Conservative estimate for free tier
                rate_limit=3,     # RPM for free tier
                priority=2,
                enabled=OPENAI_AVAILABLE
            ),
            ProviderConfig(
                provider_type=ProviderType.ANTHROPIC_FREE,
                models=["claude-3-haiku", "claude-3-sonnet"],
                daily_limit=100,
                rate_limit=5,
                priority=1,
                enabled=ANTHROPIC_AVAILABLE
            ),
            ProviderConfig(
                provider_type=ProviderType.GOOGLE_FREE,
                models=["gemini-pro", "gemini-1.5-flash"],
                daily_limit=1500,
                rate_limit=60,
                priority=3,
                enabled=GOOGLE_AVAILABLE
            ),
            ProviderConfig(
                provider_type=ProviderType.HUGGINGFACE_FREE,
                models=["microsoft/DialoGPT-large", "microsoft/CodeBERT-base"],
                daily_limit=10000,
                rate_limit=100,
                priority=4,
                enabled=TRANSFORMERS_AVAILABLE
            ),
            ProviderConfig(
                provider_type=ProviderType.GITHUB_COPILOT,
                models=["copilot-chat"],
                daily_limit=1000,
                rate_limit=60,
                priority=1,  # High priority fallback
                enabled=False  # Enable when needed
            ),
            ProviderConfig(
                provider_type=ProviderType.FALLBACK,
                models=["fallback"],
                daily_limit=999999,
                rate_limit=1000,
                priority=10,  # Lowest priority
                enabled=True
            )
        ]
        
        for provider in default_providers:
            self.providers[provider.provider_type] = provider
    
    def _initialize_clients(self):
        """Initialize AI provider clients"""
        self.clients = {}
        
        # OpenAI client
        if ProviderType.OPENAI_FREE in self.providers and OPENAI_AVAILABLE:
            openai_config = self.providers[ProviderType.OPENAI_FREE]
            api_key = openai_config.api_key or os.getenv('OPENAI_API_KEY')
            if api_key:
                self.clients[ProviderType.OPENAI_FREE] = openai.OpenAI(api_key=api_key)
                openai_config.enabled = True
        
        # Anthropic client
        if ProviderType.ANTHROPIC_FREE in self.providers and ANTHROPIC_AVAILABLE:
            anthropic_config = self.providers[ProviderType.ANTHROPIC_FREE]
            api_key = anthropic_config.api_key or os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.clients[ProviderType.ANTHROPIC_FREE] = Anthropic(api_key=api_key)
                anthropic_config.enabled = True
        
        # Google client
        if ProviderType.GOOGLE_FREE in self.providers and GOOGLE_AVAILABLE:
            google_config = self.providers[ProviderType.GOOGLE_FREE]
            api_key = google_config.api_key or os.getenv('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.clients[ProviderType.GOOGLE_FREE] = genai
                google_config.enabled = True
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Main entry point for AI requests with intelligent routing"""
        start_time = time.time()
        request_id = hashlib.md5(f"{request.prompt[:100]}{time.time()}".encode()).hexdigest()[:8]
        
        self.logger.info(f"[{request_id}] Processing {request.task_type.value} request from {request.agent_id or 'unknown'}")
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        if cache_key in self.request_cache:
            cached_response = self.request_cache[cache_key]
            cached_response.cached = True
            cached_response.request_id = request_id
            self.logger.info(f"[{request_id}] Returning cached response")
            return cached_response
        
        # Get available providers for this task
        available_providers = self._get_available_providers(request.task_type)
        
        if not available_providers:
            # Use fallback provider
            return await self._use_fallback(request, request_id)
        
        # Select optimal model
        model_selection = self.model_selector.select_model(request.task_type, available_providers)
        if not model_selection:
            return await self._use_fallback(request, request_id)
        
        model, provider_config = model_selection
        
        # Try providers with failover
        for provider_config in available_providers:
            try:
                # Check rate limits
                if not await self.rate_limiter.can_make_request(
                    provider_config.provider_type, 
                    provider_config.rate_limit
                ):
                    self.logger.warning(f"[{request_id}] Rate limit reached for {provider_config.provider_type.value}")
                    continue
                
                # Make request
                response = await self._make_provider_request(request, provider_config, model, request_id)
                
                # Record usage
                await self.rate_limiter.record_request(provider_config.provider_type)
                self._update_usage_stats(provider_config.provider_type, response.tokens_used)
                
                # Cache response
                self.request_cache[cache_key] = response
                
                response.latency = time.time() - start_time
                response.request_id = request_id
                
                self.logger.info(f"[{request_id}] Success with {provider_config.provider_type.value} ({response.latency:.2f}s)")
                return response
                
            except Exception as e:
                self.logger.warning(f"[{request_id}] Provider {provider_config.provider_type.value} failed: {e}")
                continue
        
        # All providers failed, use fallback
        return await self._use_fallback(request, request_id)
    
    def _get_available_providers(self, task_type: TaskType) -> List[ProviderConfig]:
        """Get available providers sorted by priority and suitability"""
        available = []
        
        for provider in self.providers.values():
            if provider.provider_type == ProviderType.FALLBACK:
                continue  # Handle fallback separately
                
            if (provider.enabled and 
                (not provider.task_types or task_type in provider.task_types)):
                # Check daily limits
                if self._check_daily_limit(provider.provider_type):
                    available.append(provider)
        
        # Sort by priority (lower number = higher priority)
        return sorted(available, key=lambda p: p.priority)
    
    def _check_daily_limit(self, provider_type: ProviderType) -> bool:
        """Check if provider is within daily limits"""
        today = datetime.now().date()
        usage_key = f"{provider_type.value}_{today}"
        
        daily_usage = self.usage_stats.get(usage_key, 0)
        daily_limit = self.providers[provider_type].daily_limit
        
        return daily_usage < daily_limit
    
    async def _make_provider_request(self, request: AIRequest, provider: ProviderConfig, model: str, request_id: str) -> AIResponse:
        """Make request to specific provider"""
        self.logger.debug(f"[{request_id}] Calling {provider.provider_type.value} with model {model}")
        
        if provider.provider_type == ProviderType.OPENAI_FREE:
            return await self._call_openai(request, model, request_id)
        elif provider.provider_type == ProviderType.ANTHROPIC_FREE:
            return await self._call_anthropic(request, model, request_id)
        elif provider.provider_type == ProviderType.GOOGLE_FREE:
            return await self._call_google(request, model, request_id)
        elif provider.provider_type == ProviderType.HUGGINGFACE_FREE:
            return await self._call_huggingface(request, model, request_id)
        elif provider.provider_type == ProviderType.GITHUB_COPILOT:
            return await self._call_github_copilot(request, model, request_id)
        else:
            raise Exception(f"Provider {provider.provider_type} not implemented")
    
    async def _call_openai(self, request: AIRequest, model: str, request_id: str) -> AIResponse:
        """Call OpenAI API"""
        client = self.clients.get(ProviderType.OPENAI_FREE)
        if not client:
            raise Exception("OpenAI client not initialized")
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else len(content.split()) * 1.3
        
        return AIResponse(
            content=content,
            provider=ProviderType.OPENAI_FREE,
            model=model,
            tokens_used=int(tokens_used),
            cost=tokens_used * self.providers[ProviderType.OPENAI_FREE].cost_per_token,
            latency=0  # Will be set by caller
        )
    
    async def _call_anthropic(self, request: AIRequest, model: str, request_id: str) -> AIResponse:
        """Call Anthropic API"""
        client = self.clients.get(ProviderType.ANTHROPIC_FREE)
        if not client:
            raise Exception("Anthropic client not initialized")
        
        response = await asyncio.to_thread(
            client.messages.create,
            model=model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt or "",
            messages=[{"role": "user", "content": request.prompt}]
        )
        
        content = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        return AIResponse(
            content=content,
            provider=ProviderType.ANTHROPIC_FREE,
            model=model,
            tokens_used=tokens_used,
            cost=tokens_used * self.providers[ProviderType.ANTHROPIC_FREE].cost_per_token,
            latency=0
        )
    
    async def _call_google(self, request: AIRequest, model: str, request_id: str) -> AIResponse:
        """Call Google Gemini API"""
        if ProviderType.GOOGLE_FREE not in self.clients:
            raise Exception("Google client not initialized")
            
        model_instance = genai.GenerativeModel(model)
        
        prompt_text = request.prompt
        if request.system_prompt:
            prompt_text = f"{request.system_prompt}\n\n{request.prompt}"
        
        response = await asyncio.to_thread(
            model_instance.generate_content,
            prompt_text,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=request.max_tokens,
                temperature=request.temperature
            )
        )
        
        content = response.text
        # Estimate tokens (Google doesn't always provide usage)
        tokens_used = len(content.split()) * 1.3  # Rough estimation
        
        return AIResponse(
            content=content,
            provider=ProviderType.GOOGLE_FREE,
            model=model,
            tokens_used=int(tokens_used),
            cost=0,  # Free tier
            latency=0
        )
    
    async def _call_huggingface(self, request: AIRequest, model: str, request_id: str) -> AIResponse:
        """Call Hugging Face models"""
        if not TRANSFORMERS_AVAILABLE:
            raise Exception("Transformers library not available")
            
        # Use local pipeline for Hugging Face models
        try:
            pipe = pipeline("text-generation", model=model, device=-1)  # CPU
            
            prompt_text = request.prompt
            if request.system_prompt:
                prompt_text = f"{request.system_prompt}\n\n{request.prompt}"
            
            response = await asyncio.to_thread(
                pipe,
                prompt_text,
                max_length=request.max_tokens,
                temperature=request.temperature,
                do_sample=True
            )
            
            content = response[0]['generated_text']
            tokens_used = len(content.split()) * 1.3
            
            return AIResponse(
                content=content,
                provider=ProviderType.HUGGINGFACE_FREE,
                model=model,
                tokens_used=int(tokens_used),
                cost=0,  # Free local execution
                latency=0
            )
        except Exception as e:
            raise Exception(f"HuggingFace model error: {e}")
    
    async def _call_github_copilot(self, request: AIRequest, model: str, request_id: str) -> AIResponse:
        """Call GitHub Copilot (placeholder implementation)"""
        # This would integrate with GitHub Copilot API when available
        # For now, return a placeholder response
        
        return AIResponse(
            content="GitHub Copilot integration not yet implemented",
            provider=ProviderType.GITHUB_COPILOT,
            model=model,
            tokens_used=0,
            cost=0,
            latency=0
        )
    
    async def _use_fallback(self, request: AIRequest, request_id: str) -> AIResponse:
        """Use fallback response when all providers fail"""
        self.logger.warning(f"[{request_id}] All providers failed, using fallback")
        
        # Simple rule-based fallback responses
        fallback_responses = {
            TaskType.CODING: "I'm unable to generate code at the moment. Please check the AI provider configuration and try again.",
            TaskType.ANALYSIS: "I'm unable to perform analysis at the moment. Please check the AI provider configuration and try again.",
            TaskType.WRITING: "I'm unable to assist with writing at the moment. Please check the AI provider configuration and try again.",
            TaskType.REVIEW: "I'm unable to perform reviews at the moment. Please check the AI provider configuration and try again.",
            TaskType.PLANNING: "I'm unable to assist with planning at the moment. Please check the AI provider configuration and try again.",
            TaskType.THINKING: "I'm unable to assist with complex reasoning at the moment. Please check the AI provider configuration and try again.",
            TaskType.CONVERSATION: "I'm unable to have a conversation at the moment. Please check the AI provider configuration and try again."
        }
        
        content = fallback_responses.get(request.task_type, "AI services are temporarily unavailable. Please try again later.")
        
        return AIResponse(
            content=content,
            provider=ProviderType.FALLBACK,
            model="fallback",
            tokens_used=len(content.split()),
            cost=0,
            latency=0
        )
    
    def _generate_cache_key(self, request: AIRequest) -> str:
        """Generate cache key for request"""
        key_data = f"{request.task_type.value}:{request.prompt}:{request.system_prompt}:{request.temperature}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _update_usage_stats(self, provider_type: ProviderType, tokens_used: int):
        """Update usage statistics"""
        today = datetime.now().date()
        usage_key = f"{provider_type.value}_{today}"
        
        if usage_key not in self.usage_stats:
            self.usage_stats[usage_key] = 0
        
        self.usage_stats[usage_key] += tokens_used
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage statistics report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'daily_usage': self.usage_stats,
            'available_providers': [
                {
                    'type': p.provider_type.value,
                    'enabled': p.enabled,
                    'daily_limit': p.daily_limit,
                    'priority': p.priority,
                    'models': p.models
                } for p in self.providers.values()
            ],
            'cache_size': len(self.request_cache),
            'total_providers': len([p for p in self.providers.values() if p.enabled])
        }

# FastAPI service wrapper (optional, requires: pip install fastapi uvicorn)
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
    
    class ChatRequest(BaseModel):
        message: str
        task_type: str = "conversation"
        system_prompt: Optional[str] = None
        max_tokens: int = 2000
        temperature: float = 0.7
        user_id: Optional[str] = None
        agent_id: Optional[str] = None

    class ChatResponse(BaseModel):
        response: str
        provider: str
        model: str
        tokens_used: int
        cost: float
        latency: float
        cached: bool
        request_id: str

    # Initialize FastAPI app
    app = FastAPI(
        title="AI Provider Agent Service", 
        version="1.0.0",
        description="Enterprise Meta-AI Router for AI DevOps Ecosystem"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Global AI agent instance
    ai_agent = AIProviderAgent()

    @app.post("/chat", response_model=ChatResponse)
    async def chat_endpoint(request: ChatRequest):
        """Main chat endpoint for AI requests"""
        try:
            ai_request = AIRequest(
                task_type=TaskType(request.task_type),
                prompt=request.message,
                system_prompt=request.system_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                user_id=request.user_id,
                agent_id=request.agent_id
            )
            
            response = await ai_agent.process_request(ai_request)
            
            return ChatResponse(
                response=response.content,
                provider=response.provider.value,
                model=response.model,
                tokens_used=response.tokens_used,
                cost=response.cost,
                latency=response.latency,
                cached=response.cached,
                request_id=response.request_id
            )
            
        except Exception as e:
            logger.error(f"Chat endpoint error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "service": "AI Provider Agent Service",
            "version": "1.0.0"
        }

    @app.get("/usage")
    async def usage_stats():
        """Get usage statistics"""
        return ai_agent.get_usage_report()

    @app.get("/providers")
    async def list_providers():
        """List available AI providers"""
        return [
            {
                "type": p.provider_type.value,
                "enabled": p.enabled,
                "models": p.models,
                "daily_limit": p.daily_limit,
                "priority": p.priority
            } for p in ai_agent.providers.values()
        ]

    @app.post("/reload-config")
    async def reload_config():
        """Reload provider configuration"""
        try:
            config_path = os.getenv('AI_PROVIDER_CONFIG_PATH', 'ai_providers_config.json')
            ai_agent.load_config(config_path)
            ai_agent._initialize_clients()
            return {"status": "success", "message": "Configuration reloaded"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available. Running in standalone mode.")

if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        # Run FastAPI server
        try:
            import uvicorn
            logger.info("Starting AI Provider Agent Service on port 8080")
            uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
        except ImportError:
            logger.error("uvicorn not available. Please install: pip install fastapi uvicorn")
            sys.exit(1)
    else:
        # Run standalone test
        async def test_standalone():
            agent = AIProviderAgent()
            
            test_request = AIRequest(
                task_type=TaskType.CONVERSATION,
                prompt="Hello, how are you?",
                agent_id="test-agent"
            )
            
            response = await agent.process_request(test_request)
            print(f"Response: {response.content}")
            print(f"Provider: {response.provider.value}")
            print(f"Usage Report: {agent.get_usage_report()}")
        
        logger.info("Running standalone test...")
        asyncio.run(test_standalone())
