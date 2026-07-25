import feedparser
import requests
import json
import os

# 1. Target R&D Feeds
RSS_FEEDS = [
    "https://medium.com/feed/tag/flutter",
    "https://medium.com/feed/tag/ios-app-development",
    "https://medium.com/feed/tag/android-development",
    "https://medium.com/feed/tag/artificial-intelligence"
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HISTORY_FILE = "history.json"

AI_PROMPT_TEMPLATE = """
You are an expert mobile R&D engineer reviewer. Analyze this article metadata:
Title: {title}
Snippet: {description}

Determine if this article covers deep technical architecture, native bridging (Swift/Kotlin/C++), advanced state management, engine compilation, or mobile AI agent implementations. 
Ignore generic beginner tutorials, simple UI layouts, listicles ("Top 5 packages"), or introductory fluff.

Return your response strictly in JSON format:
{{
  "is_relevant": true/false,
  "reason": "One concise sentence explaining why this matches advanced R&D mobile engineering."
}}
"""

def load_history():
    """Loads the set of previously processed URLs from a local JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            print(f"⚠️ Warning: Failed to parse history file, starting fresh. Error: {e}")
            return set()
    return set()

def save_history(processed_urls):
    """Saves the updated list of processed URLs back to the local JSON file."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(sorted(list(processed_urls)), f, indent=2)
        print("✅ History file updated successfully.")
    except Exception as e:
        print(f"❌ Error saving history file: {e}")

def filter_article_with_ai(title, description):
    """Sends article metadata to Gemini to check for high-signal R&D value."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = AI_PROMPT_TEMPLATE.format(title=title, description=description)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        text_response = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(text_response)
    except Exception as e:
        print(f"❌ AI evaluation failed for '{title}': {e}")
        return {"is_relevant": False, "reason": ""}

def send_to_telegram(title, link, reason):
    """Dispatches a formatted Markdown alert to your Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Telegram MarkdownV2 requires escaping characters, but standard HTML parsing is cleaner for dynamic text
    message_text = (
        f"🚨 <b>New R&D Article Found!</b>\n\n"
        f"<b>Title:</b> {title}\n"
        f"<b>Why it matters:</b> {reason}\n\n"
        f"🔗 <a href='{link}'>Read Article on Medium</a>"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False  # Keeps the clean Medium link preview active
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"❌ Telegram API Error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

def main():
    processed_urls = load_history()
    new_discoveries = 0
    
    print(f"Starting feed scan. History contains {len(processed_urls)} tracked articles.")
    
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:7]: 
            if entry.link in processed_urls:
                continue
                
            print(f"🔍 Analyzing new item: {entry.title}")
            analysis = filter_article_with_ai(entry.title, entry.get('summary', ''))
            
            if analysis.get("is_relevant"):
                print(f"🎯 Match found: {entry.title}")
                send_to_telegram(entry.title, entry.link, analysis.get("reason"))
            
            processed_urls.add(entry.link)
            new_discoveries += 1

    if new_discoveries > 0:
        save_history(processed_urls)
    else:
        print("💤 No new articles found across monitored feeds.")

if __name__ == "__main__":
    main()
