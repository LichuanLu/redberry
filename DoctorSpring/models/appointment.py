__author__ = 'zhangruixiang'

from database import Base
from database import db_session as session

class Appointment(Base):
    __tablename__ = 'appointment'
    __table_args__ = {
        'mysql_charset': 'utf8',
        'mysql_engine': 'MyISAM',
    }

