import os
import json
import difflib
from pyats.topology import loader
from langchain_community.chat_models import ChatOpenAI
from langchain_core.tools import tool, render_text_description
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from genie.libs.parser.utils import get_parser

# Function to run any supported show command using pyATS
def run_show_command(command: str):
    try:
        # Disallowed modifiers
        disallowed_modifiers = ['|', 'include', 'exclude', 'begin', 'redirect', '>', '<']

        # Check for disallowed modifiers
        for modifier in disallowed_modifiers:
            if modifier in command:
                return {"error": f"Command '{command}' contains disallowed modifier '{modifier}'. Modifiers are not allowed."}

        # Load the testbed
        print("Loading testbed...")
        testbed = loader.load('testbed.yaml')

        # Access the device from the testbed
        device = testbed.devices['Cat8000V']

        # Connect to the device
        print("Connecting to device...")
        device.connect()

        # Check if a pyATS parser is available for the command
        print(f"Checking if a parser exists for the command: {command}")
        parser = get_parser(command, device)
        if parser is None:
            return {"error": f"No parser available for the command: {command}"}

        # Execute the command and parse the output using Genie
        print(f"Executing '{command}'...")
        parsed_output = device.parse(command)

        # Close the connection
        print("Disconnecting from device...")
        device.disconnect()

        # Return the parsed output (JSON)
        return parsed_output
    except Exception as e:
        # Handle exceptions and provide error information
        return {"error": str(e)}

# Function to load supported commands from a JSON file
def load_supported_commands():
    file_path = 'ios_xe_commands.json'  # Ensure the file is named correctly

    # Check if the file exists
    if not os.path.exists(file_path):
        return {"error": f"Supported commands file '{file_path}' not found."}

    try:
        # Load the JSON file with the list of commands
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Extract the command strings into a list
        command_list = [entry['command'] for entry in data]
        return command_list
    except Exception as e:
        return {"error": f"Error loading supported commands: {str(e)}"}

# Function to check if a command is supported with fuzzy matching
def check_command_support(command: str) -> dict:
    command_list = load_supported_commands()

    if "error" in command_list:
        return command_list

    # Find the closest matches to the input command using difflib
    close_matches = difflib.get_close_matches(command, command_list, n=1, cutoff=0.6)

    if close_matches:
        closest_command = close_matches[0]
        return {"status": "supported", "closest_command": closest_command}
    else:
        return {"status": "unsupported", "message": f"The command '{command}' is not supported. Please check the available commands."}

# Function to apply configuration using pyATS
def apply_device_configuration(config_commands: str):
    try:
        # Load the testbed
        print("Loading testbed...")
        testbed = loader.load('testbed.yaml')

        # Access the device from the testbed
        device = testbed.devices['Cat8000V']

        # Connect to the device
        print("Connecting to device...")
        device.connect()

        # Apply the configuration
        print(f"Applying configuration:\n{config_commands}")
        device.configure(config_commands)

        # Close the connection
        print("Disconnecting from device...")
        device.disconnect()

        # Return a success message
        return {"status": "success", "message": "Configuration applied successfully."}
    except Exception as e:
        # Handle exceptions and provide error information
        return {"error": str(e)}

# Function to learn the configuration using pyATS
def execute_show_run():
    try:
        # Load the testbed
        print("Loading testbed...")
        testbed = loader.load('testbed.yaml')

        # Access the device from the testbed
        device = testbed.devices['Cat8000V']

        # Connect to the device
        print("Connecting to device...")
        device.connect()

        # Use the pyATS learn function to gather the configuration
        print("Learning configuration...")
        learned_config = device.execute('show run brief')

        # Close the connection
        print("Disconnecting from device...")
        device.disconnect()

        # Return the learned configuration as JSON
        return learned_config
    except Exception as e:
        # Handle exceptions and provide error information
        return {"error": str(e)}

# Function to learn the configuration using pyATS
def execute_show_logging():
    try:
        # Load the testbed
        print("Loading testbed...")
        testbed = loader.load('testbed.yaml')

        # Access the device from the testbed
        device = testbed.devices['Cat8000V']

        # Connect to the device
        print("Connecting to device...")
        device.connect()

        # Use the pyATS learn function to gather the configuration
        print("Learning configuration...")
        learned_logs = device.execute('show logging last 250')

        # Close the connection
        print("Disconnecting from device...")
        device.disconnect()

        # Return the learned configuration as JSON
        return learned_logs
    except Exception as e:
        # Handle exceptions and provide error information
        return {"error": str(e)}

# Define the custom tool using the langchain `tool` decorator
@tool
def run_show_command_tool(command: str) -> dict:
    """Execute a 'show' command on the router using pyATS and return the parsed JSON output."""
    return run_show_command(command)

# New tool for checking if a command is supported and chaining to run_show_command_tool
@tool
def check_supported_command_tool(command: str) -> dict:
    """Check if a command is supported by pyATS based on the command list and return the details."""
    result = check_command_support(command)

    if result.get('status') == 'supported':
        # Automatically run the show command if the command is valid
        closest_command = result['closest_command']
        return {
            "status": "supported",
            "message": f"The closest supported command is '{closest_command}'",
            "action": {
                "next_tool": "run_show_command_tool",
                "input": closest_command
            }
        }
    return result

