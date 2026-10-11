from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database import Base

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), nullable=False, unique=True)
    password = Column(String(255), nullable=False)

class UserAdmin(Base):
    __tablename__ = "user_admin"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), nullable=False, unique=True)
    password = Column(String(255), nullable=False)

class ContactUs(Base):
    __tablename__ = "contact_us"
    sno = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(500), nullable=False)
    text = Column(String(900), nullable=False)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
