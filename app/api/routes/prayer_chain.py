# app/api/routes/prayer_chain.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.permissions import get_pastor_user
from app.db.session import get_db
from app.controllers.prayer_chain import (
    get_all_prayer_chains,
    get_prayer_chain_by_id,
    create_or_update_prayer_chain,
    delete_prayer_chain,
    delete_schedule
)
from app.models.user import User
from app.schemas.prayer_chain import (
    PrayerChainResponse,
    PrayerChainCreate
)

router = APIRouter()


@router.get("/", response_model=List[PrayerChainResponse])
def read_prayer_chains(
        db: Session = Depends(get_db),
        pastor_user: User = Depends(get_pastor_user)
):
    """Get all prayer chains with detailed family information - accessible only to church pastors"""
    try:
        prayer_chains = get_all_prayer_chains(db)
        return prayer_chains
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prayer chains: {str(e)}")


@router.get("/{prayer_chain_id}", response_model=PrayerChainResponse)
def read_prayer_chain(
        prayer_chain_id: int,
        db: Session = Depends(get_db),
        pastor_user: User = Depends(get_pastor_user)
):
    """Get a specific prayer chain by ID with detailed family information - accessible only to church pastors"""
    try:
        prayer_chain = get_prayer_chain_by_id(db, prayer_chain_id)
        return prayer_chain
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prayer chain: {str(e)}")


@router.post("/", response_model=PrayerChainResponse)
def create_or_add_prayer_chain_schedules(
        prayer_chain: PrayerChainCreate,
        db: Session = Depends(get_db),
        pastor_user: User = Depends(get_pastor_user)
):
    """
    Smart endpoint for prayer chains:
    - First time: Creates prayer chain with schedules for a family
    - Subsequent times: Adds more schedules to existing prayer chain

    Automatically handles collision detection for all schedules.
    """
    try:
        return create_or_update_prayer_chain(db, prayer_chain)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing prayer chain: {str(e)}")


@router.delete("/{prayer_chain_id}")
def delete_existing_prayer_chain(
        prayer_chain_id: int,
        db: Session = Depends(get_db),
        pastor_user: User = Depends(get_pastor_user)
):
    """Delete a prayer chain and all its schedules - accessible only to church pastors"""
    try:
        return delete_prayer_chain(db, prayer_chain_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting prayer chain: {str(e)}")


@router.delete("/schedules/{schedule_id}")
def delete_existing_schedule(
        schedule_id: int,
        db: Session = Depends(get_db),
        pastor_user: User = Depends(get_pastor_user)
):
    """Delete a specific schedule - accessible only to church pastors"""
    try:
        return delete_schedule(db, schedule_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting schedule: {str(e)}")