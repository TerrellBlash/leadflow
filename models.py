from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from database import Base 

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=False)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

