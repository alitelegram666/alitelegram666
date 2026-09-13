import sys
import os
from datetime import datetime, timedelta, timezone
import feedparser

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "config"))
from sources import FEEDS, LOOKBACK_HOURS, MAX_ITEMS_PER_FEED  # noqa: E402
from common import log  # noqa: E402


def _to_dt(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_recent_items():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items = []

    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            if getattr(parsed, "bozo", 0) and not parsed.entries:
                raise ValueError(getattr(parsed, "bozo_exception", "unparseable feed"))
        except Exception as e:
            log.warning(f"failed to fetch {feed['name']}: {e}")
            continue

        count = 0
        for entry in parsed.entries:
            if count >= MAX_ITEMS_PER_FEED:
                break
            dt = _to_dt(entry)
            if dt and dt < cutoff:
                continue  # too old
            items.append({
                "source": feed["name"],
                "tag": feed["tag"],
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "summary": (entry.get("summary", "") or "")[:500],
            })
            count += 1

    return items


if __name__ == "__main__":
    found = fetch_recent_items()
    log.info(f"Fetched {len(found)} fresh items")
    for it in found[:10]:
        log.info(f"- {it['source']} | {it['title']}")
