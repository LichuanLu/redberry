__author__ = 'zhangruixiang'

from Flask import Blueprint, session
from DoctorSpring.models import DiagnosePayStats, DiagnosePayStatsLog
from DoctorSpring.util import result_status as rs,object2dict,constant
import json

diagnose_pay_stats_view = Blueprint('diagnose_pay_stats_view', __name__)

@diagnose_pay_stats_view.route('/stats/summary', methods=['GET'])
def getPayStatsSummary():
    user = session['userId']
    return getList(user, DiagnosePayStats.getSummaryPayStats(user))

@diagnose_pay_stats_view.route('/stats/applyCash', methods=['POST'])
def applyCash():
    user = session['userId']
    if user is None:
        result=rs.ResultStatus(rs.FAILURE.status,rs.FAILURE.msg)
        return  json.dumps(result.__dict__,ensure_ascii=False)
    result = DiagnosePayStats.updatePaidStatsStatus(user,constant.DiagnosePayStatsConstant.Ongoing, constant.DiagnosePayStatsConstant.Paying)
    resultDict=object2dict.objects2dicts(result)
    resultJson=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,resultDict)
    return  json.dumps(resultJson.__dict__,ensure_ascii=False)

@diagnose_pay_stats_view.route('/stats/record/list/<int:status>,<bool:paginate>,<int:pageIndex>,<int:pageSize>', methods=['GET'])
def getRecordList(status, paginate, pageIndex, pageSize):
    user = session['userId']
    return getList(user, DiagnosePayStats.getDetailPayStats(user,status,paginate,pageIndex,pageSize))

@diagnose_pay_stats_view.route('/stats/log/list', methods=['GET'])
def getStatsLogList():
    user = session['userId']
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

