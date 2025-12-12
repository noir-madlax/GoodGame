from typing import List, Dict, Any
from .state.state import AgentState
from .llm.client import LLMClient
from .node.search_node import SearchNode
from .node.summary_node import SummaryNode

from .tools.justoneapi import search_user, ApiResult
class SearchAgent:
    """
    KOL Search Agent
    """
    def __init__(self, api_key: str = None):
        self.llm = LLMClient(api_key=api_key)
        self.search_node = SearchNode(self.llm)
        self.summary_node = SummaryNode(self.llm)
        self.state = AgentState()

    def run(self, user_input: str, history: List[Dict[str, str]] = []) -> str:
        """
        Execute the agent flow
        """
        # Init state
        self.state.input_text = user_input
        self.state.messages = history
        
        # Step 1: Search
        # Pass user_input as input_data although node accesses state too if needed
        self.state = self.search_node.mutate_state(user_input, self.state)
        
        # Step 2: Summary
        # Pass kols_to_search as input_data or None, node uses state.kols_to_search
        self.state = self.summary_node.mutate_state(self.state.kols_to_search, self.state)
        
        return self.state.summary

    def get_state(self) -> Dict[str, Any]:
        return self.state.model_dump()

def execute_search_tool(tool_name: str, **kwargs) -> ApiResult:
    """
    Execute a search tool based on the provided tool name.
    
    Args:
        tool_name: The name of the tool to execute.
        **kwargs: Arguments to pass to the tool.
        
    Returns:
        The result of the tool execution.
    """
    if tool_name == "search_user":
        # Ensure keyword is present as it is required for search_user
        if "keyword" not in kwargs:
            return ApiResult(
                tool_name=tool_name,
                parameters=kwargs,
                error_message="Missing required argument: keyword"
            )
        return search_user(**kwargs)
    
    return ApiResult(
        tool_name=tool_name,
        parameters=kwargs,
        error_message=f"Tool '{tool_name}' not found"
    )
