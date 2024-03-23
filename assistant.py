from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from openai import OpenAI
from langchain.agents import tool
from tools import TOOLS, get_calendar_events
from langchain.agents.format_scratchpad.openai_tools import(
    format_to_openai_tool_messages
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import AgentExecutor
from dotenv import load_dotenv

OPENAI_CHAT_MODEL_NAME = 'gpt-3.5-turbo'
MEMORY_KEY = 'chat_history'

def get_llm(model_name: str, model_temperature: int) -> OpenAI:
    return ChatOpenAI(model=model_name, temperature=model_temperature)

def get_prompt() -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are very powerful assistant, but don't know calendar events."
            ),
            MessagesPlaceholder(variable_name=MEMORY_KEY),
            (
                "user",
                "{input}"
            ),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ]
    )
    return prompt
    

def get_agent(prompt, llm_with_tools, chat_history: list):
    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
            "chat_history": lambda x: x["chat_history"],
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )
    
    return agent
    


def main():
    load_dotenv()
    llm = get_llm(OPENAI_CHAT_MODEL_NAME, model_temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)
    prompt = get_prompt()
    chat_history = []
    
    agent = get_agent(prompt, llm_with_tools, chat_history)
    agent_executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=True)
    
    while True:
        user_input = input("Question: ")
        result = agent_executor.invoke({"input": user_input, "chat_history": chat_history})
        print(result)
        
        chat_history.extend(
            [
                HumanMessage(content=user_input),
                AIMessage(content=result["output"])
            ]
        )
        
    
if __name__ == "__main__":
    main()