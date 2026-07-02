"""Investor risk-assessment questionnaire (Step 3 input, see README Approach).

Collects the answers the recommendation stage will need later: risk
tolerance, horizon, sector preference and how many positions the user wants.
Wiring the answers into the modeling scripts is a separate, later step --
this module only defines the questions and renders the form.
"""

import streamlit as st

RISK_QUESTIONS = [
    {
        "key": "experience",
        "label": "What is your prior experience investing in individual stocks?",
        "options": ["Beginner", "Some experience", "Experienced"],
    },
    {
        "key": "horizon",
        "label": "How long do you plan to hold these positions?",
        "options": ["Less than 1 week", "1-4 weeks", "1-12 months", "1+ year"],
    },
    {
        "key": "loss_tolerance",
        "label": "What is the largest drop in your capital (%) you would accept before selling everything?",
        "options": ["5%", "10%", "20%", "30% or more"],
    },
    {
        "key": "drawdown_reaction",
        "label": "If your portfolio dropped 20% in a month, what would you do?",
        "options": ["Sell everything", "Sell part of it", "Hold", "Buy more"],
    },
    {
        "key": "capital",
        "label": "How much capital do you plan to allocate initially (USD)?",
        "options": ["Under 1,000", "1,000 - 5,000", "5,000 - 20,000", "Over 20,000"],
    },
    {
        "key": "sectors_avoid",
        "label": "Which sectors would you like to avoid?",
        "type": "multiselect",
        "options": [
            "Information Technology",
            "Financials",
            "Health Care",
            "Energy",
            "Consumer Discretionary",
            "Communication Services",
            "Industrials",
        ],
    },
    {
        "key": "sectors_prioritize",
        "label": "Which sectors would you like to prioritize?",
        "type": "multiselect",
        "options": [
            "Information Technology",
            "Financials",
            "Health Care",
            "Energy",
            "Consumer Discretionary",
            "Communication Services",
            "Industrials",
        ],
    },
    {
        "key": "position_count",
        "label": "How many different positions do you want open at the same time?",
        "options": ["Few (1-3)", "Moderate (4-7)", "Fully diversified (8-10)"],
    },
    {
        "key": "goal",
        "label": "Which trade-off best matches what you want from this portfolio?",
        "options": [
            "Minimize losses, even if it means missing some gains",
            "Maximize potential returns, even if it means larger swings",
            "Balance steady, moderate gains against moderate risk",
        ],
    },
]


def render_questionnaire():
    """Render the questionnaire form and return the answers dict once submitted, else None."""
    with st.form("risk_assessment_form"):
        answers = {}
        for i, q in enumerate(RISK_QUESTIONS, start=1):
            if q.get("type") == "multiselect":
                answers[q["key"]] = st.multiselect(f"{i}. {q['label']}", q["options"], key=f"risk_{q['key']}")
            else:
                answers[q["key"]] = st.radio(f"{i}. {q['label']}", q["options"], key=f"risk_{q['key']}")
        submitted = st.form_submit_button("Submit")

    if submitted:
        st.session_state["risk_answers"] = answers
        return answers

    return st.session_state.get("risk_answers")
