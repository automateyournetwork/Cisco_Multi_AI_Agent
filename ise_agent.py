# ISE_Agent.py

import os
import json
import logging
import requests
import difflib
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool, render_text_description
import urllib3

# Configure logging at the start of your script
logging.basicConfig(level=logging.INFO)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ISEController for ISE Authentication and GET Operations
class ISEController:
    def __init__(self, ise_url, username, password):
        self.ise = ise_url.rstrip('/')
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # GET method for Read operation
    def get_api(self, api_url: str, page: int = 0, page_size: int = 100):
        params = {"page": page, "size": page_size}
        response = requests.get(
            f"{self.ise}{api_url}",
            params=params,
            headers=self.headers,
            auth=self.auth,
            verify=False
        )
        response.raise_for_status()
        return response.json()

# Function to load supported URLs with their names from a JSON file
def load_urls(file_path='ise_urls.json'):
    if not os.path.exists(file_path):
        return {"error": f"URLs file '{file_path}' not found."}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Extract the URL and Name fields into a list of tuples
        url_list = [(entry['URL'], entry.get('Name', '')) for entry in data]
        return url_list
    except Exception as e:
        return {"error": f"Error loading URLs: {str(e)}"}

def check_url_support(api_url: str) -> dict:
    url_list = load_urls()
    if "error" in url_list:
        return url_list  # Return error if loading URLs failed

    # Separate URLs and Names into two lists for matching
    urls = [entry[0] for entry in url_list]
    names = [entry[1] for entry in url_list]

    # Find the closest matches to the input based on both URL and Name
    close_url_matches = difflib.get_close_matches(api_url, urls, n=1, cutoff=0.6)
    close_name_matches = difflib.get_close_matches(api_url, names, n=1, cutoff=0.6)

    # Determine the best match from either the URL or Name
    if close_url_matches:
        closest_url = close_url_matches[0]
        # Find the matching name for this URL
        matching_name = [entry[1] for entry in url_list if entry[0] == closest_url][0]
        return {"status": "supported", "closest_url": closest_url, "closest_name": matching_name}
    elif close_name_matches:
        closest_name = close_name_matches[0]
        # Find the corresponding URL for this name
        closest_url = [entry[0] for entry in url_list if entry[1] == closest_name][0]
        return {"status": "supported", "closest_url": closest_url, "closest_name": closest_name}
    else:
        return {"status": "unsupported", "message": f"The input '{api_url}' is not supported. Please check the available URLs or Names."}

@tool
def check_supported_url_tool(api_url: str) -> dict:
    """Check if an API URL or Name is supported by the ISE controller."""
    result = check_url_support(api_url)
    if result.get('status') == 'supported':
        # Automatically get the data if the URL is valid
        closest_url = result['closest_url']
        closest_name = result['closest_name']
        return {
            "status": "supported",
            "message": f"The closest supported API URL is '{closest_url}' ({closest_name}).",
            "action": {
                "next_tool": "get_ise_data_tool",
                "input": closest_url
            }
        }
    return result

@tool
def get_ise_data_tool(api_url: str) -> dict:
    """Fetch data from the ISE controller."""
    try:
        ise_controller = ISEController(
            ise_url="https://devnetsandboxise.cisco.com",
            username="readonly",
            password="ISEisC00L"
        )
        data = ise_controller.get_api(api_url)
        return data
    except requests.HTTPError as e:
        return {"error": f"Failed to fetch data from ISE: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

# Create a list of tools
ise_tools = [check_supported_url_tool, get_ise_data_tool]

# Render text descriptions for the tools
tool_descriptions = render_text_description(ise_tools)

# Create the PromptTemplate
template = """
Assistant is a network assistant with the capability to manage data from Cisco Identity Services Engine (ISE) controllers using GET operations.

NETWORK INSTRUCTIONS:

Assistant is designed to retrieve information from the Cisco ISE controller using provided tools. You MUST use these tools for checking available data and fetching it.

Assistant has access to a list of API URLs and their associated Names provided in a 'ise_urls.json' file. You can use the 'Name' field to find the appropriate API URL to use.

**Important Guidelines:**

1. **If you are certain of the API URL or the Name of the data you want, use the 'get_ise_data_tool' to fetch data.**
2. **If you are unsure of the API URL or Name, or if there is ambiguity, use the 'check_supported_url_tool' to verify the URL or Name or get a list of available ones.**
3. **If the 'check_supported_url_tool' finds a valid URL or Name, automatically use the 'get_ise_data_tool' to fetch the data without waiting for another input.**
4. **Do NOT use any unsupported URLs or Names.**

**Using the Tools:**

- If you are confident about the API URL or Name, use the 'get_ise_data_tool'.
- If there is any doubt or ambiguity, always check the URL or Name first with the 'check_supported_url_tool'.

To use a tool, follow this format:

Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action

If the first tool provides a valid URL or Name, you MUST immediately run the 'get_ise_data_tool' to fetch the data. Follow the flow like this:

**Example:**

Thought: Do I need to use a tool? Yes
Action: check_supported_url_tool
Action Input: "Endpoints"
Observation: "The closest supported API URL is '/ers/config/endpoint?size=100' (Endpoints)."

Thought: Do I need to use a tool? Yes
Action: get_ise_data_tool
Action Input: "/ers/config/endpoint?size=100"
Observation: [retrieved data here]

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

Thought: Do I need to use a tool? No
Final Answer: [your response here]

**Correct Formatting is Essential:** Ensure that every response follows the format strictly to avoid errors.

TOOLS:

Assistant has access to the following tools:

- check_supported_url_tool: Checks if an API URL or Name is supported by the ISE controller.
- get_ise_data_tool: Fetches data from the ISE controller using the specified API URL.

Begin!

Previous conversation history:

{chat_history}

New input: {input}

{agent_scratchpad}
"""

# Define input variables
input_variables = ["input", "agent_scratchpad"]

# Create the PromptTemplate
ise_prompt_template = PromptTemplate(
    template=template,
    input_variables=input_variables,
    partial_variables={
        "tools": tool_descriptions,
        "tool_names": ", ".join([t.name for t in ise_tools])
    }
)