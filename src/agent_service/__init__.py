"""
Agent Service Package - Provides a central AI agent that orchestrates requests.

This package serves as the main entry point for client requests,
with the agent determining how to route and process them.
"""

from .agent_service import AgentService

__all__ = ["AgentService"]