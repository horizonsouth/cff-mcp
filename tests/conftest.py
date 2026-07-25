import pytest


@pytest.fixture
def full_answers():
    return {
        "mission": {
            "statement": "Turn raw weekly support tickets into a one-page summary a manager can read in five minutes and act on.",
            "not_doing": "Replying to customers.",
        },
        "audience": {
            "who": "A shift manager with no data background.",
            "knows": "Knows the ticket categories cold, has never written a spreadsheet formula.",
            "next_action": "Uses it to staff Monday.",
        },
        "constraints": {
            "hard_limits": "Never invent a ticket number. Cannot read the PII columns. Must fit one printed page.",
            "fixed": "Plain markdown, no tables.",
            "tone": "Direct, no hedging.",
        },
        "context_stack": {
            "sources": "ticket_export.csv from Zendesk; category_definitions.md owned by ops; last three summaries in /archive.",
            "precedence": "category_definitions.md wins.",
        },
        "pattern_signal": {
            "positive": "The Oct 14 summary in /archive: three bullets, each naming a category, a count, and a recommended action.",
            "negative": "The Oct 21 one, which described trends without recommending anything.",
        },
        "success_criteria": {
            "checks": "Fits one page. Every claim traces to a ticket ID. Ends with exactly three recommended actions.",
            "fail_conditions": "Any category mentioned without a count.",
        },
        "medium": {
            "format": "Markdown file under 400 words.",
            "destination": "Committed to /reports, pasted into a Monday Slack post.",
        },
    }
