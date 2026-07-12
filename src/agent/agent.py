from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from functions import tools
from pathlib import Path
import sys

llm = ChatOpenAI(
    model="qwen-2.5-instruct",
    base_url="http://localhost:8080/v1",
    api_key="null"
)

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / 'SKILL.md', 'r') as f:
    skill = f.read()

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=skill
)

usr_input = sys.argv[1]

response = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": usr_input
        }
    ]
})

print(response['messages'][-1].content)