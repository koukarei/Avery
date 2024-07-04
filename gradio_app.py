import gradio as gr
from engine.models.round import Round
from typing import List

testing=True

cur_round=Round()

with gr.Blocks() as demo:

    from ui.ui_gallery import Gallery
    gallery=Gallery()
    with gr.Row():
        gallery.create_gallery()

    @gallery.submit_btn.click(inputs=[gallery.image],outputs=None)
    def submit_picture(image):
        gallery.hide_gallery()
        cur_round.set_original_picture(image)
        return None

    
    for i in range(3):
        with gr.Row():
            sentence_txtbox=gr.Textbox("",show_label=False,container=False)
            regenerate_btn=gr.Button("Regenerate",scale=0)
            sentence_txtbox_group.add_child(sentence_txtbox)
            choose_btn_group.add_child(gr.Button("Choose",scale=0))

            @regenerate_btn.click(outputs=[sentence_txtbox])
            def regenerate_sentence():
                from engine.function.sentence import generateSentence
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
    @submit_btn.click(inputs=[gallery.image,described_image],outputs=[scoring])
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
    