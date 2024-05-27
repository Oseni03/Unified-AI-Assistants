from django.conf import settings
from google.oauth2.credentials import Credentials

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.tool_executor import ToolExecutor

from .toolkits import GmailToolkit, GoogleCalenderToolkit
from common.models import ThirdParty
from integrations.models import Integration

GeminiLLM = ChatGoogleGenerativeAI(
    model="gemini-pro", google_api_key=settings.GOOGLE_API_KEY
)
model = ChatOpenAI(model="gpt-4o")

def create_prompt(thirdparty="slack"):
    system = None

    if thirdparty == ThirdParty.SLACK:

        system = '''You are a helpful assistant searches domain knowledge. Use tools (only if necessary) to best answer the users' questions. 
            Return the response in slack mrkdwn format, including emojis, bullet points, and bold text where necessary. 
            
            Slack message formatting example:
            Bold text: *bold text*
            Italic text: _italic text_
            Bullet points: • example 1 \n • example 2 \n
            Link: <fakeLink.toEmployeeProfile.com|Fred Enriquez - New device request>
            Remember that Slack mrkdwn formatting is different from regular markdown formatting. do not use regular markdown formatting in your response.
            As an example do not us the following: **bold text** or [link](http://example.com),
            '''

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("placeholder", "{messages}"),
        ("user", "Remember, always be polite!"),
    ])

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

    tool_executors = ToolExecutor(tools=tools)

    # prompt = create_prompt(integration.thirdparty)

    # def modify_messages(messages: list):
    #     # You can do more complex modifications here
    #     return prompt.invoke({"messages": messages})

    print(f"Created prompt successfully")

    system = '''You are a helpful assistant searches domain knowledge. Use tools (only if necessary) to best answer the users' questions. 
    Return the response in slack mrkdwn format, including emojis, bullet points, and bold text where necessary. 
    
    Slack message formatting example:
    Bold text: *bold text*
    Italic text: _italic text_
    Bullet points: • example 1 \n • example 2 \n
    Link: <fakeLink.toEmployeeProfile.com|Fred Enriquez - New device request>
    Remember that Slack mrkdwn formatting is different from regular markdown formatting. do not use regular markdown formatting in your response.
    As an example do not us the following: **bold text** or [link](http://example.com),
    '''

    agent = create_react_agent(model=model, tools=tool_executors, messages_modifier=system)

    print(f"Created agent successfully")
    return agent
    