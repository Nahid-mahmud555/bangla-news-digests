import os
import time
import requests
import feedparser
from bs4 import BeautifulSoup
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from deep_translator import GoogleTranslator

# NLTK টোকেনাইজার ডাউনলোড (GitHub Actions-এ রান হওয়ার জন্য)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

# টেলিগ্রাম তথ্য (GitHub Secrets থেকে নেবে)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# টপ ইংলিশ নিউজ ও রিসার্চ ফিড
FEEDS = {
    "🌍 বিশ্ব সংবাদ (BBC)": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "🔬 নতুন বিজ্ঞান ও গবেষণা (ScienceDaily)": "https://www.sciencedaily.com/rss/all.xml",
    "🚀 প্রযুক্তি ও উদ্ভাবন (Ars Technica)": "https://feeds.arstechnica.com/arstechnica/index",
    "🌌 মহাকাশ ও নাসা (NASA)": "https://www.nasa.gov/rss/dyn/breaking_news.rss"
}

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()

def get_extractive_summary(text, sentences_count=2):
    if not text or len(text.split()) < 25:
        return text
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, sentences_count)
    return " ".join(str(sentence) for sentence in summary)

def translate_to_bangla(text):
    if not text:
        return ""
    try:
        # গুগল ট্রান্সলেটর ফ্রি ওয়েব লিমিট (৫০০০ ক্যারেক্টারের নিচে রাখা ভালো)
        return GoogleTranslator(source='en', target='bn').translate(text[:4000])
    except Exception as e:
        print(f"Translation Error: {e}")
        return text

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing! Printing output instead:\n")
        print(message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        print(f"Telegram Error: {resp.text}")

def build_and_send_digest():
    translator_sleep = 3  # ব্লক এড়াতে ৩ সেকেন্ড বিরতি

    for category, feed_url in FEEDS.items():
        parsed = feedparser.parse(feed_url)
        entries = parsed.entries[:3]  # প্রতিটি সাইট থেকে সেরা ৩টি খবর
        
        if not entries:
            continue

        message_block = f"<b>{category}</b>\n" + ("—" * 15) + "\n\n"

        for entry in entries:
            raw_title = clean_html(entry.get("title", ""))
            raw_summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")

            # সামারি ও বাংলা অনুবাদ
            short_eng_summary = get_extractive_summary(raw_summary, sentences_count=2)
            bn_title = translate_to_bangla(raw_title)
            time.sleep(translator_sleep)
            
            bn_summary = translate_to_bangla(short_eng_summary)
            time.sleep(translator_sleep)

            message_block += (
                f"🔹 <b>{bn_title}</b>\n"
                f"{bn_summary}\n"
                f"🔗 <a href='{link}'>মূল আর্টিকেল পড়ুন</a>\n\n"
            )

        # টেলিগ্রাম মেসেজ লিমিট (৪০৯৬ ক্যারেক্টার) ঠিক রাখতে ক্যাটাগরি অনুযায়ী পাঠানো
        send_telegram_message(message_block)
        time.sleep(2)

if __name__ == "__main__":
    build_and_send_digest()
