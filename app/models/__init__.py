from sqlalchemy.orm import relationship

from .family import Family
from .family_activity import Activity
from .recommendation import Program, Comment
from .feedback import Feedback, Reply

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
