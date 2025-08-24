from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.prayer_chain import PrayerChain, Schedule
from app.models.family import Family
from app.models.user import User
from app.schemas.prayer_chain import (
    PrayerChainCreate,
    PrayerChainUpdate,
    PrayerChainResponse,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse
)
from app.schemas.user import RoleEnum
from app.utils.schedule_utils import check_db_schedule_collisions, validate_schedule_batch, normalize_time
from app.utils.logging_decorator import log_create, log_update, log_delete, log_view


def get_family_details(db: Session, family: Family) -> dict:
    """Get detailed family information including members and their details"""
    family_details = {
        "id": family.id,
        "category": family.category,
        "name": family.name,
        "pere": None,
        "mere": None,
        "members": []
    }

    # Get all family members (users in this family)
    family_members = db.query(User).filter(User.family_id == family.id).all()

    for member in family_members:
        member_info = {
            "id": member.id,
            "full_name": member.full_name,
            "email": member.email,
            "gender": member.gender,
            "phone": member.phone,
            "role": member.role,
            "other": member.other,
            "profile_pic": member.profile_pic,
            "biography": member.biography
        }

        if member.role and member.role == RoleEnum.pere:
            family_details["pere"] = member_info
        elif member.role and member.role == RoleEnum.mere:
            family_details["mere"] = member_info

        family_details["members"].append(member_info)

    return family_details


@log_view("prayer_chains", "Viewed all prayer chains")
def get_all_prayer_chains(db: Session) -> List[PrayerChainResponse]:
    """Get all prayer chains with their schedules and detailed family information"""
    prayer_chains = db.query(PrayerChain).all()

    result = []
    for prayer_chain in prayer_chains:
        family = db.query(Family).filter(Family.id == prayer_chain.family_id).first()

        if not family:
            continue

        family_details = get_family_details(db, family)

        schedules = [
            ScheduleResponse(
                id=schedule.id,
                day=schedule.day,
                start_time=normalize_time(schedule.start_time),
                end_time=normalize_time(schedule.end_time),
                prayer_chain_id=schedule.prayer_chain_id
            )
            for schedule in prayer_chain.schedules
        ]

        prayer_chain_data = PrayerChainResponse(
            id=prayer_chain.id,
            family_id=prayer_chain.family_id,
            family_name=family_details["name"],
            family_details=family_details,
            schedules=schedules
        )
        result.append(prayer_chain_data)

    return result


