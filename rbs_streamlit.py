# app.py
import json
from typing import List, Dict, Any, Tuple
import operator
import streamlit as st

# ----------------------------
# 1) Minimal rule engine
# ----------------------------
# A rule shape:
# {
#   "name": "High income & good credit",
#   "priority": 90,               # higher wins if multiple actions conflict
#   "conditions": [               # all must be true (AND)
#       ["income", ">=", 6000],
#       ["credit_score", ">=", 700],
#       ["debt_to_income", "<", 0.4]
#   ],
#   "action": {"decision": "APPROVE", "reason": "Strong income & credit"}
# }

OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "name": "Excellent profile",
        "priority": 100,
        "conditions": [
            ["income", ">=", 8000],
            ["credit_score", ">=", 750],
            ["debt_to_income", "<", 0.35],
            ["employment_years", ">=", 2],
        ],
        "action": {"decision": "APPROVE", "reason": "Excellent income/credit/DTI/employment"},
    },
    {
        "name": "Good profile",
        "priority": 80,
        "conditions": [
            ["income", ">=", 6000],
            ["credit_score", ">=", 700],
            ["debt_to_income", "<", 0.45],
        ],
        "action": {"decision": "APPROVE", "reason": "Good income & credit; DTI acceptable"},
    },
    {
        "name": "Borderline — manual review",
        "priority": 60,
        "conditions": [
            ["income", ">=", 4000],
            ["credit_score", ">=", 650],
            ["debt_to_income", "<", 0.55],
        ],
        "action": {"decision": "REVIEW", "reason": "Borderline metrics; needs manual review"},
    },
    {
        "name": "Too much debt",
        "priority": 70,
        "conditions": [
            ["debt_to_income", ">=", 0.6],
        ],
        "action": {"decision": "REJECT", "reason": "High debt-to-income ratio"},
    },
    {
        "name": "Low credit or income",
        "priority": 50,
        "conditions": [
            ["credit_score", "<", 600],
        ],
        "action": {"decision": "REJECT", "reason": "Credit score below minimum threshold"},
    },
]

def evaluate_condition(facts: Dict[str, Any], cond: List[Any]) -> bool:
    """Evaluate a single condition: [field, op, value]."""
    if len(cond) != 3:
        return False
    field, op, value = cond
    if field not in facts or op not in OPS:
        return False
    try:
        return OPS[op](facts[field], value)
    except Exception:
        return False

def rule_matches(facts: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """All conditions must be true (AND)."""
    return all(evaluate_condition(facts, c) for c in rule.get("conditions", []))

def run_rules(facts: Dict[str, Any], rules: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (best_action, fired_rules)
    - best_action: chosen by highest priority among fired rules (ties keep the first encountered)
    - fired_rules: list of rule dicts that matched
    """
    fired = [r for r in rules if rule_matches(facts, r)]
    if not fired:
        return ({"decision": "REVIEW", "reason": "No rule matched"}, [])

    fired_sorted = sorted(fired, key=lambda r: r.get("priority", 0), reverse=True)
    best = fired_sorted[0].get("action", {"decision": "REVIEW", "reason": "No action"})
    return best, fired_sorted

# ----------------------------
# 2) Streamlit UI
# ----------------------------
st.set_page_config(page_title="Rule-Based System (Streamlit)", page_icon="", layout="wide")
st.title("Simple Rule-Based System (Loan Eligibility Demo)")
st.caption("Enter applicant data, edit rules (optional), and evaluate. Designed to be a small, deployable example.")

with st.sidebar:
    st.header("Applicant Facts")
    income = st.number_input("Monthly income (MYR)", min_value=0, step=100, value=5000)
    credit_score = st.number_input("Credit score", min_value=0, max_value=900, step=10, value=680)
    debt_to_income = st.number_input("Debt-to-income ratio (0–1)", min_value=0.0, max_value=5.0, step=0.01, value=0.45)
    employment_years = st.number_input("Employment years", min_value=0, step=1, value=2)
    age = st.number_input("Age", min_value=18, max_value=100, step=1, value=30)

    st.divider()
    st.header("Rules (JSON)")
    st.caption("You can keep the defaults or paste your own JSON array of rules.")    
    default_json = json.dumps(DEFAULT_RULES, indent=2)
    rules_text = st.text_area("Edit rules here", value=default_json, height=300)

    run = st.button("Evaluate", type="primary")

facts = {
    "income": float(income),
    "credit_score": int(credit_score),
    "debt_to_income": float(debt_to_income),
    "employment_years": int(employment_years),
    "age": int(age),
}

st.subheader("Applicant Facts")
st.json(facts)

# Parse rules (fall back to defaults if invalid)
try:
    rules = json.loads(rules_text)
    assert isinstance(rules, list), "Rules must be a JSON array"
except Exception as e:
    st.error(f"Invalid rules JSON. Using defaults. Details: {e}")
    rules = DEFAULT_RULES

st.subheader("Active Rules")
with st.expander("Show rules", expanded=False):
    st.code(json.dumps(rules, indent=2), language="json")

st.divider()

if run:
    action, fired = run_rules(facts, rules)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Decision")
        badge = action.get("decision", "REVIEW")
        reason = action.get("reason", "-")
        if badge == "APPROVE":
            st.success(f"APPROVE — {reason}")
        elif badge == "REJECT":
            st.error(f"REJECT — {reason}")
        else:
            st.warning(f"REVIEW — {reason}")

    with col2:
        st.subheader("Matched Rules (by priority)")
        if not fired:
            st.info("No rules matched.")
        else:
            for i, r in enumerate(fired, start=1):
                st.write(f"**{i}. {r.get('name','(unnamed)')}** | priority={r.get('priority',0)}")
                st.caption(f"Action: {r.get('action',{})}")
                with st.expander("Conditions"):
                    for cond in r.get("conditions", []):
                        st.code(str(cond))

else:
    st.info("Set input values and click **Evaluate**.")
