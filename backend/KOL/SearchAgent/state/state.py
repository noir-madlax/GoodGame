from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """
    KOL Search Agent State
    """
    messages: List[Dict[str, str]] = Field(default_factory=list, description="Conversation history")
    input_text: str = Field(default="", description="User input text")
    kols_to_search: List[str] = Field(default_factory=list, description="List of KOL names to search")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="Raw search results from tools")
    summary: str = Field(default="", description="Final summary of the analysis")
    current_step: str = Field(default="init", description="Current step in the agent flow")