# Define the custom tool for configuration changes
@tool
def apply_configuration_tool(config_commands: str) -> dict:
    """Apply configuration commands on the router using pyATS."""
    return apply_device_configuration(config_commands)

# Define the custom tool for learning the configuration
@tool
def learn_config_tool(dummy_input: str = "") -> dict:
    """Excute show run brief on the router using pyATS to return the running-configuration."""
    return execute_show_run()

# Define the custom tool for learning the configuration
@tool
def learn_logging_tool(dummy_input: str = "") -> dict:
    """Execute show logging on the router using pyATS and return it as raw text."""
    return execute_show_logging()

# ============================================================
# Define the agent with a custom prompt template
# ============================================================

# Create a list of tools
ios_xe_tools = [run_show_command_tool, check_supported_command_tool, apply_configuration_tool, learn_config_tool, learn_logging_tool]

# Render text descriptions for the tools for inclusion in the prompt
tool_descriptions = render_text_description(ios_xe_tools)

template = '''
Assistant is a large language model trained by OpenAI.

Assistant is designed to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on various topics. As a language model, Assistant can generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide coherent and relevant responses.

Assistant is constantly learning and improving. It can process and understand large amounts of text and use this knowledge to provide accurate and informative responses to a wide range of questions. Additionally, Assistant can generate its text based on the input it receives, allowing it to engage in discussions and provide explanations and descriptions on various topics.

NETWORK INSTRUCTIONS:

Assistant is a network assistant with the capability to run tools to gather information, configure the network, and provide accurate answers. You MUST use the provided tools for checking interface statuses, retrieving the running configuration, configuring settings, or finding which commands are supported.

**Important Guidelines:**

1. **If you are certain of the command for retrieving information, use the 'run_show_command_tool' to execute it.**
2. **If you need access to the full running configuration, use the 'learn_config_tool' to retrieve it.**
3. **If you are unsure of the command or if there is ambiguity, use the 'check_supported_command_tool' to verify the command or get a list of available commands.**
4. **If the 'check_supported_command_tool' finds a valid command, automatically use 'run_show_command_tool' to run that command.**
5. **For configuration changes, use the 'apply_configuration_tool' with the necessary configuration string (single or multi-line).**
6. **Do NOT use any command modifiers such as pipes (`|`), `include`, `exclude`, `begin`, `redirect`, or any other modifiers.**
7. **If the command is not recognized, always use the 'check_supported_command_tool' to clarify the command before proceeding.**

**Using the Tools:**

- If you are confident about the command to retrieve data, use the 'run_show_command_tool'.
- If you need access to the full running configuration, use 'learn_config_tool'.
- If there is any doubt or ambiguity, always check the command first with the 'check_supported_command_tool'.
- If you need to apply a configuration change, use 'apply_configuration_tool' with the appropriate configuration commands.

To use a tool, follow this format:

Thought: Do I need to use a tool? Yes  
Action: the action to take, should be one of [{tool_names}]  
Action Input: the input to the action  
Observation: the result of the action  

If the first tool provides a valid command, you MUST immediately run the 'run_show_command_tool' without waiting for another input. Follow the flow like this:

Example:

Thought: Do I need to use a tool? Yes  
Action: check_supported_command_tool  
Action Input: "show ip access-lists"  
Observation: "The closest supported command is 'show ip access-list'."

Thought: Do I need to use a tool? Yes  
Action: run_show_command_tool  
Action Input: "show ip access-list"  
Observation: [parsed output here]

If you need access to the full running configuration:

Example:

Thought: Do I need to use a tool? Yes  
Action: learn_config_tool  
Action Input: (No input required)  
Observation: [configuration here]

If you need to apply a configuration:

Example:

Thought: Do I need to use a tool? Yes  
Action: apply_configuration_tool  
Action Input: """  
interface loopback 100  
description AI Created  
ip address 10.10.100.100 255.255.255.0  
no shutdown  
"""  
Observation: "Configuration applied successfully."

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

Thought: Do I need to use a tool? No  
Final Answer: [your response here]

Correct Formatting is Essential: Ensure that every response follows the format strictly to avoid errors.

TOOLS:

Assistant has access to the following tools:

- check_supported_command_tool: Finds and returns the closest supported commands.
- run_show_command_tool: Executes a supported 'show' command on the network device and returns the parsed output.
- apply_configuration_tool: Applies the provided configuration commands on the network device.
- learn_config_tool: Learns the running configuration from the network device and returns it as JSON.

Begin!

Previous conversation history:

{chat_history}

New input: {input}

{agent_scratchpad}
'''

# Define the input variables separately
input_variables = ["input", "agent_scratchpad", "chat_history"]

# Create the PromptTemplate using the complete template and input variables
ios_xe_prompt_template = PromptTemplate(
    template=template,
    input_variables=input_variables,
    partial_variables={
        "tools": tool_descriptions,
        "tool_names": ", ".join([t.name for t in ios_xe_tools])
    }
)
