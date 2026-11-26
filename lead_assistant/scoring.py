"""Transparent lead scoring: every point has a reason, so sales can see WHY a lead is hot."""

HOT, WARM = 65, 35


def score_lead(lead: dict, message_count: int = 1) -> tuple[int, str, list[str]]:
    intent = lead.get("intent")
    if intent == "spam":
        return 0, "spam", ["looks like spam"]
    reasons, s = ["base 10"], 10

    def add(points: int, why: str):
        nonlocal s
        s += points
        reasons.append(f"+{points} {why}")

    if intent in ("pricing", "booking"):
        add(30, f"asked for {intent}")
    elif intent == "inquiry":
        add(15, "service inquiry")
    if lead.get("interest"):
        add(15, "knows which service")
    if lead.get("budget_bhd"):
        add(15, "shared a budget")
    if lead.get("urgency") == "high":
        add(20, "urgent")
    elif lead.get("urgency") == "medium":
        add(5, "normal urgency")
    if lead.get("timeline"):
        add(10, "has a timeline")
    if lead.get("area"):
        add(5, "gave their area")
    if lead.get("name"):
        add(5, "gave their name")
    if lead.get("email"):
        add(5, "gave an email")
    if message_count >= 3:
        add(5, "engaged (3+ messages)")
    s = min(s, 100)

    if intent in ("complaint", "support"):
        return s, "support", reasons + ["complaint/support -> routed to a manager, not sales"]
    return s, "hot" if s >= HOT else "warm" if s >= WARM else "cold", reasons
