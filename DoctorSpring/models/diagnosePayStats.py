__author__ = 'zhangruixiang'

import sqlalchemy as sa
from DoctorSpring.util import constant
from database import Base, db_session as session
from datetime import datetime, timedelta
import calendar

class DiagnosePayStats(Base):
    __tablename__ = 'diagnose_pay_stats'
    __table_args__ = {
        'mysql_charset': 'utf8',
        'mysql_engine': 'MyISAM',
        }

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    diagnoseId = sa.Column(sa.Integer, sa.ForeignKey('diagnose.id'))
    userId = sa.Column(sa.Integer, sa.ForeignKey('user.id'))
    diagnoseSeriesNumber = sa.Column(sa.String(64))
    approveId = sa.Column(sa.Integer, sa.ForeignKey('user.id'))
    finishDate = sa.Column(sa.DateTime)
    money = sa.Column(sa.Integer)
    status = sa.Column(sa.Integer)

    @classmethod
    def getDetailPayStats(cls, user, payStats, pagination=False, pageIndex=1, pageSize=10):
        if not pagination:
            if payStats == constant.DiagnosePayStatsConstant.Ongoing:
                return session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                              DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                              datetime.today()+timedelta(days=-constant.RollbackPeriod) >= DiagnosePayStats.finishDate)\
                    .order_by(DiagnosePayStats.finishDate.desc()).all()
            if payStats == constant.DiagnosePayStatsConstant.Payable:
                return session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                              DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                              DiagnosePayStats.finishDate>datetime.today()+timedelta(days=-constant.RollbackPeriod) ) \
                    .order_by(DiagnosePayStats.finishDate.desc()).all()
            if payStats == constant.DiagnosePayStatsConstant.Paid:
                return  session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                               DiagnosePayStats.status == constant.DiagnosePayStatsConstant.Paid) \
                    .order_by(DiagnosePayStats.finishDate.desc()).all()
            if payStats == constant.DiagnosePayStatsConstant.All:
                return  session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId)\
                    .order_by(DiagnosePayStats.finishDate.desc()).all()
        else:
            if payStats == constant.DiagnosePayStatsConstant.Ongoing:
                return session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                              DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                              datetime.today()+timedelta(days=-constant.RollbackPeriod) >= DiagnosePayStats.finishDate) \
                    .order_by(DiagnosePayStats.finishDate.desc()).offset(pageIndex).limit(pageSize)
            if payStats == constant.DiagnosePayStatsConstant.Payable:
                return session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                              DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                              DiagnosePayStats.finishDate>datetime.today()+timedelta(days=-constant.RollbackPeriod)) \
                    .order_by(DiagnosePayStats.finishDate.desc()).offset(pageIndex).limit(pageSize)
            if payStats == constant.DiagnosePayStatsConstant.Paid:
                return  session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId,
                                                               DiagnosePayStats.status == constant.DiagnosePayStatsConstant.Paid) \
                    .order_by(DiagnosePayStats.finishDate.desc()).offset(pageIndex).limit(pageSize)
            if payStats == constant.DiagnosePayStatsConstant.All:
                return  session.query(DiagnosePayStats).filter(user == DiagnosePayStats.userId) \
                    .order_by(DiagnosePayStats.finishDate.desc()).offset(pageIndex).limit(pageSize)

    @classmethod
    def getOngoingSummary(cls, user):
        return session.query(sa.func.sum(DiagnosePayStats.money)).filter(DiagnosePayStats.userId==user,
                                                                         DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                                         datetime.today()+timedelta(days=-constant.RollbackPeriod) >= DiagnosePayStats.finishDate) \
            .group_by(DiagnosePayStats.userId).all()

    @classmethod
    def getPayableSummary(cls, user):
        return session.query(sa.func.sum(DiagnosePayStats.money)).filter(DiagnosePayStats.userId==user,
                                                                         DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                                         DiagnosePayStats.finishDate>datetime.today()+timedelta(days=-constant.RollbackPeriod)) \
            .group_by(DiagnosePayStats.userId).all()

    @classmethod
    def getPaidSummary(cls, user):
        return session.query(sa.func.sum(DiagnosePayStats.money)).filter(user == DiagnosePayStats.userId,
                                                                         DiagnosePayStats.status == constant.DiagnosePayStatsConstant.Paid) \
            .group_by(DiagnosePayStats.userId).all()

    @classmethod
    def getLastMonthRevenue(cls, user):
        lastMonthStartDate = cls.getStartLastDayOfLastMonth()[0]
        lastMonthFinishDate = cls.getStartLastDayOfLastMonth()[1]
        lastMonthRevenue = session.query(sa.func.sum(DiagnosePayStats.money)).filter(user == DiagnosePayStats.userId,
                                                                                     lastMonthFinishDate > DiagnosePayStats.finishDate,
                                                                                     DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Ongoing,
                                                                                     DiagnosePayStats.finishDate >= lastMonthStartDate,
                                                                                     DiagnosePayStats.finishDate>datetime.today()+timedelta(days=-constant.RollbackPeriod)) \
            .group_by(DiagnosePayStats.userId).all()
        lastMonthRevenue += session.query(sa.func.sum(DiagnosePayStats.money)).filter(user == DiagnosePayStats.userId,
                                                                                      lastMonthFinishDate > DiagnosePayStats.finishDate,
                                                                                      DiagnosePayStats.status==constant.DiagnosePayStatsConstant.Paid,
                                                                                      DiagnosePayStats.finishDate >= lastMonthStartDate) \
            .group_by(DiagnosePayStats.userId).all()
        return lastMonthRevenue

    @classmethod
    def getSummaryPayStats(cls, user):
        ongoing = cls.getOngoingSummary(user)
        usable = cls.getPayableSummary(user)
        paid = cls.getPaidSummary(user)
        lastMonthRevenue = cls.getLastMonthRevenue(user)
        return ongoing,usable,paid,lastMonthRevenue

    @classmethod
    def updatePaidStatsStatus(cls, user, prevStatus,status):
        if user is None or prevStatus is None or status is None:
            return
        if prevStatus == constant.DiagnosePayStatsConstant.Ongoing:
            result = session.query(DiagnosePayStats,sa.func.sum(DiagnosePayStats.money).label('cash')).filter(user == DiagnosePayStats.userId,
                                                                 prevStatus == DiagnosePayStats.status,
                                                                 datetime.today()+timedelta(days=-constant.RollbackPeriod)>DiagnosePayStats.finishDate)\
            .update(dict(status=status))
        else:
            result = session.query(DiagnosePayStats,sa.func.sum(DiagnosePayStats.money).label('cash')).filter(user == DiagnosePayStats.userId,
                                                                  prevStatus == DiagnosePayStats.status) \
            .update(dict(status=status))
        session.commit()
        session.flush()
        return result.cash

    @classmethod
    def save(cls,payStats):
        if payStats:
            session.add(payStats)
            session.commit()
            session.flush()

    @classmethod
    def getStartLastDayOfLastMonth(cls):
        current = datetime.now()
        year = current.year
        month = current.month

        if month == 1:
            month = 12
            year -= 1
        else :
            month -= 1
        days = calendar.monthrange(year, month)[1]
        return datetime(year,month,1).strftime('%Y-%m-%d %X'), \
               (datetime(year,month,1)+timedelta(days= days)).strftime('%Y-%m-%d %X')

