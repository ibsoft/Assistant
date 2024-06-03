# Assistant
AI Assistant


Install Ollama

curl -fsSL https://ollama.com/install.sh | sh

ollama pull all-minilm

ollama pull tinydolphin

cd Assistant

python -m venv venv

source venv/bin/activate

flask run

http://localhost:5000
