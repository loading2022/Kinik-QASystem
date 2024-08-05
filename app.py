from flask import Flask, render_template, request, jsonify
import os
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain_community.callbacks import get_openai_callback
from langchain_openai import AzureChatOpenAI
from opencc import OpenCC
import io
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE_URL = os.getenv("AZURE_OPENAI_ENDPOINT")
#openai.api_type = "azure"
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_MODEL") 
OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

app = Flask(__name__)

class NamedBytesIO(io.BytesIO):
    name = 'transcript.wav'

chat_history = []
data_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

if not os.path.exists(data_folder):
    os.makedirs(data_folder)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    user_input = request.form.get('user_input')
    if not user_input:
        return jsonify({'error': 'No user input provided'})
    if user_input:
        embeddings = AzureOpenAIEmbeddings()
        dir_path="./db/"
        new_db = None
        for db in os.listdir(dir_path):
            print(f"db name:{db}")
            db=FAISS.load_local(os.path.join(dir_path,db),embeddings, allow_dangerous_deserialization=True)
            if new_db is None:
                new_db = db
            else:
                new_db.merge_from(db)
        #print(new_db.docstore._dict)
        
        docs = new_db.similarity_search(user_input)
        llm = AzureChatOpenAI(
            #deployment_name=OPENAI_DEPLOYMENT_NAME,
            model_name="gpt-4o",
            api_key=OPENAI_API_KEY,
            #azure_endpoint=OPENAI_API_BASE_URL,
            #api_version=OPENAI_API_VERSION
        )

        chain = load_qa_chain(llm, chain_type="stuff")

        with get_openai_callback() as cb:
            response = chain.invoke({"input_documents": docs,"question":user_input}, return_only_outputs=True)
        cc = OpenCC('s2t')
        answer=cc.convert(response['output_text'])
        
        chat_history.append({'user': user_input, 'assistant': response['output_text']})
        return jsonify({'response': answer})

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    audio_file = request.files['audio']
    if audio_file:
        audio_stream = NamedBytesIO(audio_file.read())
        audio_stream.name = 'transcript.wav' 

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_stream,
            response_format='text'
        )
        cc = OpenCC('s2t')
        text = cc.convert(transcript)
        return jsonify({'message': '音頻已處理', 'transcript': text})
    return jsonify({'error': '沒有接收到音訊文件'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000), host='0.0.0.0')  
