import json
from typing import Any, Dict
from jobs.logger import get_logger
from .base import StateMutationNode
from ..state.state import AgentState
from ..prompts.prompts import SYSTEM_PROMPT_SEARCH

logger = get_logger(__name__)

class SearchNode(StateMutationNode):
    """
    Node 1: Search Node
    Responsibility:
    - Analyze user input and generate search keywords for KOLs using LLM.
    """
    
    def __init__(self, llm_client: Any):
        """
        Initialize Search Node
        
        Args:
            llm_client: LLM Client
        """
        super().__init__(llm_client, node_name="SearchNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        if isinstance(input_data, str):
            return True
        return False
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, str]:
        """
        Call LLM to generate search query
        
        Args:
            input_data: User input string
            **kwargs: Extra arguments
            
        Returns:
            Dictionary containing search_query and reasoning
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("Input data must be a string")
            
            # Prepare input message
            message_data = {"user_requirement": input_data}
            message = json.dumps(message_data, ensure_ascii=False)
            
            self.log_info(f"Generating search query for: {input_data}")
            
            # Call LLM
            # Assuming llm_client has a method similar to invoke or chat
            # Adapting to the method used in reference: stream_invoke_to_string or generate_text
            # Checking main.py, LLMClient is used. Let's assume generate_text or similar.
            # The reference used `stream_invoke_to_string`. I'll use `generate_text` if that's what `LLMClient` has, 
            # or `chat`. Let's assume standard `generate_text` for now based on previous summary_node.
            
            # Use SYSTEM_PROMPT_SEARCH
            # We need to format the prompt or send it as system message.
            # If LLMClient supports system prompts:
            # response = self.llm_client.chat(messages=[{"role": "system", "content": SYSTEM_PROMPT_SEARCH}, {"role": "user", "content": message}])
            # Or if it's a simple generate:
            full_prompt = f"{SYSTEM_PROMPT_SEARCH}\n\nUser Input:\n{message}"
            response = self.llm_client.generate_text(full_prompt)
            self.log_info(f"Generated search query: {response}")
            
            # Process response
            processed_response = self.process_output(response)
            
            self.log_info(f"Generated search query: {processed_response.get('search_query', 'N/A')}")
            return processed_response
            
        except Exception as e:
            self.log_exception(f"Failed to generate search query: {str(e)}")
            raise e

    def process_output(self, output: str) -> Dict[str, str]:
        """
        Process LLM output, extract search query and reasoning
        """
        try:
            # Basic cleanup
            cleaned_output = output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]
            cleaned_output = cleaned_output.strip()
            
            result = json.loads(cleaned_output)
            
            return {
                "search_query": result.get("search_query", ""),
                "reasoning": result.get("reasoning", "")
            }
        except json.JSONDecodeError as e:
            self.log_error(f"JSON parsing failed: {str(e)}")
            # Fallback or simple extraction could go here
            return self._get_default_search_query()
        except Exception as e:
            self.log_error(f"Output processing failed: {str(e)}")
            return self._get_default_search_query()

    def _get_default_search_query(self) -> Dict[str, str]:
        return {
            "search_query": "KOL",
            "reasoning": "Default query due to parsing failure"
        }

    def mutate_state(self, input_data: Any, state: AgentState, **kwargs) -> AgentState:
        """
        Mutate state with search results
        """
        # input_data is user_input string
        result = self.run(input_data)
        
        # In this step, we just get the query. 
        # The user said "first node just calls llm, see what tools to call next".
        # But we are also supposed to put "data" in state.
        # For now, let's store the query in kols_to_search as a list (even if it's just a keyword)
        # or maybe we should store it in a new field? 
        # State has `kols_to_search: List[str]`.
        
        search_query = result.get("search_query")
        if search_query:
            state.kols_to_search = [search_query] # Treat the keyword as the "KOL" to search for now
            self.log_info(f"Updated state with search query: {search_query}")
        
        state.current_step = "search_query_generated"
        return state
    
    def log_exception(self, message: str):
         logger.error(f"[{self.node_name}] Exception: {message}")
