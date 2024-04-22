from typing import List
from langchain.agents import AgentExecutor
from langchain_core.prompts.base import BasePromptTemplate
from langchain.tools.render import format_tool_to_openai_function
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from .formatters import Input, Output


def create_agent(prompt: BasePromptTemplate, llm, tools: List[str]):
    llm_with_tools = llm.bind(functions=[format_tool_to_openai_function(t) for t in tools])

    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_functions(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm_with_tools
        | OpenAIFunctionsAgentOutputParser()
    )

    return AgentExecutor(agent=agent, tools=tools).with_types(input_type=Input, output_type=Output)


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


def create_prompt(variable_name="agent_scratchpad"):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant searches domain knowledge. Use tools (only if necessary) to best answer the users' questions. 
        Return the response in Slack mrkdwn format, including emojis, bullet points, and bold text where necessary.

        Slack message formatting example:
        Bold text: *bold text*
        Italic text: _italic text_
        Bullet points: • example 1 \n • example 2 \n
        Link: <fakeLink.toEmployeeProfile.com|Fred Enriquez - New device request>
        Remember that slack mrkdwn formatting is different from regular markdown formatting. do not use regular markdown formatting in your response.
        As an example do not us the following: **bold text** or [link](http://example.com),
        """),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name=variable_name),
    ])
    return prompt