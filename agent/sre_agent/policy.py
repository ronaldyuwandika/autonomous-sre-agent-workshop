"""Remediation policy: which proposals may run without a human.

AUTONOMY=approve (default)  every proposal waits for a human (Slack button or CLI).
AUTONOMY=auto               proposals whose action is listed in AUTO_ACTIONS run at once;
                            everything else still waits for a human.
AUTO_ACTIONS                comma list of actions allowed to run alone (default: "scale").

Whatever the policy says, the write tools keep their own guardrails (allow-list,
increase-only, hard caps), and every outcome is reported to Slack and email.
"""
import os

ACTIONS = {"rollback", "scale"}


def autonomy() -> str:
    mode = os.environ.get("AUTONOMY", "approve").strip().lower()
    return mode if mode in {"approve", "auto"} else "approve"


def auto_actions() -> set[str]:
    raw = os.environ.get("AUTO_ACTIONS", "scale")
    return {a.strip().lower() for a in raw.split(",") if a.strip().lower() in ACTIONS}


def decide(proposal: dict | None) -> str:
    """'auto', 'approve', or 'none' (no proposal to act on)."""
    if not proposal or proposal.get("action") not in ACTIONS:
        return "none"
    if autonomy() == "auto" and proposal["action"] in auto_actions():
        return "auto"
    return "approve"
