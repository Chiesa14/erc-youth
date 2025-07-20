from sqlalchemy.orm import relationship

from .family import Family
from .family_activity import Activity

Family.activities = relationship("Activity", back_populates="family", cascade="all, delete")
Activity.family = relationship("Family", back_populates="activities")
