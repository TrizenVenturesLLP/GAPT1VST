from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from yt_dlp import YoutubeDL
import whisper
from transformers import pipeline, MBartForConditionalGeneration, MBart50TokenizerFast, MBartConfig, AutoModelForQuestionAnswering, AutoTokenizer

app = Flask(__name__)
CORS(app)

# Initialize Whisper and Summarizer
whisper_model = whisper.load_model("base")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Initialize MBart model and tokenizer
model_dir = "./mbart_model"

def load_mbart_model(model_dir):
    if not os.path.exists(model_dir):
        config = MBartConfig.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
        config.early_stopping = True  # Set early_stopping parameter
        model = MBartForConditionalGeneration.from_pretrained(
            "facebook/mbart-large-50-many-to-many-mmt",
            config=config
        )
        tokenizer = MBart50TokenizerFast.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
        model.save_pretrained(model_dir)
        tokenizer.save_pretrained(model_dir)
        return model, tokenizer
    else:
        config = MBartConfig.from_pretrained(model_dir)
        config.early_stopping = True  # Set early_stopping parameter
        return (
            MBartForConditionalGeneration.from_pretrained(model_dir, config=config),
            MBart50TokenizerFast.from_pretrained(model_dir)
        )

mbart_model, mbart_tokenizer = load_mbart_model(model_dir)

def translate_to_telugu(text):
    print("transl****", text)
    if text is not None and isinstance(text, str):
        encoded_text = mbart_tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        mbart_tokenizer.src_lang = "en_XX"
        forced_bos_token_id = mbart_tokenizer.lang_code_to_id["te_IN"]
        generated_tokens = mbart_model.generate(**encoded_text, forced_bos_token_id=forced_bos_token_id)
        translation = mbart_tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        return translation[0]
    return None

def youtube_to_audio(youtube_url, output_directory="./audio_output"):
    try:
        os.makedirs(output_directory, exist_ok=True)
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": os.path.join(output_directory, "%(title)s.%(ext)s"),
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            base_filename = os.path.splitext(filename)[0]
            return f"{base_filename}.mp3"
    except Exception as e:
        raise Exception(f"Error downloading audio: {str(e)}")

def transcribe_audio(audio_file):
    result = whisper_model.transcribe(audio_file)
    return result['text']

def summarize_text(text):
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    return summary[0]['summary_text']

model_name = "deepset/roberta-base-squad2"
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer)

@app.route('/api/chat', methods=['POST'])
def chat_about_summary():
    try:
        data = request.get_json()
        question = data.get('question')
        summary = data.get('summary')
        
        if not question or not summary:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Use the QA pipeline to get an answer
        qa_result = qa_pipeline({
            'question': question,
            'context': summary
        })
        
        response = qa_result['answer']
        print("********", response)
        return jsonify({
            'response': response
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summarize', methods=['POST'])
def get_summary():
    try:
        data = request.get_json()
        youtube_url = data.get('url')
        
        if not youtube_url:
            return jsonify({'error': 'No URL provided'}), 400
            
        # Download and convert to audio
        audio_file = youtube_to_audio(youtube_url)
        
        # Transcribe audio
        transcription = transcribe_audio(audio_file)
        
        # Generate summary
        summary = summarize_text(transcription)
        
        # Clean up audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        return jsonify({
            'summary': summary,
            'transcription': transcription
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text = data.get('text')
        target_language = data.get('target_language')
        
        if not text:
            return jsonify({'error': 'Missing text'}), 400
            
        if target_language == 'te':
            translated_text = translate_to_telugu(text)
            return jsonify({
                'translated_text': translated_text
            })
        else:
            # For now, return mock translation for other languages
            translated_text = f"[{target_language}] {text}"
            return jsonify({
                'translated_text': translated_text 
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.get_json()
        summary = data.get('summary')
        
        if not summary:
            return jsonify({'error': 'Missing summary'}), 400
            
        # For now, return mock questions (implement proper quiz generation later)
        questions = [
            {
                'question': 'What is the main topic discussed in the summary?',
                'options': ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
                'correctAnswer': 0
            },
            {
                'question': 'What is a key point mentioned in the summary?',
                'options': ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
                'correctAnswer': 1
            }
        ]
        
        return jsonify({'questions': questions})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)