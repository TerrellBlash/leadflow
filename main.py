from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from orchestrator import run_workflow
from database import Base, SessionLocal, engine
from models import Lead, WorkflowRun
from schemas import LeadIn, LeadOut, WorkflowRunOut

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadIn, db: Session = Depends(get_db)):
    lead = Lead(name=payload.name, email=payload.email, company=payload.company)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    run_workflow(lead, db)
    return lead


@app.get("/leads", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)):
    return db.query(Lead).all()

@app.get("/workflow_runs", response_model=list[WorkflowRunOut])
def list_workflow_runs(db: Session = Depends(get_db)):
    return db.query(WorkflowRun).all()


 
