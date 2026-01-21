from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.worship_team import WorshipTeamActivity, WorshipTeamMember, WorshipTeamSong
from app.schemas.worship_team import (
    WorshipTeamActivityCreate,
    WorshipTeamActivityUpdate,
    WorshipTeamMemberCreate,
    WorshipTeamMemberUpdate,
    WorshipTeamSongCreate,
    WorshipTeamSongUpdate,
)


def list_activities(db: Session, frequency=None):
    query = db.query(WorshipTeamActivity)
    if frequency:
        query = query.filter(WorshipTeamActivity.frequency == frequency)
    return query.order_by(WorshipTeamActivity.id.desc()).all()


def create_activity(db: Session, payload: WorshipTeamActivityCreate):
    item = WorshipTeamActivity(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_activity(db: Session, activity_id: int, payload: WorshipTeamActivityUpdate):
    item = db.query(WorshipTeamActivity).filter(WorshipTeamActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_activity(db: Session, activity_id: int) -> None:
    item = db.query(WorshipTeamActivity).filter(WorshipTeamActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(item)
    db.commit()


def list_members(db: Session):
    return db.query(WorshipTeamMember).order_by(WorshipTeamMember.id.desc()).all()


def create_member(db: Session, payload: WorshipTeamMemberCreate):
    item = WorshipTeamMember(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_member(db: Session, member_id: int, payload: WorshipTeamMemberUpdate):
    item = db.query(WorshipTeamMember).filter(WorshipTeamMember.id == member_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Member not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_member(db: Session, member_id: int) -> None:
    item = db.query(WorshipTeamMember).filter(WorshipTeamMember.id == member_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(item)
    db.commit()


def list_songs(db: Session):
    return db.query(WorshipTeamSong).order_by(WorshipTeamSong.id.desc()).all()


def create_song(db: Session, payload: WorshipTeamSongCreate):
    item = WorshipTeamSong(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_song(db: Session, song_id: int, payload: WorshipTeamSongUpdate):
    item = db.query(WorshipTeamSong).filter(WorshipTeamSong.id == song_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Song not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_song(db: Session, song_id: int) -> None:
    item = db.query(WorshipTeamSong).filter(WorshipTeamSong.id == song_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Song not found")
    db.delete(item)
    db.commit()