@log_view("prayer_chains", "Viewed prayer chain details")
def get_prayer_chain_by_id(db: Session, prayer_chain_id: int) -> PrayerChainResponse:
    """Get a specific prayer chain by ID with detailed family information"""
    prayer_chain = db.query(PrayerChain).filter(PrayerChain.id == prayer_chain_id).first()

    if not prayer_chain:
        raise HTTPException(status_code=404, detail="Prayer chain not found")

    family = db.query(Family).filter(Family.id == prayer_chain.family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    family_details = get_family_details(db, family)

    schedules = [
        ScheduleResponse(
            id=schedule.id,
            day=schedule.day,
            start_time=normalize_time(schedule.start_time),
            end_time=normalize_time(schedule.end_time),
            prayer_chain_id=schedule.prayer_chain_id
        )
        for schedule in prayer_chain.schedules
    ]

    return PrayerChainResponse(
        id=prayer_chain.id,
        family_id=prayer_chain.family_id,
        family_name=family_details["name"],
        family_details=family_details,
        schedules=schedules
    )


@log_create("prayer_chains", "Created or updated prayer chain")
def create_or_update_prayer_chain(db: Session, prayer_chain: PrayerChainCreate,
                                  allow_update: bool = True) -> PrayerChainResponse:
    """
    Smart endpoint: Creates prayer chain on first time, adds schedules on subsequent times
    """
    # Check if family exists
    family = db.query(Family).filter(Family.id == prayer_chain.family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    if not prayer_chain.schedules:
        raise HTTPException(status_code=400, detail="At least one schedule is required")

    # Normalize times in schedules
    normalized_schedules = [
        ScheduleCreate(
            day=schedule.day,
            start_time=normalize_time(schedule.start_time),
            end_time=normalize_time(schedule.end_time)
        )
        for schedule in prayer_chain.schedules
    ]

    # Check for collisions
    collision_check = validate_schedule_batch(normalized_schedules)
    if collision_check.has_collision:
        raise HTTPException(
            status_code=400,
            detail=f"Schedule conflicts detected: {collision_check.collision_details[0]}"
        )

    # Check if family already has a prayer chain
    existing_prayer_chain = db.query(PrayerChain).filter(
        PrayerChain.family_id == prayer_chain.family_id
    ).first()

    if existing_prayer_chain:
        # Check for collisions with existing schedules
        db_collision_check = check_db_schedule_collisions(db, existing_prayer_chain.id,
                                                        normalized_schedules)
        if db_collision_check.has_collision:
            raise HTTPException(
                status_code=400,
                detail=f"Schedule conflicts with existing schedules: {db_collision_check.collision_details[0]}"
            )

        # Add valid schedules
        for schedule_data in db_collision_check.valid_schedules:
            db_schedule = Schedule(
                day=schedule_data.day,
                start_time=normalize_time(schedule_data.start_time),
                end_time=normalize_time(schedule_data.end_time),
                prayer_chain_id=existing_prayer_chain.id
            )
            db.add(db_schedule)

        db.commit()
        return get_prayer_chain_by_id(db, existing_prayer_chain.id)

    else:
        # Create new prayer chain
        db_prayer_chain = PrayerChain(family_id=prayer_chain.family_id)
        db.add(db_prayer_chain)
        db.commit()
        db.refresh(db_prayer_chain)

        # Create schedules
        for schedule_data in normalized_schedules:
            db_schedule = Schedule(
                day=schedule_data.day,
                start_time=normalize_time(schedule_data.start_time),
                end_time=normalize_time(schedule_data.end_time),
                prayer_chain_id=db_prayer_chain.id
            )
            db.add(db_schedule)

        db.commit()
        return get_prayer_chain_by_id(db, db_prayer_chain.id)


@log_update("prayer_chains", "Updated prayer chain")
def update_prayer_chain(db: Session, prayer_chain_id: int, prayer_chain: PrayerChainUpdate) -> PrayerChainResponse:
    """Update an existing prayer chain"""
    db_prayer_chain = db.query(PrayerChain).filter(PrayerChain.id == prayer_chain_id).first()
    if not db_prayer_chain:
        raise HTTPException(status_code=404, detail="Prayer chain not found")

    update_data = prayer_chain.dict(exclude_unset=True)

    # If updating family_id, check if the new family exists and doesn't already have a prayer chain
    if "family_id" in update_data:
        new_family_id = update_data["family_id"]
        family = db.query(Family).filter(Family.id == new_family_id).first()
        if not family:
            raise HTTPException(status_code=404, detail="Family not found")

        existing_prayer_chain = db.query(PrayerChain).filter(
            PrayerChain.family_id == new_family_id,
            PrayerChain.id != prayer_chain_id
        ).first()

        if existing_prayer_chain:
            raise HTTPException(
                status_code=400,
                detail=f"Family '{family.name}' already has a prayer chain assigned"
            )

    for key, value in update_data.items():
        setattr(db_prayer_chain, key, value)

    db.commit()
    db.refresh(db_prayer_chain)
    return get_prayer_chain_by_id(db, db_prayer_chain.id)


@log_delete("prayer_chains", "Deleted prayer chain")
def delete_prayer_chain(db: Session, prayer_chain_id: int):
    """Delete a prayer chain and all its schedules"""
    db_prayer_chain = db.query(PrayerChain).filter(PrayerChain.id == prayer_chain_id).first()
    if not db_prayer_chain:
        raise HTTPException(status_code=404, detail="Prayer chain not found")

    db.delete(db_prayer_chain)
    db.commit()
    return {"message": "Prayer chain deleted successfully"}


@log_create("prayer_schedules", "Added schedule to prayer chain")
def add_schedule_to_prayer_chain(db: Session, prayer_chain_id: int, schedule: ScheduleCreate) -> ScheduleResponse:
    """Add a new schedule to an existing prayer chain with collision detection"""
    prayer_chain = db.query(PrayerChain).filter(PrayerChain.id == prayer_chain_id).first()
    if not prayer_chain:
        raise HTTPException(status_code=404, detail="Prayer chain not found")

    # Normalize times
    normalized_schedule = ScheduleCreate(
        day=schedule.day,
        start_time=normalize_time(schedule.start_time),
        end_time=normalize_time(schedule.end_time)
    )

    # Check for collisions
    collision_check = check_db_schedule_collisions(db, prayer_chain_id, [normalized_schedule])
    if collision_check.has_collision:
        raise HTTPException(
            status_code=400,
            detail=f"Schedule conflicts detected: {collision_check.collision_details[0]}"
        )

    db_schedule = Schedule(
        day=normalized_schedule.day,
        start_time=normalized_schedule.start_time,
        end_time=normalized_schedule.end_time,
        prayer_chain_id=prayer_chain_id
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    return ScheduleResponse(
        id=db_schedule.id,
        day=db_schedule.day,
        start_time=normalize_time(db_schedule.start_time),
        end_time=normalize_time(db_schedule.end_time),
        prayer_chain_id=db_schedule.prayer_chain_id
    )


@log_update("prayer_schedules", "Updated prayer schedule")
def update_schedule(db: Session, schedule_id: int, schedule: ScheduleUpdate) -> ScheduleResponse:
    """Update an existing schedule with collision detection"""
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = schedule.dict(exclude_unset=True)

    # Normalize times
    start_time = normalize_time(update_data.get("start_time", db_schedule.start_time))
    end_time = normalize_time(update_data.get("end_time", db_schedule.end_time))

    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")

    # Check for collisions if day or times are being updated
    if "day" in update_data or "start_time" in update_data or "end_time" in update_data:
        day = update_data.get("day", db_schedule.day)

        # Create a temporary schedule object for collision checking
        temp_schedule = ScheduleCreate(
            day=day,
            start_time=start_time,
            end_time=end_time
        )

        collision_check = check_db_schedule_collisions(
            db,
            db_schedule.prayer_chain_id,
            [temp_schedule],
            exclude_schedule_id=schedule_id
        )

        if collision_check.has_collision:
            raise HTTPException(
                status_code=400,
                detail=f"Schedule conflicts detected: {collision_check.collision_details[0]}"
            )

    for key, value in update_data.items():
        if key in ["start_time", "end_time"]:
            value = normalize_time(value)
        setattr(db_schedule, key, value)

    db.commit()
    db.refresh(db_schedule)

    return ScheduleResponse(
        id=db_schedule.id,
        day=db_schedule.day,
        start_time=normalize_time(db_schedule.start_time),
        end_time=normalize_time(db_schedule.end_time),
        prayer_chain_id=db_schedule.prayer_chain_id
    )


@log_delete("prayer_schedules", "Deleted prayer schedule")
def delete_schedule(db: Session, schedule_id: int):
    """Delete a specific schedule"""
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(db_schedule)
    db.commit()
    return {"message": "Schedule deleted successfully"}