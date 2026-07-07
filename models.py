from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from database import Base 

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=False)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    status = Column(String, nullable=False, default="running")
    current_step = Column(String, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

