import torch
import stanza
from stanza.download import DownloadMethod

# Stanza English model
def en_nlp_load():
    #stanza.download('en')
    en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate', download_method=DownloadMethod.REUSE_RESOURCES)
    try:
        yield en_nlp
    finally:
        del en_nlp


# BLIP2 text-image matching model
def blip2_model_load():
    from lavis.models import load_model_and_preprocess
    from lavis.processors import load_processor
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blip2_model, vis_processors, text_processors = load_model_and_preprocess(
        "blip2_image_text_matching", "pretrain", device=device, is_eval=True
    )
    try:
        yield blip2_model, vis_processors, text_processors
    finally:
        del blip2_model, vis_processors, text_processors

# GPT2 model
def gpt2_model_load():
    if "gpt2".startswith("gpt2"):
        from transformers import GPT2Tokenizer, GPT2LMHeadModel
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        model = GPT2LMHeadModel.from_pretrained("gpt2")
    else:
        from transformers import OpenAIGPTTokenizer, OpenAIGPTLMHeadModel
        tokenizer = OpenAIGPTTokenizer.from_pretrained("openai-gpt")
        model = OpenAIGPTLMHeadModel.from_pretrained("openai-gpt")
    model.eval()
    if torch.cuda.is_available():
        model.to('cuda')
    print("Model init")

    try:
        yield model, tokenizer
    finally:
        del model, tokenizer