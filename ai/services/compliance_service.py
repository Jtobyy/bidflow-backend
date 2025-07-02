def check_compliance(text: str) -> dict:
    """
    Checks for dummy compliance by looking for required keywords.
    """
    required_keywords = ['TIN', 'Tax', 'Registration', 'BOQ']
    found = all(keyword.lower() in text.lower() for keyword in required_keywords)

    return {
        "compliant": found,
        "missing_items": [kw for kw in required_keywords if kw.lower() not in text.lower()]
    }
