class Prompts:
    EXTRACT_KOL_NAMES = """
    You are an assistant that extracts KOL (Key Opinion Leader) names from a conversation.
    User Input: {input}
    Output a JSON list of names: ["name1", "name2"]
    """
    
    SUMMARIZE_SEARCH_RESULTS = """
    Summarize the following KOL search results into a concise report.
    Data: {data}
    Report:
    """
