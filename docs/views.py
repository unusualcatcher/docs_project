import os
import requests
import sys
import json
from django.shortcuts import render
from dotenv import load_dotenv
import google.generativeai as genai
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from bs4 import BeautifulSoup
from googletrans import Translator
from django.views.decorators.csrf import csrf_exempt
# Ensure the terminal output is UTF-8 encoded
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables (if not loaded in settings.py)
load_dotenv()

# Configure the Google Gemini API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))  

# Initialize the Gemini Pro model
model = genai.GenerativeModel("gemini-pro")
chat_instance = model.start_chat(history=[])  # Renamed variable

# Function to get Gemini response
def get_gemini_response(question):
    response = chat_instance.send_message(question, stream=True)  # Updated to use chat_instance
    return response


def scrape_and_translate(url: str, target_language: str = 'hi'):
    # Get the HTML from the specified URL
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        source = response.text
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None  # Return None or an appropriate message

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(source, 'lxml')

    # Remove non-text elements like scripts, styles, and code blocks
    for element in soup(['script', 'style', 'code', 'pre']):
        element.extract()

    # Extract the text content
    text_content = soup.get_text(separator=" ", strip=True)
    print(text_content)  # Check what text is extracted

    # Initialize the Translator
    translator = Translator()

    try:
        # Translate the text content to the target language
        translated_text = translator.translate(text=text_content, src='auto', dest=target_language).text
        print(translated_text)  # Print the translated text
        return translated_text
    except Exception as e:
        print(f"Translation error: {e}")
        return None  # Handle the translation error gracefully


# View to handle the Q&A and rendering the page
def chat_view(request):  # Renamed view function to chat_view
    # Initialize chat history in session if it doesn't exist
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []

    if request.method == "POST":
        user_input = request.POST.get("input")

        if user_input:
            # Get the Gemini response
            response = get_gemini_response(user_input)

            # Store user query and bot response in session
            request.session['chat_history'].append(("You", user_input))
            bot_response = "".join([chunk.text for chunk in response])
            request.session['chat_history'].append(("Bot", bot_response))

            # Ensure session is saved
            request.session.modified = True

    # Render the Q&A page with chat history
    return render(request, 'docs/chat.html', {
        'chat_history': request.session['chat_history']
    })

def translate(text, language):
    translator = Translator()
    translated_text = translator.translate(text=text, src='auto', dest=language).text
    return translated_text

@csrf_exempt 
def translate_text(request):
    if request.method == 'POST':
        # Parse JSON data from the request body
        try:
            body = json.loads(request.body)
            text = body.get('text')  # Extract the text to translate
            language = body.get('target_language')  # Extract the target language
            print("Language:",language)
            if not text or not language:
                return JsonResponse({'error': 'Text and language are required.'}, status=400)
            
            # Translate the text
            translated_text = translate(text, language)
            
            # Return the translated text in a JSON response
            return JsonResponse({'translated_text': translated_text})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    else:
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

@csrf_exempt
def translate_page_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        url_to_translate = data.get('url')
        target_language = data.get('target_language')
        txt = scrape_and_translate(url_to_translate, target_language)

        if txt is None:  # Check if translation failed
            return JsonResponse({'error': 'Failed to translate the text.'}, status=500)

        return JsonResponse({'translated_text': txt})
