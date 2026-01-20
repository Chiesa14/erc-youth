from sqlalchemy.orm import relationship

from .family import Family
from .family_activity import Activity
from .family_activity_checkin import ActivityCheckinSession, ActivityAttendance
from .recommendation import Program, Comment
from .feedback import Feedback, Reply
from .system_log import SystemLog
from .family_role import FamilyRole
from .anti_drugs_unit import AntiDrugsActivity, AntiDrugsTestimony, AntiDrugsOutreachPlan
from .worship_team import WorshipTeamActivity
from .organization import OrganizationPosition, SmallCommittee, SmallCommitteeDepartment, SmallCommitteeMember

Family.activities = relationship("Activity", back_populates="family", cascade="all, delete")
Activity.family = relationship("Family", back_populates="activities")

# Recommendation relationships
Family.programs = relationship("Program", back_populates="family", cascade="all, delete")
Family.comments = relationship("Comment", back_populates="family", cascade="all, delete")
Program.family = relationship("Family", back_populates="programs")
Comment.family = relationship("Family", back_populates="comments")

# Feedback relationships
Family.feedback = relationship("Feedback", back_populates="family", cascade="all, delete")
Feedback.family = relationship("Family", back_populates="feedback")
Feedback.replies = relationship("Reply", back_populates="feedback", cascade="all, delete")
Reply.feedback = relationship("Feedback", back_populates="replies")

# System logging relationships
Family.system_logs = relationship("SystemLog", back_populates="family")
SystemLog.family = relationship("Family", back_populates="system_logs")

