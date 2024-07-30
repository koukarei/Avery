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

def genSentences(keywords,amt=3):
    gen_Sentences=[]
    for i in range(amt):
        gen_Sentences.append(generateSentence(keywords).content)
    return gen_Sentences

def checkSentence(sentence,temp=0.5):
  client=OpenAI()
  completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": """
       You are English teacher.
       You are going to correct the sentence given by the user. 
       Your input only needs to be the corrected sentence.
       If the sentence is not English, reply with "Please enter an English sentence."
       If the sentence is not valid, reply with "Please enter a valid English sentence."
       If the sentence is correct, reply with the sentence itself.
"""},
      {"role": "user", "content": f"{sentence}"}
    ],
    temperature=temp

  )
  if completion.choices[0].message:
    return completion.choices[0].message.content
  else:
     raise Exception("Sentence correction failed.")