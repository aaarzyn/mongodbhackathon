"""Base agent class and interfaces for multi-agent recommendation system."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ContextFormat(str, Enum):
    """Format for agent-to-agent context passing."""

    JSON = "json"
    MARKDOWN = "markdown"


class AgentContext(BaseModel):
    """Context passed between agents.
    
    This captures the information flow and metadata for evaluation.
    """

    agent_name: str = Field(..., description="Name of the agent producing this context")
    format: ContextFormat = Field(..., description="Format of the context data")
    data: Dict[str, Any] = Field(..., description="The actual context data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When context was created"
    )
    tokens: Optional[int] = Field(
        default=None, description="Token count of the context"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "UserProfilerAgent",
                "format": "json",
                "data": {
                    "user_id": "123",
                    "top_genres": ["Sci-Fi", "Thriller"],
                },
                "tokens": 245,
                "metadata": {"model": "granite-4.0"},
            }
        }


class AgentOutput(BaseModel):
    """Output from an agent including context and execution info."""

    context: AgentContext = Field(..., description="Context produced by the agent")
    execution_time_ms: float = Field(
        ..., description="Time taken to execute the agent in milliseconds"
    )
    success: bool = Field(default=True, description="Whether execution was successful")
    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "context": {
                    "agent_name": "UserProfilerAgent",
                    "format": "json",
                    "data": {"user_id": "123"},
                },
                "execution_time_ms": 125.5,
                "success": True,
            }
        }


class Agent(ABC):
    """Base class for all agents in the recommendation pipeline.
    
    Each agent processes input context and produces output context
    that can be evaluated for fidelity and drift.
    """

    def __init__(self, name: str, context_format: ContextFormat = ContextFormat.JSON):
        """Initialize the agent.
        
        Args:
            name: Name of the agent.
            context_format: Format for context output (JSON or Markdown).
        """
        self.name = name
        self.context_format = context_format

    @abstractmethod
    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        """Process input context and produce output context.
        
        Args:
            input_context: Context from previous agent (None for first agent).
            
        Returns:
            AgentOutput with context and execution metadata.
        """
        pass

    def _create_context(
        self, data: Dict[str, Any], tokens: Optional[int] = None, **metadata
    ) -> AgentContext:
        """Helper to create context output.
        
        Args:
            data: Context data dictionary.
            tokens: Optional token count.
            **metadata: Additional metadata.
            
        Returns:
            AgentContext object.
        """
        return AgentContext(
            agent_name=self.name,
            format=self.context_format,
            data=data,
            tokens=tokens,
            metadata=metadata,
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count.
        
        Uses simple heuristic: ~4 characters per token.
        
        Args:
            text: Text to estimate tokens for.
            
        Returns:
            Estimated token count.
        """
        return len(text) // 4

