"""
Offline end-to-end smoke test — no real network calls.

It fakes:
  - feedparser (so we don't need the real package or internet)
  - the Telegram + Groq HTTP calls (via monkeypatching the shared session)

...and walks through the full flow:
  1. score_and_draft.main()   -> should send 3 picks and write data/pending.json
  2. check_and_publish.main() -> simulate Ali replying "2", should publish pick #2
                                   to the channel and clear pending.json

Run with:  python3 tests/smoke_test.py
Exits with code 0 and prints "ALL TESTS PASSED" on success.
"""

import os
import sys
import json
import types
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "config"))

# ---- 1. Fake required secrets before anything imports common.py ----
os.environ["TELEGRAM_BOT_TOKEN"] = "TEST_TOKEN"
os.environ["TELEGRAM_ADMIN_CHAT_ID"] = "111111"
os.environ["TELEGRAM_CHANNEL_ID"] = "@test_channel"
os.environ["GROQ_API_KEY"] = "TEST_GROQ_KEY"

# ---- 2. Fake the feedparser module so fetch_sources doesn't need internet ----
fake_feedparser = types.ModuleType("feedparser")


def fake_parse(url):
    entry = {
        "title": f"Fake fresh item from {url}",
        "link": f"{url}#item1",
        "summary": "A free AI tool that does something genuinely useful.",
    }
    result = types.SimpleNamespace()
    result.bozo = 0
    result.entries = [entry]
    return result


fake_feedparser.parse = fake_parse
sys.modules["feedparser"] = fake_feedparser

# ---- 3. Import our modules now that the environment is patched ----
import common  # noqa: E402
import fetch_sources  # noqa: E402
import score_and_draft  # noqa: E402
import check_and_publish  # noqa: E402

sent_messages = []  # capture every "message" we send, for assertions


def fake_session_post(url, json=None, headers=None, timeout=None):
    resp = MagicMock()
    resp.raise_for_status = lambda: None

    if "api.groq.com" in url:
        # Simulate the model returning 3 valid picks.
        fake_payload = {
            "picks": [
                {"title": "ابزار رایگان شماره ۱", "description": "توضیح ۱.",
                 "source_name": "Test Source", "source_link": "https://example.com/1"},
                {"title": "ابزار رایگان شماره ۲", "description": "توضیح ۲.",
                 "source_name": "Test Source", "source_link": "https://example.com/2"},
                {"title": "ابزار رایگان شماره ۳", "description": "توضیح ۳.",
                 "source_name": "Test Source", "source_link": "https://example.com/3"},
            ]
        }
        resp.json = lambda: {"choices": [{"message": {"content": json_dumps(fake_payload)}}]}
        return resp

    if "api.telegram.org" in url:
        method = url.rsplit("/", 1)[-1]
        if method == "getUpdates":
            # Simulate Ali replying "2" in his private chat with the bot.
            resp.json = lambda: {
                "ok": True,
                "result": [{
                    "update_id": 1001,
                    "message": {
                        "chat": {"id": 111111},
                        "text": "2",
                    },
                }],
            }
            return resp
        if method == "sendMessage":
            sent_messages.append(json)
            resp.json = lambda: {"ok": True, "result": {}}
            return resp

    raise AssertionError(f"Unexpected POST to {url}")


def json_dumps(obj):
    import json as _json
    return _json.dumps(obj, ensure_ascii=False)


common._session.post = fake_session_post

# ---- 4. Run the daily digest step ----
data_dir = common.DATA_DIR
common.save_json(common.PENDING_FILE, {})
common.save_json(common.STATE_FILE, {"last_update_id": 0})
common.save_json(common.HISTORY_FILE, {"posted_links": []})

score_and_draft.main()

pending = common.load_json(common.PENDING_FILE, None)
assert pending and len(pending["picks"]) == 3, "Expected 3 picks to be saved to pending.json"
assert len(sent_messages) == 1, "Expected exactly one Telegram message to the admin"
assert "ابزار رایگان شماره ۱" in sent_messages[0]["text"], "Admin message should list pick #1"
print("[OK] Daily digest step: 3 picks generated and sent to admin.")

# ---- 5. Run the reply-check/publish step (simulating reply "2") ----
sent_messages.clear()
check_and_publish.main()

history = common.load_json(common.HISTORY_FILE, {"posted_links": []})
pending_after = common.load_json(common.PENDING_FILE, None)

assert len(sent_messages) == 2, "Expected a channel post + an admin confirmation"
channel_post = sent_messages[0]
assert "ابزار رایگان شماره ۲" in channel_post["text"], "Should publish pick #2 (the one Ali replied with)"
assert channel_post["chat_id"] == "@test_channel", "Should publish to the configured channel"
assert "https://example.com/2" in history["posted_links"], "Chosen link should be recorded in history"
assert pending_after == {}, "Pending picks should be cleared after publishing"
print("[OK] Reply step: pick #2 correctly published to the channel and history updated.")

print("\nALL TESTS PASSED")