class DiagnosePayStatsLog(Base):
    __tablename__ = 'diagnose_pay_stats_log'
    __table_args__ = {
        'mysql_charset': 'utf8',
        'mysql_engine': 'MyISAM',
        }

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    userId = sa.Column(sa.Integer, sa.ForeignKey('user.id'))
    action = sa.Column(sa.Integer)
    type = sa.Column(sa.Integer)
    date = sa.Column(sa.DateTime)
    money = sa.Column(sa.Integer)
    status = sa.Column(sa.Integer)

    @classmethod
    def save(cls,payStatsLog):
        if payStatsLog:
            session.add(payStatsLog)
            session.commit()
            session.flush()

    @classmethod
    def getLogList(cls,user):
        return session.query(DiagnosePayStatsLog).filter(user == DiagnosePayStatsLog.user,
                                                         constant.DiagnosePayStatsLogConstant.FinishPay == DiagnosePayStatsLog.action)\
            .order_by(DiagnosePayStatsLog.date.desc())

class DiagnosePayStatsLogRel(Base):
    __tablename__ = 'diagnose_pay_stats_relation'
    __table_args__ = {
        'mysql_charset': 'utf8',
        'mysql_engine': 'MyISAM',
        }

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    payStatsId = sa.Column(sa.Integer, sa.ForeignKey('diagnose_pay_stats.id'))
    logId = sa.Column(sa.Integer, sa.ForeignKey('diagnose_pay_stats_log.id'))
    status = sa.Column(sa.Integer)

    @classmethod
    def save(cls,payStatsLogRel):
        if payStatsLogRel:
            session.add(payStatsLogRel)
            session.commit()
            session.flush()