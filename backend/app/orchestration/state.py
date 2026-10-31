from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    workflow_id: str
    document_id: str
    organization_id: str
    user_id: str
    actor: str
    extraction: dict[str, Any]
    validation: dict[str, Any]
    plan: dict[str, Any]
    decision: dict[str, Any]  # {"decision": approve|reject|request_correction, reviewer, comment, corrections}
    execution: list[dict[str, Any]]
    outcome: str  # completed|rejected|needs_correction|failed|awaiting_approval
    error: str
