import os
import time
import requests
import feedparser
from bs4 import BeautifulSoup
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from deep_translator import GoogleTranslator, MyMemoryTranslator

# NLTK টোকেনাইজার ডাউনলোড
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# বিশ্ব সংবাদ, টেক আপডেট, নতুন উদ্ভাবন ও রিসার্চ পেপার সোর্স
FEEDS = {
    "🌍 বিশ্ব সংবাদ (BBC)": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "💻 টেক নিউজ ও আপডেট (Ars Technica)": "https://feeds.arstechnica.com/arstechnica/index",
    "⚡ টেক ও গ্যাজেট আপডেট (The Verge)": "https://www.theverge.com/rss/index.xml",
    "🚀 নতুন প্রযুক্তি ও উদ্ভাবন (MIT Tech Review)": "https://www.technologyreview.com/feed/",
    "🔬 বিজ্ঞান ও গবেষণা (ScienceDaily)": "https://www.sciencedaily.com/rss/all.xml",
    "🧠 গভীর গবেষণা ও বিজ্ঞান (Quanta)": "https://www.quantamagazine.org/feed/",
    "📄 রিসার্চ পেপার - AI (arXiv cs.AI)": "https://rss.arxiv.org/rss/cs.AI",
    "📄 রিসার্চ পেপার - ML (arXiv cs.LG)": "https://rss.arxiv.org/rss/cs.LG",
    "🌌 মহাকাশ ও নাসা (NASA)": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ")
    return " ".join(text.split()).strip()

def get_extractive_summary(text, sentences_count=2):
    if not text or len(text.split()) < 20:
        return text
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentences_count)
        result = " ".join(str(sentence) for sentence in summary).strip()
        return result if result else text[:350]
    except Exception as e:
        print(f"Summary fallback: {e}")
        return text[:350]

def has_bangla(text):
    return any('\u0980' <= ch <= '\u09ff' for ch in text)

def translate_to_bangla(text):
    if not text:
        return ""

    clean_text = text[:1000]

    # ১ম চেষ্টা: GoogleTranslator
    for attempt in range(2):
        try:
            res = GoogleTranslator(source='en', target='bn').translate(clean_text)
            if res and has_bangla(res):
                return res
        except Exception as e:
            print(f"GoogleTranslator attempt {attempt + 1} failed: {e}")
            time.sleep(6 * (attempt + 1))

    # ২য় চেষ্টা: MyMemoryTranslator (ব্যাকআপ)
    try:
        res = MyMemoryTranslator(source='en-GB', target='bn-BD').translate(clean_text[:500])
        if res and has_bangla(res):
            return res
    except Exception as e:
        print(f"MyMemoryTranslator failed: {e}")

    # কোনোটাতেই বাংলা না এলে মূল ইংরেজি লেখাটিই দেবে
    return clean_text

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing!\n")
        print(message)
        return

    max_len = 3900
    chunks = [message[i:i + max_len] for i in range(0, len(message), max_len)]

    for chunk in chunks:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code != 200:
                print(f"Telegram Error: {resp.text}")
        except Exception as e:
            print(f"Request Error: {e}")
        time.sleep(2)

def build_and_send_digest():
    for category, feed_url in FEEDS.items():
        try:
            parsed = feedparser.parse(feed_url)
            entries = parsed.entries[:2]
        except Exception as e:
            print(f"Feed parse error ({category}): {e}")
            continue

        if not entries:
            print(f"No entries found for {category}")
            continue

        message_block = f"<b>{category}</b>\n" + ("—" * 15) + "\n\n"

        for entry in entries:
            raw_title = clean_html(entry.get("title", ""))
            raw_summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")

            short_eng_summary = get_extractive_summary(raw_summary, sentences_count=2)

            combined_en = f"Title: {raw_title}\nSummary: {short_eng_summary}"
            bn_combined = translate_to_bangla(combined_en)
            time.sleep(7)

            safe_bn = bn_combined.replace("<", "&lt;").replace(">", "&gt;")

            message_block += (
                f"🔹 {safe_bn}\n"
                f"🔗 <a href='{link}'>মূল আর্টিকেল / পেপার দেখুন</a>\n\n"
            )

        send_telegram_message(message_block)
        time.sleep(5)

if __name__ == "__main__":
    build_and_send_digest()
