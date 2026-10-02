import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("未找到 DEEPSEEK_API_KEY，请检查项目根目录中的 .env 文件。")

client = OpenAI(
    api_key=api_key,
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
