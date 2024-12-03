import torch

# Stanza English model
def en_nlp_load():
    global en_nlp
    import stanza
    stanza.download('en')
    en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate')
    return en_nlp

# GPT2 model
def gpt2_model_load():
    global perplexity_model, tokenizer
    if "gpt2".startswith("gpt2"):
        from transformers import GPT2Tokenizer, GPT2LMHeadModel
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        perplexity_model = GPT2LMHeadModel.from_pretrained("gpt2")
    else:
        from transformers import OpenAIGPTTokenizer, OpenAIGPTLMHeadModel
        tokenizer = OpenAIGPTTokenizer.from_pretrained("openai-gpt")
        perplexity_model = OpenAIGPTLMHeadModel.from_pretrained("openai-gpt")
    perplexity_model.eval()
    if torch.cuda.is_available():
        perplexity_model.to('cuda')
    print("Model init")
    return perplexity_model, tokenizer