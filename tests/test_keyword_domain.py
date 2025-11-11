from app.services.keyword_domain import classify_domain


def test_classify_domain_prefers_keyword_match():
    text = "Soft robotics and control theory"
    assert classify_domain(text, ["cs.RO", "cs.AI"]) == "cs.RO"


def test_classify_domain_falls_back_to_first_candidate():
    assert classify_domain("", ["cs.AI", "cs.LG"]) == "cs.AI"
