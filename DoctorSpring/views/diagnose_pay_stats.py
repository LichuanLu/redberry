__author__ = 'zhangruixiang'

from flask import Blueprint, session
from DoctorSpring.models import DiagnosePayStats, DiagnosePayStatsLog
from DoctorSpring.util import result_status as rs,object2dict,constant
import json,decimal

diagnose_pay_stats_view = Blueprint('diagnose_pay_stats_view', __name__)

@diagnose_pay_stats_view.route('/stats/summary', methods=['GET'])
def getPayStatsSummary():
    user = session['userId']
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
def applyCash(user):
    user = session['userId']
    if user is None:
        result=rs.ResultStatus(rs.FAILURE.status,rs.FAILURE.msg)
        return  json.dumps(result.__dict__,ensure_ascii=False)
    result = DiagnosePayStats.updatePaidStatsStatus(user,constant.DiagnosePayStatsConstant.Ongoing, constant.DiagnosePayStatsConstant.Paying)
    dict = {}
    dict['money'] = float(result)
    resultJson=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,dict)
    return  json.dumps(resultJson.__dict__,ensure_ascii=False)

@diagnose_pay_stats_view.route('/stats/record/list/<int:stats>',
                               defaults={'paginate':False, 'pageIndex':1, 'pageSize':10}, methods=['GET'])
@diagnose_pay_stats_view.route('/stats/record/list/<int:stats>/<paginate>/<int:pageIndex>/<int:pageSize>', methods=['GET'])
def getRecordList(stats, paginate, pageIndex, pageSize):
    user = session['userId']
    return getList(user, DiagnosePayStats.getDetailPayStats(user, stats,paginate,pageIndex,pageSize))

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

