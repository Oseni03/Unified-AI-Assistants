import operator
import functools
from django.conf import settings
from typing import Annotated, Sequence, TypedDict
from google.oauth2.credentials import Credentials

# from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.tool_executor import ToolExecutor
from langgraph.graph import StateGraph, END
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser

from .tools import GmailTools, GoogleCalenderTools, SalesForceTools
from .constants import GENERAL_SYSTEM_MESSAGE, GMAIL_SYSTEM_MESSAGE, GOOGLE_CALENDER_SYSTEM_MESSAGE
from common.models import ThirdParty
from integrations.models import Integration

GeminiLLM = ChatGoogleGenerativeAI(
    model="gemini-pro", google_api_key=settings.GOOGLE_API_KEY
)


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}


def create_agent(llm: ChatOpenAI, tools: list, system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("user", "Remember, always be polite!"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools)
    return executor


def agent_node(state, agent, name):
    result = agent.invoke(state)
    return {"messages": [HumanMessage(content=result["output"], name=name)]}


# The agent state is the input to each node in the graph
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # The 'next' field indicates where to route to next
    next: str


def create_agent_supervisor(llm, members: list):
    # Create Agent Supervisor
    system_prompt = (
        "As a supervisor, your role is to oversee a dialogue between these"
        " workers: {members}. Based on the user's request,"
        " determine which worker should take the next action. Ecah worker is responsible for"
        " executing a specific task and reporting back their findings and process. Once all tasks are complete"
        " indicate with 'FINISH'."
    )

    options = ["FINISH"] + members
    function_def = {
        "name": "route",
        "description": "Select the next role",
        "parameters": {
            "title": "routeSchema",
            "type": "object", 
            "properties": {"next": {"title": "Next", "anyOf": [{"enums": options}]}},
            "required": ["next"]
        }
    }

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Given the conversation above, who should act next? or should we FINISH? ")
    ]).partial(options=str(options), members=", ".join(members))

    supervisor_chain = (
        prompt
        | llm.bind_functions(functions=[function_def], function_call="route")
        | JsonOutputFunctionsParser()
    )
    return supervisor_chain


def create_google_workspace_multi_agent(llm: ChatOpenAI, credential: Credentials):
    # Define members of the AI crew
    members = ["Gmail_Assistant", "Google_Calender_Assistant"]

    # Create supervisor chain
    supervisor_chain = create_agent_supervisor(llm, members)

    # Define each agent tools
    gmail_tools = GmailTools(creds=credential).get_tools()
    calender_tools = GoogleCalenderTools(creds=credential).get_tools()

    # define the agent and node
    gmail_agent = create_agent(llm, gmail_tools, GMAIL_SYSTEM_MESSAGE)
    gmail_node = functools.partial(agent_node, agent=gmail_agent, name="Gmail_Assistant")

    calender_agent = create_agent(llm, calender_tools, GOOGLE_CALENDER_SYSTEM_MESSAGE)
    calender_node = functools.partial(agent_node, agent=calender_agent, name="Google_Calender_Assistant")
    
    # Create Graph
    workflow = StateGraph(AgentState)
    workflow.add_node("Gmail_Assistant", gmail_node)
    workflow.add_node("Google_Calender_Assistant", calender_node)
    workflow.add_node("supervisor", supervisor_chain)

    # Now connect all the edges in the graph.
    for member in members:
    # We want our workers to ALWAYS "report back" to the supervisor when done
        workflow.add_edge(member, "supervisor")
    # The supervisor populates the "next" field in the graph state
    # which routes to a node or finishes
    conditional_map = {k: k for k in members}
    conditional_map["FINISH"] = END
    workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
    # Finally, add entrypoint
    workflow.set_entry_point("supervisor")

    graph = workflow.compile()
    return graph


def get_agent(integration: Integration, credential: Credentials = None, username: str = None, password: str = None, security_token: str = None):
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=settings.OPENAI_API_KEY)

    if integration.is_workspace:
        if integration.thirdparty == ThirdParty.GOOGLE_WORKSPACE and credential is not None:
            agent = create_google_workspace_multi_agent(llm, credential=credential)
    else:
        tools = []

        if integration.thirdparty == ThirdParty.SALESFORCE:
            tools = SalesForceTools.get_tools()

        tool_executors = ToolExecutor(tools=tools)
        agent = create_react_agent(model=llm, tools=tool_executors, messages_modifier=GENERAL_SYSTEM_MESSAGE)

    print(f"Created agent successfully")
    return agent
    