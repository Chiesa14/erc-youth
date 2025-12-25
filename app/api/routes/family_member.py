from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload

from app.controllers import family_member as crud_member
from app.controllers.family_member import verify_temp_password, create_user_from_member
from app.db.session import get_db
from app.core.security import get_current_active_user, get_password_hash
from app.core.permissions import require_parent
from app.models import Family, Activity
from app.models.family_member import FamilyMemberInvitation, FamilyMember
from app.models.user import User
from app.schemas.family_activity import ActivityCategoryEnum
from app.schemas.family_member import (
    FamilyMemberCreate,
    FamilyMemberOut,
    FamilyMemberUpdate,
    GrantAccessRequest,
    DelegatedAccessOut, MemberActivationResponse, MemberActivationRequest, AccessPermissionEnum, FamilyStats,
    AgeDistribution, MonthlyTrend
)
from app.services.email_service import EmailService
from app.utils.timestamps import (
    parse_timestamp_filters,
    apply_timestamp_filters,
    apply_timestamp_sorting
)

router = APIRouter(tags=["Family Members"])


# ========================
# 🚪 Access Management First (Specific routes go before dynamic ones!)
# ========================

@router.post("/access/grant", status_code=status.HTTP_204_NO_CONTENT)
def grant_access(
    request: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.grant_permissions_to_member(db, current_user.family_id, request, current_user)


@router.get("/access", response_model=list[DelegatedAccessOut])
def list_access_grants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    return crud_member.get_members_with_permissions(db, current_user.family_id)


@router.post("/access/update", status_code=status.HTTP_204_NO_CONTENT)
def update_access(
    request: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.update_member_permissions(db, current_user.family_id, request, current_user)


@router.delete("/access/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.revoke_member_permissions(db, current_user.family_id, member_id)


# ========================
# 👨‍👩‍👧 Family Member CRUD
# ========================

@router.post("/", response_model=FamilyMemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    member: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any family.")

    member_data = member.model_copy(update={"family_id": current_user.family_id})
    db_member = crud_member.create_family_member(db, member_data)
    return FamilyMemberOut.model_validate(db_member)


@router.get("/", response_model=list[FamilyMemberOut])
def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    created_after: Optional[str] = Query(None, description="Filter members created after this timestamp (ISO 8601)"),
    created_before: Optional[str] = Query(None, description="Filter members created before this timestamp (ISO 8601)"),
    updated_after: Optional[str] = Query(None, description="Filter members updated after this timestamp (ISO 8601)"),
    updated_before: Optional[str] = Query(None, description="Filter members updated before this timestamp (ISO 8601)"),
    sort_by: Optional[str] = Query(None, description="Sort by timestamp field", enum=["created_at", "updated_at"]),
    sort_order: Optional[str] = Query("desc", description="Sort order", enum=["asc", "desc"]),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any family.")

    # If no timestamp filters are provided, use the original function
    if not any([created_after, created_before, updated_after, updated_before, sort_by]):
        return crud_member.get_family_members_by_family_id(db, current_user.family_id)
    
    # Parse timestamp filters
    filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
    
    # Build query with filters and sorting
    query = db.query(FamilyMember).filter(FamilyMember.family_id == current_user.family_id)
    query = apply_timestamp_filters(query, FamilyMember, filters)
    query = apply_timestamp_sorting(query, FamilyMember, sort_by, sort_order)
    
    return query.all()


@router.get("/{member_id}", response_model=FamilyMemberOut)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    return member


@router.put("/{member_id}", response_model=FamilyMemberOut)
def update_member(
    member_id: int,
    updates: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    return crud_member.update_family_member(db, member_id, updates)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    if not crud_member.delete_family_member(db, member_id):
        raise HTTPException(status_code=500, detail="Failed to delete member.")


@router.post("/activate", response_model=MemberActivationResponse)
def activate_member_account(
        request: MemberActivationRequest,
        db: Session = Depends(get_db),
):
    # Verify temporary password
    if not verify_temp_password(db, request.member_id, request.temp_password):
        raise HTTPException(status_code=400, detail="Invalid temporary password or invitation already used.")

    # Create user account
    user = create_user_from_member(db, request.member_id, request.new_password)

    return MemberActivationResponse(
        message="Account activated successfully",
        user_id=user.id,
    )


@router.post("/{member_id}/resend-invitation", status_code=status.HTTP_204_NO_CONTENT)
def resend_invitation(
        member_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    """Resend invitation email to a family member"""
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    if not member.email:
        raise HTTPException(status_code=400, detail="Family member has no email address.")

    # Check if already activated
    if member.invitation and member.invitation.is_activated:
        raise HTTPException(status_code=400, detail="Member has already activated their account.")

    # Generate new temporary password and send email
    email_service = EmailService()
    temp_password = email_service.generate_temporary_password()

    # Update or create invitation
    if member.invitation:
        member.invitation.temp_password = get_password_hash(temp_password)
    else:
        invitation = FamilyMemberInvitation(
            member_id=member.id,
            temp_password=get_password_hash(temp_password)
        )
        db.add(invitation)

    db.commit()

    # Send email
    family = db.query(Family).filter(Family.id == member.family_id).first()
    email_sent = email_service.send_invitation_email(
        to_email=member.email,
        member_name=member.name,
        temp_password=temp_password,
        family_name=family.name if family else "Your Family",
        member_id=member.id,
    )

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send invitation email.")


@router.get("/access/permissions", response_model=List[str])
def list_available_permissions():
    return [perm.value for perm in AccessPermissionEnum]

@router.get("/access/{member_id}", response_model=DelegatedAccessOut)
def get_member_permissions(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    member = db.query(FamilyMember).options(joinedload(FamilyMember.permissions)) \
        .filter(FamilyMember.id == member_id, FamilyMember.family_id == current_user.family_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found.")

    return DelegatedAccessOut(
        member_id=member.id,
        name=member.name,
        permissions=[perm.permission for perm in member.permissions]
    )


@router.get("/{family_id}/stats", response_model=FamilyStats, tags=["Stats"])
def get_family_stats(family_id: int, db: Session = Depends(get_db)):

    if not db.query(Family).filter(Family.id == family_id).first():
        raise HTTPException(status_code=404, detail="Family not found")

    today = date.today()
    current_year = today.year


    total_members_count = db.query(User).filter(User.family_id == family_id).count()

    first_day_of_current_month = today.replace(day=1)
    monthly_members_count = db.query(User).filter(
        User.family_id == family_id,
        User.created_at >= first_day_of_current_month
    ).count()

    bcc_graduate_count = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.year_of_graduation != None,
        FamilyMember.year_of_graduation < current_year
    ).count()

    active_events_count = db.query(Activity).filter(
        Activity.family_id == family_id,
        Activity.date >= today
    ).count()

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    weekly_events_count = db.query(Activity).filter(
        Activity.family_id == family_id,
        Activity.date.between(start_of_week, end_of_week)
    ).count()

    thirty_days_ago = today - timedelta(days=30)
    engagement_count = db.query(Activity).filter(
        Activity.family_id == family_id,
        Activity.date >= thirty_days_ago
    ).count()

    # --- New: Age Distribution Calculation ---
    members_with_dob = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.date_of_birth != None
    ).all()

    total_with_dob = len(members_with_dob)
    age_counts = {"0-12": 0, "13-18": 0, "19-25": 0, "35+": 0}

    if total_with_dob > 0:
        for member in members_with_dob:
            age = today.year - member.date_of_birth.year - (
                        (today.month, today.day) < (member.date_of_birth.month, member.date_of_birth.day))
            if 0 <= age <= 12:
                age_counts["0-12"] += 1
            elif 13 <= age <= 18:
                age_counts["13-18"] += 1
            elif 19 <= age <= 25:
                age_counts["19-25"] += 1
            elif age >= 35:
                age_counts["35+"] += 1

    age_distribution_data = AgeDistribution(
        zero_to_twelve=round((age_counts["0-12"] / total_with_dob * 100), 2) if total_with_dob > 0 else 0,
        thirteen_to_eighteen=round((age_counts["13-18"] / total_with_dob * 100), 2) if total_with_dob > 0 else 0,
        nineteen_to_twenty_five=round((age_counts["19-25"] / total_with_dob * 100), 2) if total_with_dob > 0 else 0,
        thirty_five_plus=round((age_counts["35+"] / total_with_dob * 100), 2) if total_with_dob > 0 else 0,
    )

    # --- New: Activity Trends Calculation (Last 6 Months) ---
    trends = {}
    for i in range(6):
        # Go back month by month
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        month_key = date(year, month, 1).strftime("%Y-%m")
        trends[month_key] = {"spiritual": 0, "social": 0}

    six_months_ago_date = date(today.year, today.month, 1) - timedelta(days=31 * 5)  # Approximate start date

    activities = db.query(Activity).filter(
        Activity.family_id == family_id,
        Activity.date >= six_months_ago_date.replace(day=1),
        Activity.category.in_([ActivityCategoryEnum.spiritual, ActivityCategoryEnum.social])
    ).all()

    for act in activities:
        month_key = act.date.strftime("%Y-%m")
        if month_key in trends:
            if act.category == ActivityCategoryEnum.spiritual:
                trends[month_key]["spiritual"] += 1
            elif act.category == ActivityCategoryEnum.social:
                trends[month_key]["social"] += 1

    activity_trends_data = {
        month: MonthlyTrend(**counts) for month, counts in trends.items()
    }

    return FamilyStats(
        total_members=total_members_count,
        monthly_members=monthly_members_count,
        bcc_graduate=bcc_graduate_count,
        active_events=active_events_count,
        weekly_events=weekly_events_count,
        engagement=engagement_count,
        age_distribution=age_distribution_data,
        activity_trends=activity_trends_data,
    )