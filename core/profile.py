"""Business profile: services, areas, offer. Edit business_profile.json to demo for ANY company."""
import json
import re

from . import config


def load() -> dict:
    return json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))


def has_word(text: str, words: list[str]) -> bool:
    """Whole-word keyword match ('plants' must not trigger 'ants'). Arabic: substring.
    Words up to 4 letters match whole words (plural s allowed); longer ones match as a word prefix."""
    text = text.lower()
    for w in words:
        w = w.lower().strip()
        if not w:
            continue
        if re.search(r"[؀-ۿ]", w):
            if w in text:
                return True
        elif len(w) <= 4:
            if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?:s|es)?(?![a-z0-9])", text):
                return True
        elif re.search(r"(?<![a-z0-9])" + re.escape(w), text):
            return True
    return False


def service_label(profile: dict, key: str | None, lang: str = "en") -> str:
    for s in profile["services"]:
        if s["key"] == key:
            return s["label_ar"] if lang == "ar" else s["label"]
    return key or ""
