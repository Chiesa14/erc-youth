from typing import List, Tuple, Dict, Optional
from datetime import time, datetime
from sqlalchemy.orm import Session
from app.schemas.prayer_chain import ScheduleCreate, ScheduleCollisionResponse
from app.models.prayer_chain import Schedule


def normalize_time(t: time) -> time:
    """Convert offset-aware time to offset-naive time if necessary"""
    if isinstance(t, datetime):
        # If input is a datetime, convert to naive time
        if t.tzinfo is not None:
            t = t.replace(tzinfo=None)
        return t.time()
    elif isinstance(t, time):
        # If input is already a time object, ensure it's naive
        if hasattr(t, 'tzinfo') and t.tzinfo is not None:
            # Create a new time object without timezone
            return time(t.hour, t.minute, t.second, t.microsecond)
        return t
    raise ValueError(f"Invalid time object: {type(t)}")


def validate_schedule_batch(schedules: List[ScheduleCreate]) -> ScheduleCollisionResponse:
    """
    Validate a batch of schedules for internal collisions
    Returns details about any collisions found
    """
    collision_details = []
    valid_schedules = []
    conflicting_schedules = []
    has_collision = False

    # Group schedules by day for easier collision detection
    schedules_by_day: Dict[str, List[Tuple[int, ScheduleCreate]]] = {}

    for i, schedule in enumerate(schedules):
        # Normalize times
        start_time = normalize_time(schedule.start_time)
        end_time = normalize_time(schedule.end_time)

        # Basic validation
        if start_time >= end_time:
            collision_details.append(f"Start time must be before end time")
            conflicting_schedules.append(schedule)
            has_collision = True
            continue

        day = schedule.day.value
        if day not in schedules_by_day:
            schedules_by_day[day] = []
        schedules_by_day[day].append((i, schedule))

    # Check for collisions within each day
    for day, day_schedules in schedules_by_day.items():
        for i, (idx1, schedule1) in enumerate(day_schedules):
            schedule1_valid = True
            start1 = normalize_time(schedule1.start_time)
            end1 = normalize_time(schedule1.end_time)
            for j, (idx2, schedule2) in enumerate(day_schedules[i + 1:], i + 1):
                start2 = normalize_time(schedule2.start_time)
                end2 = normalize_time(schedule2.end_time)
                if (start1 < end2 and end1 > start2):
                    collision_details.append(
                        f"Schedule collision on {day}: "
                        f"Schedule {idx1 + 1} ({start1}-{end1}) "
                        f"overlaps with Schedule {idx2 + 1} ({start2}-{end2})"
                    )
                    if schedule1 not in conflicting_schedules:
                        conflicting_schedules.append(schedule1)
                    if schedule2 not in conflicting_schedules:
                        conflicting_schedules.append(schedule2)
                    schedule1_valid = False
                    has_collision = True

            if schedule1_valid and schedule1 not in valid_schedules:
                valid_schedules.append(schedule1)

    return ScheduleCollisionResponse(
        has_collision=has_collision,
        collision_details=collision_details if collision_details else None,
        valid_schedules=valid_schedules,
        conflicting_schedules=conflicting_schedules
    )


def check_db_schedule_collisions(
    db: Session,
    prayer_chain_id: int,
    schedules: List[ScheduleCreate],
    exclude_schedule_id: Optional[int] = None
) -> ScheduleCollisionResponse:
    """
    Check if new schedules collide with existing schedules in the database
    for a given prayer chain
    """
    collision_details = []
    valid_schedules = []
    conflicting_schedules = []
    has_collision = False

    # First validate internal collisions
    internal_validation = validate_schedule_batch(schedules)
    if internal_validation.has_collision:
        return internal_validation

    # Check against existing schedules in DB
    for i, new_schedule in enumerate(schedules):
        new_start = normalize_time(new_schedule.start_time)
        new_end = normalize_time(new_schedule.end_time)

        query = db.query(Schedule).filter(
            Schedule.prayer_chain_id == prayer_chain_id,
            Schedule.day == new_schedule.day
        )

        if exclude_schedule_id:
            query = query.filter(Schedule.id != exclude_schedule_id)

        existing_schedules = query.all()

        schedule_valid = True
        for existing in existing_schedules:
            exist_start = normalize_time(existing.start_time)
            exist_end = normalize_time(existing.end_time)
            if (new_start < exist_end and new_end > exist_start):
                collision_details.append(
                    f"Schedule {i + 1} ({new_start}-{new_end}) "
                    f"on {new_schedule.day.value} collides with existing schedule "
                    f"({exist_start}-{exist_end})"
                )
                conflicting_schedules.append(new_schedule)
                schedule_valid = False
                has_collision = True

        if schedule_valid:
            valid_schedules.append(new_schedule)

    return ScheduleCollisionResponse(
        has_collision=has_collision,
        collision_details=collision_details if collision_details else None,
        valid_schedules=valid_schedules,
        conflicting_schedules=conflicting_schedules
    )


def format_time_range(start_time: time, end_time: time) -> str:
    """Format time range for display"""
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)
    return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"


def get_schedule_summary(schedules: List[ScheduleCreate]) -> Dict[str, List[str]]:
    """Get a summary of schedules grouped by day"""
    summary = {}
    for schedule in schedules:
        day = schedule.day.value
        if day not in summary:
            summary[day] = []
        summary[day].append(format_time_range(schedule.start_time, schedule.end_time))
    return summary