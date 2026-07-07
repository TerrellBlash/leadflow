from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Lead, WorkflowRun


def log_lead(lead: Lead, db: Session) -> None:
    print(f"[log_lead] Lead {lead.id}: {lead.name} from {lead.company}")


def tag_priority(lead: Lead, db: Session) -> None:
    if "ceo" in lead.name.lower() or "founder" in lead.name.lower():
        lead.status = "hot"
    else: 
        lead.status = "warm"
    db.commit()


WORKFLOW_STEPS = [
    ("log_lead", log_lead),
    ("tag_priority", tag_priority),
]


def run_workflow(lead: Lead, db: Session) -> WorkflowRun:
    run = WorkflowRun(lead_id=lead.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        for step_name, step_function in WORKFLOW_STEPS:
            run.current_step = step_name
            db.commit()
            step_function(lead, db)

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    return run