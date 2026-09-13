from common import (
    ADMIN_CHAT_ID, CHANNEL_ID, PENDING_FILE, STATE_FILE, HISTORY_FILE,
    send_message, get_updates, load_json, save_json, log,
)


def main():
    pending = load_json(PENDING_FILE, None)
    if not pending or not pending.get("picks"):
        log.info("No pending picks waiting for a reply. Nothing to do.")
        return

    state = load_json(STATE_FILE, {"last_update_id": 0})
    last_update_id = state.get("last_update_id", 0)

    updates = get_updates(offset=last_update_id + 1).get("result", [])
    if not updates:
        log.info("No new Telegram updates.")
        return

    chosen_idx = None
    max_update_id = last_update_id

    for upd in updates:
        max_update_id = max(max_update_id, upd["update_id"])
        msg = upd.get("message") or {}
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text = (msg.get("text") or "").strip()

        if chat_id != str(ADMIN_CHAT_ID):
            continue
        if text in ("1", "2", "3"):
            chosen_idx = int(text) - 1

    # Always advance the offset so we don't reprocess old messages next run.
    state["last_update_id"] = max_update_id
    save_json(STATE_FILE, state)

    if chosen_idx is None:
        log.info("No valid 1/2/3 reply found yet.")
        return

    picks = pending["picks"]
    if chosen_idx >= len(picks):
        log.info("Reply number out of range, ignoring.")
        return

    chosen = picks[chosen_idx]
    post_text = (
        f"<b>{chosen['title']}</b>\n\n{chosen['description']}\n\n"
        f"منبع: {chosen.get('source_name','')}"
    )
    if chosen.get("source_link"):
        post_text += f"\n{chosen['source_link']}"

    send_message(CHANNEL_ID, post_text)
    send_message(ADMIN_CHAT_ID, f"✅ پست شماره {chosen_idx + 1} توی کانال منتشر شد.")

    # Record history to avoid re-suggesting the same link, and clear pending.
    history = load_json(HISTORY_FILE, {"posted_links": []})
    if chosen.get("source_link"):
        history["posted_links"].append(chosen["source_link"])
        history["posted_links"] = history["posted_links"][-500:]  # keep it small
    save_json(HISTORY_FILE, history)
    save_json(PENDING_FILE, {})

    log.info(f"Published pick #{chosen_idx + 1} to channel.")


if __name__ == "__main__":
    main()
