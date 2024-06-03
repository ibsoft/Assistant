from flask import Flask, render_template, request, session
from flask_bootstrap import Bootstrap
import requests
import chromadb
import json

app = Flask(__name__)
Bootstrap(app)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Define the template prompt
template = """ You're an excellent IT service assistant trained to provide the best assistance to Unixfor's clients. Your task is to use the following pieces of context to answer the question at the end in a natural language form.
The company you work for is Unixfor, and you have been assisting clients with their IT service needs for years.
You are well-versed in troubleshooting technical issues, providing kiosk hardware devices and software support, and ensuring smooth operation of systems.
Respond to every client queries in a concise, polite and helpful manner only from your context or you will be penalized. 
Remember, making up answers is not allowed. Direct clients to call helpdesk department at 210.9987500 or email s3support@unixfor.gr.

{context}
Question: {question}
Helpful Answer:
"""

# Define functions to interact with the Ollama API


def get_embedding(text):
    url = "http://localhost:11434/api/embeddings"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "all-minilm",
        "prompt": text
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        try:
            response_json = response.json()
            return response_json["embedding"]
        except (json.decoder.JSONDecodeError, KeyError):
            print("Error decoding JSON response or missing 'embedding' key:")
            print(response.content)
            return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


def generate_response(prompt, temperature=0):
    url = "http://localhost:11434/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "tinydolphin",
        "prompt": prompt,
        "temperature": temperature
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        try:
            # Collecting all fragments of the response
            response_lines = response.text.strip().split('\n')
            response_text = ''.join([json.loads(line)["response"]
                                    for line in response_lines if line])
            return response_text
        except (json.decoder.JSONDecodeError, KeyError) as e:
            print("Error decoding JSON response or missing 'response' key:")
            print(response.content)
            return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


# Load documents from the external JSON file
with open('dataset.json', 'r', encoding='utf-8') as f:
    documents = json.load(f)

# Initialize ChromaDB client and collection
client = chromadb.Client()
if "docs" in client.list_collections():
    client.delete_collection(name="docs")
collection = client.create_collection(name="docs")

# Store each document in a vector embedding database
for i, doc in enumerate(documents):
    embedding = get_embedding(doc["text"])
    if embedding:
        collection.add(
            ids=[str(i)],
            embeddings=[embedding],
            documents=[doc["text"]]
        )

print("Done")


@app.route('/')
def index():
    session['chat_history'] = []
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    prompt = request.form['prompt']
    chat_history = session.get('chat_history', [])

    # Generate an embedding for the prompt and retrieve the most relevant doc
    query_embedding = get_embedding(prompt)
    if query_embedding:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        context = results['documents'][0][0]

        # Use the template prompt to generate a formatted prompt
        formatted_prompt = template.format(context=context, question=prompt)

        # Generate a response using the formatted prompt
        response_text = generate_response(formatted_prompt,temperature=0)
        if not response_text:
            response_text = "Error generating response."

        chat_history.append(
            {'sender': 'You', 'message': prompt, 'response': response_text})
        session['chat_history'] = chat_history

    return render_template('chat.html', chat_history=chat_history)


if __name__ == '__main__':
    app.run(debug=True)
