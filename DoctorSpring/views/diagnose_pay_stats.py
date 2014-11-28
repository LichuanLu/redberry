__author__ = 'zhangruixiang'

from flask import Blueprint, session
from DoctorSpring.models import DiagnosePayStats, DiagnosePayStatsLog, DiagnosePayStatsLogRel, Diagnose, DiagnoseLog
from DoctorSpring.util import result_status as rs,object2dict,constant
import json,decimal,datetime

diagnose_pay_stats_view = Blueprint('diagnose_pay_stats_view', __name__)

@diagnose_pay_stats_view.route('/stats/summary', methods=['GET'])
def getPayStatsSummary():
    user = session['user_id']
    summary = DiagnosePayStats.getSummaryPayStats(user)
    dict={}
    dict['ongoing']=float(summary[0])
    dict['payable']=float(summary[1])
    dict['paid']=float(summary[2])
    dict['lastMonthRevenue']= float(summary[3])

    resultJson=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,dict)
    return  json.dumps(resultJson.__dict__,default=json_encode_decimal)

def json_encode_decimal(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError(repr(obj) + " is not JSON serializable")

@diagnose_pay_stats_view.route('/stats/applyCash', methods=['POST'])
def applyCash():
    return pay(constant.DiagnosePayStatsConstant.Ongoing, constant.DiagnosePayStatsConstant.Paying,
               constant.DiagnosePayStatsLogConstant.ApplyPay)

@diagnose_pay_stats_view.route('/stats/applyRefund/<int:diagnoseId>', methods=['POST'])
def applyRefund(diagnoseId):
    userId = session['user_id']
    diagoseLog=DiagnoseLog(userId,diagnoseId,constant.DiagnoseLogAction.DiagnoseRefund)
    DiagnoseLog.save(session,diagoseLog)

    diagnose = Diagnose.getDiagnoseById(diagnoseId)
    if diagnose.status == constant.DiagnoseStatus.Diagnosed:
        diagnosePayStats = DiagnosePayStats.getPayStatsByDiagnoseId(diagnoseId)
        for payStats in diagnosePayStats:
            payStats.status = constant.DiagnosePayStatsConstant.Refund
        DiagnosePayStats.updatePayStats(diagnosePayStats)

    return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)

@diagnose_pay_stats_view.route('/stats/diagnoseFinish/<int:diagnoseId>', methods=['POST'])
def diagnoseFinish(diagnoseId):
    diagnosePayStats = DiagnosePayStats()
    diagnose = Diagnose.getDiagnoseById(diagnoseId)
    diagnosePayStats.diagnoseId = diagnoseId
    diagnosePayStats.diagnoseSeriesNumber = diagnose.diagnoseSeriesNumber
    diagnosePayStats.userId = session["user_id"]
    diagnosePayStats.finishDate = datetime.now()
    diagnosePayStats.money = diagnose.money
    diagnosePayStats.status = constant.DiagnosePayStatsConstant.Ongoing
    DiagnosePayStats.save(diagnosePayStats)
    resultJson=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg)
    return  json.dumps(resultJson.__dict__,ensure_ascii=False)

@diagnose_pay_stats_view.route('/stats/finishPay', methods=['POST'])
def finishPay():
    return pay(constant.DiagnosePayStatsConstant.Paying, constant.DiagnosePayStatsConstant.Paid,
               constant.DiagnosePayStatsLogConstant.FinishPay)

def pay(statsOldStatus, statsNewStatus, logStatus):
    user = session['user_id']
    if user is None:
        result=rs.ResultStatus(rs.FAILURE.status,rs.FAILURE.msg)
        return  json.dumps(result.__dict__,ensure_ascii=False)
    result = DiagnosePayStats.updatePaidStatsStatus(user,statsOldStatus, statsNewStatus)
    log = DiagnosePayStatsLog.insertNewItem(logStatus,user,result[0])
    DiagnosePayStatsLogRel.insertNewItem(result[1],log)
    dict = {}
    dict['money'] = float(result[0])
    resultJson=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,dict)
    return  json.dumps(resultJson.__dict__,ensure_ascii=False)

@diagnose_pay_stats_view.route('/stats/record/list/<int:stats>',
                               defaults={'paginate':False, 'pageIndex':1, 'pageSize':10}, methods=['GET'])
@diagnose_pay_stats_view.route('/stats/record/list/<int:stats>/<paginate>/<int:pageIndex>/<int:pageSize>', methods=['GET'])
def getRecordList(stats, paginate, pageIndex, pageSize):
    user = session['user_id']
    return getList(user, DiagnosePayStats.getDetailPayStats(user, stats,paginate,pageIndex,pageSize))

@diagnose_pay_stats_view.route('/stats/log/list', methods=['GET'])
def getStatsLogList():
    user = session['user_id']
    return getList(user, DiagnosePayStatsLog.getLogList(user))

def getList(user, list):
    if user is None:
        result=rs.ResultStatus(rs.FAILURE.status,rs.FAILURE.msg)
        return  json.dumps(result.__dict__,ensure_ascii=False)
    if (list and len(list)>0):
        resultLogs=object2dict.objects2dicts(list)
        result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,resultLogs)
        return  json.dumps(result.__dict__,ensure_ascii=False)
    return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)