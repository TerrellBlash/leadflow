from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class LeadIn(BaseModel):
    name: str
    email: EmailStr
    company: str
    
    
class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    email: EmailStr
    company: str
    status: str
    created_at: datetime
    
class WorkflowRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    status: str
    current_step: str | None
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None

class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    lead_id: int
    content: str
    model: str
    prompt_version: str
    created_at: datetime
    
    