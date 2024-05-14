from pprint import pprint
from typing import List

from django.conf import settings
from google.oauth2.credentials import Credentials

from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.prompts.base import BasePromptTemplate
from langchain.tools.render import format_tool_to_openai_function
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.utils.json_schema import dereference_refs
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from .toolkits import GmailToolkit, GoogleCalenderToolkit
from common.models import ThirdParty
from integrations.models import Integration

GeminiLLM = ChatGoogleGenerativeAI(
    model="gemini-pro", google_api_key=settings.GOOGLE_API_KEY
)


# prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", """You are a helpful assistant that searches Salesforce Knowledge articles. Use tools (only if necessary) to best answer the users' questions. Return the response in Slack mrkdwn format, including emojis, bullet points, and bold text where necessary.

# Slack message formatting example:
# Bold text: *bold text*
# Italic text: _italic text_
# Bullet points: • example 1 \n • example 2 \n
# Link: <fakeLink.toEmployeeProfile.com|Fred Enriquez - New device request>
# Remember that slack mrkdwn formatting is different from regular markdown formatting. do not use regular markdown formatting in your response.
# As an example do not us the following: **bold text** or [link](http://example.com),
#          """),
#         # Please note that the ordering of the user input vs.
#         # the agent_scratchpad is important.
#         # The agent_scratchpad is a working space for the agent to think,
#         # invoke tools, see tools outputs in order to respond to the given
#         # user input. It has to come AFTER the user input.
#         ("user", "{input}"),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#     ]
# )


def create_prompt(thirdparty="slack"):
    if thirdparty == ThirdParty.SLACK:

        template = '''You are a helpful assistant searches domain knowledge. Use tools (only if necessary) to best answer the users' questions. 
            Return the response in slack mrkdwn format, including emojis, bullet points, and bold text where necessary. 
            
            Slack message formatting example:
            Bold text: *bold text*
            Italic text: _italic text_
            Bullet points: • example 1 \n • example 2 \n
            Link: <fakeLink.toEmployeeProfile.com|Fred Enriquez - New device request>
            Remember that Slack mrkdwn formatting is different from regular markdown formatting. do not use regular markdown formatting in your response.
            As an example do not us the following: **bold text** or [link](http://example.com),
            
            You have access to the following tools:

            {tools}

            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            Begin!

            Question: {input}
            Thought:{agent_scratchpad}'''

    prompt = PromptTemplate.from_template(template, partial_variables={"thirdparty": thirdparty})

    return prompt


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}


def get_agent(integration: Integration, credential: Credentials):
    tools = []

    if integration.thirdparty == ThirdParty.GMAIL:
        toolkit = GmailToolkit(credentials=credential)
    elif integration.thirdparty == ThirdParty.GOOGLE_CALENDER:
        toolkit = GoogleCalenderToolkit(credentials=credential)
    tools = toolkit.get_tools()

    prompt = create_prompt()
    print(f"Created prompt successfully")

    agent = create_react_agent(GeminiLLM, tools, prompt)

    agent_exceutor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    print(f"Created agent successfully")
    return agent_exceutor
    