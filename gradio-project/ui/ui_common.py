import gradio as gr

class LeftBar:
     
    steps=gr.State([
        {"name":"Choose Picture","complete":False},
        {"name":"Type Keywords","complete":False},
        {"name":"Combine to a sentence","complete":False},
        {"name":"Check Sentence","complete":False},
        {"name":"Generate Picture","complete":False},
        {"name":"Score","complete":False},
    ])

    step_boxes=[]
    step_txtboxes=[]

    def update_step(self,step_name):
        for step in self.steps:
            if step["name"]==step_name:
                step["complete"]=True
                break
         

    def create_left_bar(self):
        for step in self.steps.value:
            with gr.Row():
                step_box=gr.Checkbox(step["name"],step["complete"],show_label=False,container=False,interactive=False)
                self.step_boxes.append(step_box)
                step_txtbox=gr.Textbox(step["name"],show_label=False,container=False)
                self.step_txtboxes.append(step_txtbox)
