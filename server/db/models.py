# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from server.db.base import Base, UTCDateTime

class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    disability_severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(Enum("active", "inactive", "deleted", name="user_status"), default="active", nullable=False)

    devices: Mapped[List["UserDevice"]] = relationship("UserDevice", back_populates="user")

class UserDevice(Base):
    __tablename__ = "user_devices"

    device_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False)
    device_uuid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(Enum("ios", "android", "unknown", name="device_platform"), default="unknown", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["AppUser"] = relationship("AppUser", back_populates="devices")

class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    admin_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("super_admin", "operator", "viewer", name="admin_role"), default="operator", nullable=False)
    status: Mapped[str] = mapped_column(Enum("active", "inactive", "locked", "deleted", name="admin_status"), default="active", nullable=False)

class AdminLoginAudit(Base):
    __tablename__ = "admin_login_audits"

    audit_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
