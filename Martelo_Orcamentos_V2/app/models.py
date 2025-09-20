from sqlalchemy import Column, Integer, String
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # hash da password
    role = Column(String(20), default="user", nullable=False)
