# 10 · Human Approval

## When approval is required

| Trigger | Reason shown to reviewer |
|---|---|
| Invoice passes validation | "Payment release is a high-impact action" |
| Admission form passes validation | "Admission decision requires committee approval" |
| Duplicate detected | "Duplicate record detected — normal execution blocked" |
| Required field missing / invalid | "Validation failed — correction required" |
| Required field unreadable | "Unreadable required values — human verification needed" |
| Any field below confidence threshold | "Low-confidence fields need human verification: …" |
| Document type unknown | "Unclassified document" |
| Complaint with high urgency | "Urgent complaint — supervisor confirms escalation" |

## Decisions

- **Approve** — executes the plan (simulated). If the reviewer entered corrected values, they are saved as `corrected` fields and the validator + planner run again first.
- **Reject** — closes the workflow; no action executes. Comment required.
- **Request correction** — closes as `needs_correction`. Comment required.

Each decision stores reviewer id/name, timestamp, comment and corrected field names, writes an `APPROVAL_DECISION` audit event, and that event is queued for MST anchoring. A decision cannot be made twice (409), and only `reviewer`/`admin` roles can decide (403 otherwise).

## Simulated execution

Executed actions return `SIMULATED: '<title>' handed to <department>. No external system was called.` This is deliberate: the prototype never claims to have paid a vendor or emailed a student.
