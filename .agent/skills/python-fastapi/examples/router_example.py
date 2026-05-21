"""
Example: FastAPI Router Patterns

This example demonstrates best practices for FastAPI development:
- Proper router structure
- Dependency injection
- Pydantic models
- Error handling
- Authentication
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.orm import Session

# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class MemberBase(BaseModel):
    """Base member schema with shared fields."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[\d\s-]{10,20}$")


class MemberCreate(MemberBase):
    """Schema for creating a new member."""

    branch_id: int

    @validator("email")
    def email_lowercase(cls, v):
        """Normalize email to lowercase."""
        return v.lower()


class MemberUpdate(BaseModel):
    """Schema for updating member - all fields optional."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^\+?[\d\s-]{10,20}$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended)$")


class MemberResponse(MemberBase):
    """Schema for member response."""

    id: int
    branch_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: List[MemberResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    """Standard error response format."""

    code: str
    message: str
    details: Optional[dict] = None


# =============================================================================
# DEPENDENCIES
# =============================================================================


def get_db():
    """Database session dependency."""
    from src.infrastructure.database.connection import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    # token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Authenticate and return current user."""
    # Implement JWT validation
    # user = validate_jwt_token(token, db)
    # if not user:
    #     raise HTTPException(status_code=401, detail="Invalid token")
    # return user
    pass


def get_current_active_user(current_user=Depends(get_current_user)):
    """Ensure user is active."""
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    # return current_user
    pass


def require_role(required_roles: List[str]):
    """Role-based access control dependency."""

    def check_role(current_user=Depends(get_current_active_user)):
        # if current_user.role not in required_roles:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Insufficient permissions"
        #     )
        # return current_user
        pass

    return check_role


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(
    prefix="/api/v1/members",
    tags=["members"],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
    },
)


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="List members",
    description="Get a paginated list of members with optional filtering.",
)
async def list_members(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    List members with pagination and filtering.

    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **status**: Filter by member status
    - **search**: Search in name and email
    """
    from src.application.services.member_service import MemberService

    service = MemberService(db)

    # Apply branch isolation (multi-tenancy)
    branch_id = current_user.branch_id

    members, total = service.list_members(
        branch_id=branch_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
    )

    return PaginatedResponse(
        items=members,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create member",
)
async def create_member(
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "staff"])),
):
    """
    Create a new member.

    Requires admin or staff role.
    """
    from src.application.services.member_service import MemberService
    from src.domain.exceptions import DuplicateEmailError

    service = MemberService(db)

    try:
        new_member = service.create_member(member.model_dump())
        return new_member
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DUPLICATE_EMAIL", "message": "Email already exists"},
        )


@router.get("/{member_id}", response_model=MemberResponse, summary="Get member by ID")
async def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get a member by their ID."""
    from src.application.services.member_service import MemberService

    service = MemberService(db)
    member = service.get_member_by_id(member_id)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Member not found"},
        )

    # Check branch access
    if member.branch_id != current_user.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Cannot access this member"},
        )

    return member


@router.patch("/{member_id}", response_model=MemberResponse, summary="Update member")
async def update_member(
    member_id: int,
    member: MemberUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "staff"])),
):
    """
    Update a member's information.

    Only provided fields will be updated.
    """
    from src.application.services.member_service import MemberService

    service = MemberService(db)

    # Only update non-None fields
    update_data = member.model_dump(exclude_unset=True)

    updated_member = service.update_member(member_id, update_data)

    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Member not found"},
        )

    return updated_member


@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete member (soft)",
)
async def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin"])),
):
    """
    Soft delete a member.

    Requires admin role.
    """
    from src.application.services.member_service import MemberService

    service = MemberService(db)
    success = service.soft_delete_member(member_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Member not found"},
        )

    # Return 204 No Content
    return None


# =============================================================================
# BACKGROUND TASKS EXAMPLE
# =============================================================================

from fastapi import BackgroundTasks


@router.post(
    "/{member_id}/send-welcome",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send welcome email",
)
async def send_welcome_email(
    member_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "staff"])),
):
    """
    Send welcome email to member (async).

    Returns immediately, email sent in background.
    """

    def send_email_task(email: str, name: str):
        # Email sending logic here
        pass

    from src.application.services.member_service import MemberService

    service = MemberService(db)
    member = service.get_member_by_id(member_id)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Queue background task
    background_tasks.add_task(
        send_email_task,
        email=member.email,
        name=f"{member.first_name} {member.last_name}",
    )

    return {"message": "Welcome email queued"}
