#!/usr/bin/env python3
"""快速测试 Qwen API 调用格式"""

from openai import OpenAI

client = OpenAI(
    api_key="sk-9b155a5f0d8849bdb1957500a34f644e",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

try:
    response = client.chat.completions.create(
        model="qwen3-max",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, what is 2+2?"},
        ],
        temperature=0.7,
        max_tokens=200,
        stream=False
    )
    
    print(f"Response type: {type(response)}")
    print(f"Response attributes: {dir(response)}")
    print(f"Response: {response}")
    
    # 尝试提取内容
    if hasattr(response, 'choices') and response.choices:
        print(f"\nFirst choice: {response.choices[0]}")
        choice = response.choices[0]
        if hasattr(choice, 'message'):
            print(f"Message: {choice.message}")
            if hasattr(choice.message, 'content'):
                print(f"Content: {choice.message.content}")
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    print(traceback.format_exc())
