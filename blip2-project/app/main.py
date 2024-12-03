from flask import Flask, request, jsonify
import torch
import uuid, os, PIL

app = Flask(__name__)

from lavis.models import load_model_and_preprocess

device = None
blip2_model = None
vis_processors = None
text_processors = None

def load_blip2_model():
    global blip2_model, vis_processors, text_processors, device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    blip2_model, vis_processors, text_processors = load_model_and_preprocess(
        "blip2_image_text_matching", "pretrain", device=device, is_eval=True
    )

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route('/content_score',methods=['POST'])
def calculate_content_score():
    file = request.files['image']
    handle_id = uuid.uuid4().hex
    sentence = request.form['sentence']
    image_path = f"media/{handle_id}.jpg"

    if file:
        file.save(image_path)

    raw_image = PIL.Image.open(image_path).convert("RGB")

    if blip2_model is None:
        load_blip2_model()

    img = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    txt = text_processors["eval"](sentence)

    itm_output = blip2_model({"image": img, "text_input": txt}, match_head="itm")
    itm_scores = torch.nn.functional.softmax(itm_output, dim=1)
    content_score = itm_scores[:, 1].item()*100
    # print(f'The image and text are matched with a probability of {itm_scores[:, 1].item():.3%}')

    # itc_score = model({"image": img, "text_input": txt}, match_head='itc')
    # print('The image feature and text feature has a cosine similarity of %.4f'%itc_score)
    
    if os.path.isfile(image_path):
        os.remove(image_path)
    
    return jsonify(
        {'content_score':int(round(content_score))}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7874)