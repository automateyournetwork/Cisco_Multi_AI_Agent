import os
import logging
import streamlit as st
from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI
import urllib3

# Import the tools and prompt templates from your agent scripts
from ios_xe_agent import ios_xe_tools, ios_xe_prompt_template
from aci_agent import aci_tools, aci_prompt_template
from ise_agent import ise_tools, ise_prompt_template

# Configure logging at the start of your script
logging.basicConfig(level=logging.INFO)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize LLM
llm = ChatOpenAI(model_name="gpt-4")

# Create sub-agents for each system using initialize_agent
ios_xe_agent = initialize_agent(
    tools=ios_xe_tools,
    llm=llm,
    agent='zero-shot-react-description',
    prompt=ios_xe_prompt_template,
    verbose=True
)

aci_agent = initialize_agent(
    tools=aci_tools,
    llm=llm,
    agent='zero-shot-react-description',
    prompt=aci_prompt_template,
    verbose=True
)

ise_agent = initialize_agent(
    tools=ise_tools,
    llm=llm,
    agent='zero-shot-react-description',
    prompt=ise_prompt_template,
    verbose=True
)

# Define wrapper functions for each agent
def ios_xe_agent_func(input_text: str) -> str:
    return ios_xe_agent.run(input_text)

def aci_agent_func(input_text: str) -> str:
    return aci_agent.run(input_text)

def ise_agent_func(input_text: str) -> str:
    return ise_agent.run(input_text)

# Define tools for each sub-agent
ios_xe_tool = Tool(
    name="IOS XE Agent",
    func=ios_xe_agent_func,
    description="Use for interacting with Cisco IOS XE devices."
)

aci_tool = Tool(
    name="ACI Agent",
    func=aci_agent_func,
    description="Use for interacting with Cisco ACI controllers."
)

ise_tool = Tool(
    name="ISE Agent",
    func=ise_agent_func,
    description="Use for interacting with Cisco ISE."
)

# Create master agent tools list
master_tools = [ios_xe_tool, aci_tool, ise_tool]

# Initialize the master agent
master_agent = initialize_agent(
    tools=master_tools,
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

# ============================================================
# Streamlit App
# ============================================================

# Initialize Streamlit
st.title("Network AI Agent with LangChain")
st.write("Ask your network questions and get insights using AI!")

# Input for user questions
user_input = st.text_input("Enter your question:")

# Session state to store chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = ""

if "conversation" not in st.session_state:
    st.session_state.conversation = []

# Button to submit the question
if st.button("Send"):
    if user_input:
        # Add the user input to the conversation history
        st.session_state.conversation.append({"role": "user", "content": user_input})

        # Invoke the master agent with the user input
        try:
            response = master_agent.run(user_input)

            # Display the question and answer
            st.write(f"**Question:** {user_input}")
            st.write(f"**Answer:** {response}")

            # Add the response to the conversation history
            st.session_state.conversation.append({"role": "assistant", "content": response})

            # Update chat history with the new conversation
            st.session_state.chat_history = "\n".join(
                [f"{entry['role'].capitalize()}: {entry['content']}" for entry in st.session_state.conversation]
            )
        except Exception as e:
            st.write(f"An error occurred: {str(e)}")

# Display the entire conversation history
if st.session_state.conversation:
    st.write("## Conversation History")
    for entry in st.session_state.conversation:
        st.write(f"**{entry['role'].capitalize()}:** {entry['content']}")
