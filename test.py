from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  extra_body={},
  model="qwen/qwen2.5-vl-32b-instruct:free",
  messages=[
              {
                "role": "user",
                "content": "Music recommendation after hearing megalovania, make it short"
              }
            ]
)
print(completion.choices[0].message.content)