import gradio as gr
from engine.game.round import Round
from typing import List

testing=False

cur_round=Round()

with gr.Blocks() as demo:
    img=gr.Image(value=f"demo/Test Picture/sddefault.jpg",label="Original Picture",interactive=True)
    
    if testing:
        keywords=gr.State([
            {"name":"A sloth","remove":False},
            {"name":"red car","remove":False},
            {"name":"driving","remove":False},
            {"name":"teasing","remove":False},
        ])
    else:
        keywords=gr.State([])


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
    sentence_txtbox_group=gr.Group(visible=False)
    choose_btn_group=gr.Group(visible=False)

    @get_sentences_btn.click(inputs=keywords,outputs=sentence_txtbox_group.children)
    def get_sentences(keyword_list):
        cur_round.set_original_picture(img.value)
        cur_round.set_keyword(keyword_list)

        from engine.function.gen_sentence import genSentences

        return genSentences(cur_round.keyword)
    
    for i in range(3):
        with gr.Row():
            sentence_txtbox=gr.Textbox("",show_label=False,container=False)
            regenerate_btn=gr.Button("Regenerate",scale=0)
            sentence_txtbox_group.add_child(sentence_txtbox)
            choose_btn_group.add_child(gr.Button("Choose",scale=0))

            @regenerate_btn.click(outputs=[sentence_txtbox])
            def regenerate_sentence():
                from engine.function.gen_sentence import generateSentence
                sentence_txtbox.value=generateSentence(cur_round.keyword).content
                return generateSentence(cur_round.keyword).content
            
            
    answer_txtbox=gr.Textbox("",interactive=True,label="Your Answer",autofocus=True)
    for choose_btn in choose_btn_group.children:
        @choose_btn.click(inputs=[choose_btn.parent.children[0]],outputs=[answer_txtbox])
        def update_answer(answer):
            return answer
        
    from engine.function.gen_image import gen_image
    described_image=gr.Image(label="Generated Image",interactive=False)
    answer_txtbox.submit(gen_image,[answer_txtbox],[described_image])

    get_description_btn=gr.Button("Get generated image",scale=0)
    get_description_btn.click(gen_image,[answer_txtbox],[described_image])

    submit_btn=gr.Button("Submit and start scoring",scale=0)
    scoring=gr.Textbox(0,label="Scoring",interactive=False)
    @submit_btn.click(inputs=[img,described_image],outputs=[scoring])
    def scoring(original_img,described_img):
        if described_img is None:
            return "Please generate an image first."
        elif original_img is None:
            return "Please provide an original image first."
        import cv2
        from sewar.full_ref import ssim
        original2=cv2.resize(
            original_img,
            (described_img.shape[1],described_img.shape[0]),
            interpolation=cv2.INTER_AREA
        )
        return ssim(original2,described_img)[0]



if __name__ == "__main__":
    demo.launch(share=not testing)
    