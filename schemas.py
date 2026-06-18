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
    
  

