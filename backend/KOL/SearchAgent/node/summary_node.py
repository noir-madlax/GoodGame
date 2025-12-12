from typing import Any
from .base import StateMutationNode
from ..state.state import AgentState
from .base import StateMutationNode
from ..state.state import AgentState
from ..llm.client import LLMClient
from ..prompts.prompts import SYSTEM_PROMPT_SUMMARY
import json

class SummaryNode(StateMutationNode):
    """
    Node 2: Summary Node
    Responsibility:
    - Summarize the search results using LLM
    """
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client, node_name="SummaryNode")

    def run(self, input_data: Any, **kwargs) -> Any:
        self.log_info("Executing Summary Node")
        
        user_requirement = kwargs.get("user_requirement", "")
        search_results = input_data
        
        # Format search results for prompt
        results_str = json.dumps(search_results, ensure_ascii=False, indent=2)
        
        full_prompt = f"{SYSTEM_PROMPT_SUMMARY}\n\nUser Requirement:\n{user_requirement}\n\nSearch Results:\n{results_str}"
        
        self.log_info(f"Generating summary for {len(search_results) if isinstance(search_results, list) else 0} results...")
        
        # Call LLM
        response = self.llm_client.generate_text(full_prompt)
        
        self.log_info(f"Summary generated: {response[:100]}...") # Log first 100 chars
        return response

    def mutate_state(self, input_data: Any, state: AgentState, **kwargs) -> AgentState:
        # Pass search_results as main input, and user input as requirement
        
        summary = self.run(state.search_results, user_requirement=state.input_text)
        
        state.summary = summary
        state.current_step = "finished"
        return state

