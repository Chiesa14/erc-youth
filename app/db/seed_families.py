"""
Seed script for all families from SYSTEM.md documentation.
Creates 27 families: 15 Mature Adults Families and 12 Young Adults Families.
"""

from sqlalchemy.orm import Session
from app.models.family import Family
import logging

logger = logging.getLogger(__name__)

# Mature Adults Families (15)
MATURE_ADULTS_FAMILIES = [
    "Joseph", "Benaiah", "David", "Daniel", "Nathan",
    "Nehemiah", "Joel", "Samuel", "Isaac", "Caleb",
    "Ezekiel", "Ezra", "Jeremiah", "Phineas", "Elijah"
]

# Young Adults Families (12)
YOUNG_ADULTS_FAMILIES = [
    "Samuel", "Isaac", "Caleb", "Joel", "Nathan",
    "Nehemiah", "David", "Daniel", "Perez", "Phinehas",
    "Benaiah", "Ezra"
]


def seed_families(db: Session) -> int:
    """
    Seed all families from documentation.
    Returns the number of families created.
    """
    created_count = 0
    
    # Seed Mature Adults Families
    for family_name in MATURE_ADULTS_FAMILIES:
        existing = db.query(Family).filter(
            Family.name == family_name,
            Family.category == "Mature"
        ).first()
        
        if not existing:
            new_family = Family(
                name=family_name,
                category="Mature"
            )
            db.add(new_family)
            created_count += 1
            logger.info(f"Created Mature Adults family: {family_name}")
    
    # Seed Young Adults Families
    for family_name in YOUNG_ADULTS_FAMILIES:
        existing = db.query(Family).filter(
            Family.name == family_name,
            Family.category == "Young"
        ).first()
        
        if not existing:
            new_family = Family(
                name=family_name,
                category="Young"
            )
            db.add(new_family)
            created_count += 1
            logger.info(f"Created Young Adults family: {family_name}")
    
    db.commit()
    
    if created_count > 0:
        logger.info(f"Seeded {created_count} families successfully")
    else:
        logger.info("All families already exist, no seeding needed")
    
    return created_count


def get_family_stats(db: Session) -> dict:
    """Get statistics about seeded families."""
    mature_count = db.query(Family).filter(Family.category == "Mature").count()
    young_count = db.query(Family).filter(Family.category == "Young").count()
    
    return {
        "mature_adults_families": mature_count,
        "young_adults_families": young_count,
        "total": mature_count + young_count
    }
