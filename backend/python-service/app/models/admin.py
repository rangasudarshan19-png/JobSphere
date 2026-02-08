"""
Admin-related models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.utils.database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)  # 'user_deleted', 'user_suspended', 'setting_changed'
    target_type = Column(String(50))  # 'user', 'application', 'setting'
    target_id = Column(Integer)
    old_value = Column(Text)  # JSON string
    new_value = Column(Text)  # JSON string
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    admin = relationship("User", foreign_keys=[admin_id])


class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(255), unique=True, nullable=False, index=True)
    setting_value = Column(Text)  # JSON string
    category = Column(String(50))  # 'general', 'security', 'email', 'features'
    updated_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    updated_by_user = relationship("User", foreign_keys=[updated_by])


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)

    # Relationship
    creator = relationship("User", foreign_keys=[created_by])


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])
