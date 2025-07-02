def score_bid(text: str) -> dict:
    """
    Dummy scoring based on text length and keyword presence.
    """
    base_score = len(text.split()) % 100
    bonus = 10 if 'experience' in text.lower() else 0

    return {
        "score": base_score + bonus,
        "ranked_score": min(base_score + bonus, 100)
    }
