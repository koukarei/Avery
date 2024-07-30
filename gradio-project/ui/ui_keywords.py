import gradio as gr

class Keywords:
    """Create a keywords object for the user interface.
        AI keyword cannot be removed.
        User keyword can be added or removed.
    """
    
    def __init__(self):
        self.keywords=gr.State([])
        self.new_keyword=None
        self.new_keyword_btn=None
        self.ask_keyword_btn=None
        self.submit_btn=None
        self.keywords_txtbox=None
        self.keyword_list=None
        self.image=None
        self.example_keywords=[
                {"name":"A sloth","source":"user","remove":False},
                {"name":"red car","source":"system","remove":False},
                {"name":"driving","source":"user","remove":False},
                {"name":"smiling","source":"system","remove":False},
            ]
        

        def render_keywords(keyword_list):
            for keyword in keyword_list:
                with gr.Row():
                    gr.Textbox(keyword['name'],show_label=False,container=False)

                    remove_btn=gr.Button("Remove",scale=0)
                    def remove_keyword(keyword=keyword):
                        keyword_list.remove(keyword)
                        return keyword_list
                    remove_btn.click(remove_keyword,None,[self.keywords])
                    if keyword['source']=="system":
                        remove_btn.interactive=False

        self.render_keywords=render_keywords
    
    def create_new_keyword_textbox(self):
        self.new_keyword=gr.Textbox(label="Keyword",autofocus=True)

        def add_keyword(keywords,new_keyword):
            return keywords+[{"name":new_keyword,"source":"user","remove":False}],""
        self.add_keyword=add_keyword
        self.new_keyword.submit(add_keyword,[self.keywords,self.new_keyword],[self.keywords,self.new_keyword])

    def create_add_keyword_button(self):
        with gr.Row():
            
            self.new_keyword_btn=gr.Button("Add keyword",scale=0)
            self.new_keyword_btn.click(self.add_keyword,[self.keywords,self.new_keyword],[self.keywords,self.new_keyword])
        
            self.ask_keyword_btn=gr.Button("Add AI keyword",scale=0)        
            def ask_keyword(img,keyword_list):
                from function.keywords import get_ai_keywords
                keywords=[keyword['name'] for keyword in keyword_list]
                ai_keyword=get_ai_keywords(img,current_keywords=keywords)
                if ai_keyword:
                    ai_keyword=ai_keyword[0]
                return keyword_list+[{"name":ai_keyword,"source":"system","remove":False}]
            self.ask_keyword_btn.click(ask_keyword,[self.image,self.keywords],[self.keywords])

    def create_keywords_row(self,test=False):
        if not test:
            self.example_keyword=[]

        def submit(keyword_list):
            keyword_list=self.example_keyword
            return keyword_list
        self.submit=submit
    
    def create_image(self,image):
        if isinstance(image,gr.components.Image):
            from PIL import Image as Im
            image=Im.fromarray(image.value)
        self.image=gr.Image(
            image,
            label="Give keywords to describe the image.",
            interactive=False,
        )
    
    def create_keyword_tab(self,image_path,test=False):
        
        self.create_image(image_path)
        self.create_new_keyword_textbox()
        self.create_add_keyword_button()
        self.create_keywords_row(test)
        self.submit_btn=gr.Button("Submit",scale=0)


                                    