"""
Example: SQLAlchemy Model with Proper Patterns

This example demonstrates best practices for database model design:
- Proper column types
- Foreign key relationships
- Soft deletes
- Branch isolation
- Timestamps
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()


class Branch(Base):
    """Branch entity - required for multi-tenancy."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    gym_business_id: Mapped[int] = mapped_column(
        ForeignKey("gym_businesses.id"), nullable=False
    )

    # Relationships
    members = relationship("Member", back_populates="branch")


class Member(Base):
    """
    Example member model following all best practices.

    Key patterns:
    - branch_id for multi-tenancy isolation
    - is_deleted for soft deletes
    - created_at/updated_at timestamps
    - Proper indexes on frequently queried columns
    """

    __tablename__ = "members"

    # Primary Key (surrogate)
    id: Mapped[int] = mapped_column(primary_key=True)

    # Branch isolation (REQUIRED for all operational tables)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id"),
        nullable=False,
        index=True,  # Always index foreign keys
    )

    # Business fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,  # Unique constraint for business rule
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Status with constrained values
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Financial - use Numeric for money (NOT Float!)
    balance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete flag
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    branch = relationship("Branch", back_populates="members")
    contracts = relationship("Contract", back_populates="member")

    # Composite indexes for common queries
    __table_args__ = (
        # Index for finding active members by branch
        Index("ix_members_branch_status", "branch_id", "status"),
        # Index for searching by name within branch
        Index("ix_members_branch_name", "branch_id", "last_name", "first_name"),
    )

    def __repr__(self):
        return f"<Member(id={self.id}, email={self.email})>"


class Contract(Base):
    """
    Example contract model with proper relationships.

    Demonstrates:
    - Many-to-one relationship to Member
    - Date handling
    - Status lifecycle
    """

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Branch isolation
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )

    # Foreign key to member
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id"), nullable=False, index=True
    )

    # Contract details
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Financial - stored in cents
    monthly_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="contracts")

    __table_args__ = (
        # Find active contracts by member
        Index("ix_contracts_member_status", "member_id", "status"),
        # Find contracts by date range
        Index("ix_contracts_dates", "start_date", "end_date"),
    )
