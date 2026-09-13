import json
import re
import time
from datetime import datetime, timezone

from common import (
    ADMIN_CHAT_ID, PENDING_FILE, HISTORY_FILE,
    send_message, groq_chat, load_json, save_json, log,
)
from fetch_sources import fetch_recent_items

SYSTEM_PROMPT = """
You are the content editor for a Persian-language Telegram channel about AI news, free AI tools, and practical tricks.
You will receive a numbered list of raw AI news items (title, summary, source, link).

Your job:
1. Pick the 3 BEST items, prioritized in this order:
   a) A free AI tool or a practical trick/workflow tip (highest priority)
   b) A genuinely new/newsworthy model or research release
   c) How interesting, surprising, or "shareable" it would be to a general tech-curious Persian-speaking audience
2. Reject pure marketing fluff, SEO spam, or anything already stale/well-known.
3. For each of the 3 picks, write a Telegram-ready POST in Persian:
   - "title": short, punchy, curiosity-driving (max ~12 words), NO clickbait lies
   - "description": 2-4 sentences in Persian, clear and engaging, explaining what it is and why it matters / how to use it
   - "source_name": the source name as given
   - "source_link": the link as given

Respond with ONLY valid JSON, no markdown fences, no commentary, in this exact shape:
{
  "picks": [
    {"title": "...", "description": "...", "source_name": "...", "source_link": "..."},
    {"title": "...", "description": "...", "source_name": "...", "source_link": "..."},
    {"title": "...", "description": "...", "source_name": "...", "source_link": "..."}
  ]
}
"""


def build_user_prompt(items):
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i}. [{it['source']}] {it['title']}\n   Summary: {it['summary']}\n   Link: {it['link']}"
        )
    return "Here are today's raw items:\n\n" + "\n\n".join(lines)


def extract_json(text):
    # Groq sometimes wraps JSON in fences despite instructions; strip them defensively.
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    return json.loads(text)


def get_picks_with_retry(user_prompt, attempts=2):
    """Groq occasionally wraps/garbles the JSON despite instructions; retry once
    with a stricter reminder before giving up."""
    last_error = None
    for attempt in range(1, attempts + 1):
        prompt = user_prompt if attempt == 1 else (
            user_prompt + "\n\nReminder: respond with ONLY the raw JSON object, nothing else."
        )
        raw = groq_chat(SYSTEM_PROMPT, prompt)
        try:
            result = extract_json(raw)
            picks = result.get("picks", [])[:3]
            if picks:
                return picks
            last_error = "Model returned an empty 'picks' list."
        except Exception as e:
            last_error = f"{e}\nRaw output:\n{raw}"
        log.warning(f"Attempt {attempt}/{attempts} failed to yield valid picks: {last_error}")
    raise RuntimeError(f"Could not get valid picks from Groq after {attempts} attempts: {last_error}")


def main():
    history = load_json(HISTORY_FILE, {"posted_links": []})
    posted_links = set(history.get("posted_links", []))

    items = fetch_recent_items()
    items = [it for it in items if it["link"] not in posted_links]

    if not items:
        log.info("No fresh, unposted items found today. Skipping.")
        return

    # Cap how much we send to the model to keep prompts small/fast/free-tier-friendly.
    items = items[:60]

    user_prompt = build_user_prompt(items)
    try:
        picks = get_picks_with_retry(user_prompt)
    except RuntimeError as e:
        log.error(str(e))
        return

    # Save pending drafts so the reply-checker knows what "1/2/3" refers to.
    pending = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "picks": picks,
    }
    save_json(PENDING_FILE, pending)

    # Send to Ali for selection.
    message_lines = ["🧠 <b>پیشنهاد امروز — یکی رو با شماره ریپلای کن (۱، ۲ یا ۳)</b>\n"]
    for idx, p in enumerate(picks, 1):
        message_lines.append(
            f"<b>{idx}. {p['title']}</b>\n{p['description']}\n"
            f"منبع: {p.get('source_name','')} — {p.get('source_link','')}\n"
        )
    send_message(ADMIN_CHAT_ID, "\n".join(message_lines))
    log.info(f"Sent {len(picks)} picks to admin for review.")


if __name__ == "__main__":
    main()
