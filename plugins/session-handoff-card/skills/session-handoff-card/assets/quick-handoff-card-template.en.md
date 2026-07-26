---
handoff_protocol: "session-handoff-card/v1.3"
handoff_id: "{{HANDOFF_ID}}"
created_at: "{{CREATED_AT}}"
updated_at: "{{UPDATED_AT}}"
status: "DRAFT"
history_coverage: "UNKNOWN"
language: "en"
profile: "QUICK"
delivery_mode: "{{DELIVERY_MODE}}"
evidence_mode: "{{EVIDENCE_MODE}}"
project_root: '{{PROJECT_ROOT}}'
card_path: '{{CARD_PATH}}'
source_session: '{{SOURCE_SESSION}}'
target_models: "any"
---

# Session Continuation Card (Quick)

## 1. What we are doing now

- Current goal: TBD-REQUIRED
- Current state: TBD-REQUIRED
- Do not do: TBD-REQUIRED; write "None" when empty.

## 2. Context that must survive

- Completed: TBD-REQUIRED
- Key constraints: TBD-REQUIRED
- Open issues and gaps: TBD-REQUIRED; mark each as "blocks" or "does not block the one next action". When empty, write "None; does not block the one next action."

## 3. Next step

- Next action: TBD-REQUIRED
- Expected output: TBD-REQUIRED
- Stop condition: TBD-REQUIRED
- Later candidates (not authorized): None; otherwise separate 1–3 items with semicolons.

## 4. How the new session should continue

- History coverage: TBD-REQUIRED
- Minimum attachments: This card only unless a listed gap requires more.
- First prompt in the new session: Read this complete card first. Restate the current goal, prohibited actions, one next action, and stop condition. Mark missing facts unknown. Do not rewrite the one next action unless the card explicitly marks a blocker, and do not execute later candidates without approval.
- Fallback when access is unavailable: Continue with the one next action. Stop and ask only when the card is BLOCKED or a gap is explicitly marked as blocking.
