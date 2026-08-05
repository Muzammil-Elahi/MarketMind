"""Tests for src/recommendation/explain.py (REC-03/D-06 deterministic
template-based explanation).

Pure, zero-I/O plain-dict fixtures -- exact-string assertions since
fidelity to the UI-SPEC Copywriting Contract is the acceptance bar.
"""

from src.recommendation.explain import FACTOR_LABELS, explain


def test_explain_one_factor_template_for_clear_single_winner():
    sub_scores = {
        "profile_fit": 0.5,
        "momentum": 0.9,
        "volatility": 0.5,
        "quality": 0.5,
        "similarity": 0.5,
    }

    result = explain(sub_scores, "Moderate")

    assert result == "Strong momentum matches your Moderate risk profile."


def test_explain_two_factor_template_for_exact_two_way_tie_in_sub_score_order():
    sub_scores = {
        "profile_fit": 0.5,
        "momentum": 0.8,
        "volatility": 0.8,
        "quality": 0.3,
        "similarity": 0.2,
    }

    result = explain(sub_scores, "Aggressive")

    assert (
        result
        == "Strong momentum and low volatility match your Aggressive risk profile."
    )


def test_explain_falls_back_to_one_factor_template_on_five_way_tie():
    sub_scores = {
        "profile_fit": 0.7,
        "momentum": 0.7,
        "volatility": 0.7,
        "quality": 0.7,
        "similarity": 0.7,
    }

    result = explain(sub_scores, "Conservative")

    assert (
        result
        == "Strong alignment with your preferred sectors matches your Conservative risk profile."
    )


def test_explain_is_deterministic_across_repeated_calls():
    sub_scores = {
        "profile_fit": 0.5,
        "momentum": 0.9,
        "volatility": 0.5,
        "quality": 0.5,
        "similarity": 0.5,
    }

    first = explain(sub_scores, "Moderate")
    second = explain(sub_scores, "Moderate")

    assert first == second


def test_no_directive_financial_advice_language_in_labels_or_templates():
    import src.recommendation.explain as explain_module

    forbidden = ("buy", "sell", "you should")
    haystacks = list(FACTOR_LABELS.values()) + [
        explain_module.ONE_FACTOR_TEMPLATE,
        explain_module.TWO_FACTOR_TEMPLATE,
    ]

    for text in haystacks:
        lowered = text.lower()
        for phrase in forbidden:
            assert phrase not in lowered
