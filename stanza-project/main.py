from flask import Flask, request, jsonify
import stanza

# Initialize Stanza NLP pipeline
nlp = stanza.Pipeline(lang='en', processors='tokenize,pos,constituency', package='default_accurate')

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_text():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Process the text with Stanza
    doc = nlp(text)
    response = []
    for sentence in doc.sentences:

        response.append
        for word in sentence.words:
            response.append({
                "text": word.text,
                "lemma": word.lemma,
                "pos": word.pos,
                "ner": word.ner
            })
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
