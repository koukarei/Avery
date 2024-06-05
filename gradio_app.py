import gradio as gr
from engine.game.round import Round


cur_round=Round()

with gr.Blocks() as demo:
    img=gr.Image(value=f"demo/Test Picture/sddefault.jpg",label="Original Picture",interactive=True)
    
    keywords=gr.State([])
    keywords=gr.State([
        {"name":"A sloth","remove":False},
        {"name":"red car","remove":False},
        {"name":"driving","remove":False},
        {"name":"teasing","remove":False},
    ])

    new_keyword=gr.Textbox(label="Keyword",autofocus=True)

    def add_keyword(keywords,new_keyword):
        return keywords+[{"name":new_keyword,"remove":False}],""
    new_keyword.submit(add_keyword,[keywords,new_keyword],[keywords,new_keyword])
    
    @gr.render(inputs=keywords)
    def render_keywords(keyword_list):
        for keyword in keyword_list:
            with gr.Row():
                gr.Textbox(keyword['name'],show_label=False,container=False)
                remove_btn=gr.Button("Remove",scale=0)
                def remove_keyword(keyword=keyword):
                    keyword_list.remove(keyword)
                    return keyword_list
                remove_btn.click(remove_keyword,None,[keywords])

    get_sentences_btn=gr.Button("Get Sentences",scale=0)
    sentences=gr.State([])
    sentence_txtbox_group=gr.Group()
    
    def get_sentences(sentences):
        cur_round.set_original_picture(img.value)
        cur_round.set_keyword(keywords.value)
        from engine.function.gen_sentence import generateSentence
        if not sentences:
            sentence_list=[]
            for i in range(3):
                sentence_list.append({
                    "name":f"sentence{i}",
                    "sentence":generateSentence(cur_round.keyword).content
                })
        sentences=gr.State(sentence_list)
        for sentence in sentence_list:
            with gr.Row():
                sentence_txtbox=gr.Textbox(sentence['sentence'],show_label=False,container=False)
                sentence_txtbox_group.add_child(sentence_txtbox)
                regenerate_btn=gr.Button("Regenerate",scale=0)
                
                def regenerate_sentence(sentence):
                    sentence.change(generateSentence,cur_round.keyword)
                regenerate_btn.click(regenerate_sentence,sentence_txtbox,None)
               

    get_sentences_btn.click(get_sentences,[sentences],[sentences])
    test_txtbox=gr.Textbox()
    def on_select(evt: gr.SelectData):
        return f"You selected {evt.value} at {evt.index} from {evt.target}"
    
    for sentence_txtbox in sentence_txtbox_group.children:
        print(type(sentence_txtbox))
        sentence_txtbox.select(on_select,None,test_txtbox)



if __name__ == "__main__":
    demo.launch()
