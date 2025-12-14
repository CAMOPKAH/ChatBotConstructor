from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    script_code = Column(Text, nullable=False)
    is_start = Column(Boolean, default=False)
    ui_x = Column(Integer, default=0)
    ui_y = Column(Integer, default=0)

class BotUser(Base):
    __tablename__ = "bot_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) # External ID
    platform = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"

    user_id = Column(String, primary_key=True)
    platform = Column(String, primary_key=True)
    current_block_id = Column(Integer, ForeignKey("blocks.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    block = relationship("Block")

class UserParam(Base):
    __tablename__ = "user_params"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    platform = Column(String, index=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=True)

class Trace(Base):
    __tablename__ = "trace"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    platform = Column(String, index=True)
    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=True)
    direction = Column(String, nullable=False) # 'inbound' or 'outbound'
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    py_file = Column(String, nullable=False)
    status = Column(String, default="stop") # run, stop, error
