import culpa
culpa.init()

from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a Python function that reverses a string"}]
)
print(response.content[0].text)