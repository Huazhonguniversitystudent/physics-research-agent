import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

question = input("请输入你的物理问题：")

response = client.responses.create(
    model="deepseek-flash",
    instructions=(
        "You are a helpful physics research assistant. "
        "Explain physics concepts clearly to an undergraduate physics student."
    ),
    input=question,
)

print("\nAI 回答：")
print(response.output_text)