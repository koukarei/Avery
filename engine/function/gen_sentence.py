from openai import OpenAI

def generateSentence(keywords):
  client=OpenAI()
  completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": "You are going to write a sentence by keywords given by the user."},
      {"role": "user", "content": f"Here are some keywords: {keywords}."}
    ]
  )

  return completion.choices[0].message

def genSentences(keywords):
    gen_Sentences=[]
    for i in range(10):
        gen_Sentences.append(generateSentence(keywords).content)
    return gen_Sentences