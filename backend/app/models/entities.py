import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(80), default="education")
    city: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(30), default="operator")  # admin|reviewer|operator|viewer
    department: Mapped[str] = mapped_column(String(120), default="Administration")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    organization: Mapped[Organization] = relationship()


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    detected_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded", index=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="document", order_by="Workflow.created_at")


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    started_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # queued|running|awaiting_approval|completed|rejected|needs_correction|failed
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    current_stage: Mapped[str] = mapped_column(String(40), default="uploaded")
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_reasons: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Persistent LangGraph checkpoint for the human-approval pause.
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    execution_result: Mapped[dict] = mapped_column(JSON, default=dict)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[Document] = relationship(back_populates="workflows")
    executions: Mapped[list["AgentExecution"]] = relationship(order_by="AgentExecution.started_at", cascade="all")
    fields: Mapped[list["ExtractedField"]] = relationship(cascade="all")
    validations: Mapped[list["ValidationResult"]] = relationship(cascade="all")
    action_plans: Mapped[list["ActionPlan"]] = relationship(cascade="all")
    approvals: Mapped[list["Approval"]] = relationship(cascade="all", order_by="Approval.created_at")


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    agent: Mapped[str] = mapped_column(String(40))  # extractor|validator|action_planner|human_approval|executor|audit
    status: Mapped[str] = mapped_column(String(30), default="running")  # running|completed|failed|waiting
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine: Mapped[str] = mapped_column(String(60), default="deterministic")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(120))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok|uncertain|missing|corrected
    note: Mapped[str] = mapped_column(Text, default="")
    corrected_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (Index("ix_fields_name_value", "name", "value"),)


class ValidationRule(Base):
    __tablename__ = "validation_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    code: Mapped[str] = mapped_column(String(60))
    document_type: Mapped[str] = mapped_column(String(50), index=True)  # or "*"
    rule_type: Mapped[str] = mapped_column(String(30))  # required|regex|range|date|not_future|date_order|duplicate|confidence
    field: Mapped[str | None] = mapped_column(String(80), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str] = mapped_column(String(10), default="failed")  # failed|warning
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_rule_code"),)


class ValidationResult(Base):
    __tablename__ = "validation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    rule_code: Mapped[str] = mapped_column(String(60))
    rule_type: Mapped[str] = mapped_column(String(30))
    field: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(10))  # passed|warning|failed
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class ActionPlan(Base):
    __tablename__ = "action_plans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    step: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20))  # low|normal|high|urgent
    impact: Mapped[str] = mapped_column(String(10))  # low|medium|high
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    reasoning: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned|executed|skipped|blocked


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending|approved|rejected|correction_requested
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrections: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    """Append-only. Rows are never updated or deleted (enforced in app.services.audit_service)."""

    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sequence: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor: Mapped[str] = mapped_column(String(200))
    agent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class ContractDeployment(Base):
    __tablename__ = "contract_deployments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    network: Mapped[str] = mapped_column(String(20))
    chain_id: Mapped[int] = mapped_column(Integer)
    address: Mapped[str] = mapped_column(String(42))
    deploy_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    deployer: Mapped[str | None] = mapped_column(String(42), nullable=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified_on_chain: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("chain_id", "address", name="uq_deployment"),)


class BlockchainAnchor(Base):
    """Links one off-chain audit event to its on-chain proof on MST Blockchain."""

    __tablename__ = "blockchain_anchors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    audit_event_id: Mapped[str] = mapped_column(ForeignKey("audit_events.id"), index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    event_hash: Mapped[str] = mapped_column(String(66))  # 0x-prefixed bytes32 (= audit event hash)
    workflow_id_hash: Mapped[str] = mapped_column(String(66))
    event_type: Mapped[str] = mapped_column(String(40))
    network: Mapped[str] = mapped_column(String(20))
    chain_id: Mapped[int] = mapped_column(Integer)
    contract_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    # queued|submitted|confirmed|failed|not_configured
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    submitted_via: Mapped[str | None] = mapped_column(String(20), nullable=True)  # relayer|wallet
    submitter_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gas_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    onchain_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("chain_id", "event_hash", name="uq_anchor_event_per_chain"),)
