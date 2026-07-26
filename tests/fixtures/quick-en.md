---
handoff_protocol: "session-handoff-card/v1.3"
handoff_id: "HOF-QUICK-EN"
created_at: "2026-07-26T12:00:00Z"
updated_at: "2026-07-26T12:00:00Z"
status: "HANDOFF_READY"
history_coverage: "FULL"
language: "en"
profile: "QUICK"
delivery_mode: "text"
evidence_mode: "conversation"
project_root: ''
card_path: ''
source_session: ''
target_models: "any"
---

# Session Continuation Card (Quick)

## 1. What we are doing now

- Current goal: Prepare a two-option family trip shortlist.
- Current state: Constraints are confirmed; no booking has occurred.
- Do not do: Do not book, call vendors, pay deposits, or share identity details.

## 2. Context that must survive

- Completed: The budget, accessibility, diet, hotel, and departure constraints were collected.
- Key constraints: Total local budget is 5,500 CNY; one vegetarian traveler; avoid long stairs and departures before 09:00.
- Open issues and gaps: Destination has not been selected; this does not block the one next action.

## 3. Next step

- Next action: Produce two destination options with rough category budgets and accessibility notes.
- Expected output: A concise comparison for user review.
- Stop condition: Stop before checkout, vendor contact, or requests for identity documents.
- Later candidates (not authorized): None.

## 4. How the new session should continue

- History coverage: All provided and currently visible conversation was processed.
- Minimum attachments: This card only.
- First prompt in the new session: Read this complete card, then restate the goal, prohibited actions, one next action, and stop condition. Do not rewrite that action unless the card explicitly marks a blocker.
- Fallback when access is unavailable: Continue from the card; stop only if the card is BLOCKED or a gap is explicitly blocking.
