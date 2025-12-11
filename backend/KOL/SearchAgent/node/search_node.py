from typing import Any
from .base import StateMutationNode
from ..state.state import AgentState
from ..llm.client import LLMClient

class SearchNode(StateMutationNode):
    """
    Node 1: Search Node
    Responsibility: 
    - Parse user input to identify KOLs (using LLM or regex)
    - Call tools to fetch data (Deferred)
    """
    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client, node_name="SearchNode")

    def run(self, input_data: Any, **kwargs) -> Any:
        self.log_info("Executing Search Node")
        # Logic to extract KOL names and calling tools would go here
        
        # Simulating finding KOLs for structure verification
        # 1. Use LLM to extract names
        # 2. Call crawler tool for each name
        
        # Return dummy data to be used in mutate_state
        return ["DemoKOL1", "DemoKOL2"]

    def mutate_state(self, input_data: Any, state: AgentState, **kwargs) -> AgentState:
        # Get result from run logic (or call it here if design dictates)
        # Assuming run is called separately or we put logic here.
        # The base class doesn't enforce calling run inside mutate_state, 
        # but typically we execute logic then update state.
        
        # Let's assume run() returns the data we need to update state with.
        # But wait, main.py calls run(state). 
        # BaseNode.run signature is (input_data, **kwargs).
        
        self.log_info("Mutating state with search results")
        kols = self.run(input_data)
        
        state.kols_to_search = kols
        state.current_step = "search_complete"
        return state

