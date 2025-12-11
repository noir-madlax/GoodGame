from typing import Any
from .base import StateMutationNode
from ..state.state import AgentState
from ..llm.client import LLMClient

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
        # Logic to summarize
        
        # Dummy summary
        summary_prompt = f"Summarize data for: {input_data}"
        # response = self.llm_client.generate_text(summary_prompt)
        response = f"Summary for {input_data}: [Mock Data Copied]"
        return response

    def mutate_state(self, input_data: Any, state: AgentState, **kwargs) -> AgentState:
        # In this flow, input_data might be state.kols_to_search passed from main
        
        summary = self.run(state.kols_to_search)
        
        state.summary = summary
        state.current_step = "finished"
        return state

