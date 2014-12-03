# coding: utf-8
__author__ = 'ccheng'

from flask import Flask, request, session, g, redirect, url_for, Blueprint, jsonify
from flask import abort, render_template, flash
from flask.ext.login import login_user, logout_user, current_user, login_required
from forms import LoginForm ,CommentsForm ,UserFavortiesForm,ThanksNoteForm ,UserUpdateForm,UserChangePasswdForm,DoctorUpdateForm,UserResetPasswdForm
from DoctorSpring import lm
from database import  db_session
from sqlalchemy.exc import IntegrityError
from DoctorSpring.models import User,Patient,Doctor,Diagnose ,DiagnoseTemplate,DoctorProfile ,Department,Skill
from DoctorSpring.models import User,Comment,Message ,UserFavorites,UserRole ,ThanksNote,Hospital ,Doctor2Skill
from DoctorSpring.util import result_status as rs,object2dict,pdf_utils,constant
from DoctorSpring.util.constant import MessageUserType,Pagger,ReportType,ReportStatus
from DoctorSpring.util.authenticated import authenticated
from param_service import UserCenter
from database import db_session
from datetime import datetime
import string
from werkzeug.security import generate_password_hash, check_password_hash
from config import ALLOWED_PICTURE_EXTENSIONS
import  data_change_service as dataChangeService
from os.path import getsize
import json

import config
from config import LOGIN_URL,ERROR_URL
config = config.rec()
from DoctorSpring import app
LOG=app.logger

uc = Blueprint('user_center', __name__)



@uc.route('/doctorhome',  methods = ['GET', 'POST'])
def endterDoctorHome():
    userId=session['userId']
    doctor=Doctor.getByUserId(userId)

    if doctor is None:
        return redirect(ERROR_URL)

    resultDate={}
    messageCount=Message.getMessageCountByReceiver(userId)
    resultDate['messageCount']=messageCount

    diagnoseCount=Diagnose.getNewDiagnoseCountByDoctorId(doctor.id)
    resultDate['diagnoseCount']=diagnoseCount

    resultDate['doctor']=doctor
    pager=Pagger(1,20)
    diagnoses=Diagnose.getDiagnosesByDoctorId(db_session,doctor.id,pager)
    diagnoseDict=dataChangeService.userCenterDiagnoses(diagnoses)
    resultDate['diagnoses']=diagnoseDict
    return render_template("doctorHome.html",data=resultDate)

@uc.route('/patienthome',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Patient)
def endterPatientHome():
    if session.has_key('userId'):
        userId=session['userId']
        user=User.getById(userId)

        if user is None:
            return redirect(ERROR_URL)

        resultDate={}
        messageCount=Message.getMessageCountByReceiver(userId)
        resultDate['messageCount']=messageCount

        diagnoseCount=Diagnose.getNewDiagnoseCountByUserId(userId)
        resultDate['diagnoseCount']=diagnoseCount

        resultDate['user']=user
        #pager=Pagger(1,20)
        # diagnoses=Diagnose.getDiagnosesByDoctorId(db_session,doctor.id,pager)
        # diagnoseDict=dataChangeService.userCenterDiagnoses(diagnoses)
        # resultDate['diagnoses']=diagnoseDict
        return render_template("patientHome.html",data=resultDate)
    else:
        return redirect(LOGIN_URL)

@uc.route('/admin/kefu',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Kefu)

def endterKefuhome():

    return render_template("adminKefu.html")

@uc.route('/hospital/user',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.HospitalUser)
def endterHospitalUserHome():
    userId=session['userId']
    user=User.getById(userId)

    if user is None:
        return redirect(ERROR_URL)

    resultDate={}
    # messageCount=Message.getMessageCountByReceiver(userId)
    # resultDate['messageCount']=messageCount
    #
    # diagnoseCount=Diagnose.getNewDiagnoseCountByUserId(userId)
    # resultDate['diagnoseCount']=diagnoseCount
    #
    # resultDate['user']=user
    #pager=Pagger(1,20)
    # diagnoses=Diagnose.getDiagnosesByDoctorId(db_session,doctor.id,pager)
    # diagnoseDict=dataChangeService.userCenterDiagnoses(diagnoses)
    # resultDate['diagnoses']=diagnoseDict
    return render_template("hospitalUser.html",data=resultDate)




@uc.route('/doctor/site/<int:userId>',  methods = ['GET', 'POST'])
def endterDoctorSite(userId):

    #user=User.getById(userId)
    doctor=Doctor.getByUserId(userId)

    if  doctor is None:
        return redirect(ERROR_URL)

    if  hasattr(doctor,'user') !=True:
        return redirect(ERROR_URL)

    resultDate={}
    userFavortiesCount=UserFavorites.getFavortiesCountByDoctorId(doctor.id)
    resultDate['userFavortiesCount']=userFavortiesCount

    diagnoseCount=Diagnose.getDiagnoseCountByDoctorId(db_session,doctor.id)
    resultDate['diagnoseCount']=diagnoseCount

    goodDiagnoseCount=Diagnose.getDiagnoseCountByDoctorId(db_session,doctor.id,1)#good
    goodDiagnoseCount+=Diagnose.getDiagnoseCountByDoctorId(db_session,doctor.id,2)
    resultDate['goodDiagnoseCount']=goodDiagnoseCount

    resultDate['doctor']=dataChangeService.get_doctor(doctor)

    thanksNoteCount=ThanksNote.getThanksNoteCountByReceiver(db_session,userId)
    resultDate['thanksNoteCount']=thanksNoteCount

    diagnoseCommentCount=Comment.getCountByReceiver(userId)
    resultDate['diagnoseCommentCount']=diagnoseCommentCount

    if session.has_key('userId'):
        loginUserId=session.get('userId')
        if loginUserId:
            loginUserId=string.atoi(loginUserId)
            userfavor=UserFavorites.getUerFavortiesByNormalStatus(db_session,loginUserId,constant.UserFavoritesType.Doctor,doctor.id)
            if userfavor:
                resultDate['userFavortiesId']=userfavor.id





    pager=constant.Pagger(1,10)

    diagnoseComments=Comment.getCommentByReceiver(userId,constant.ModelStatus.Normal,constant.CommentType.DiagnoseComment,pager)
    if diagnoseComments  and  len(diagnoseComments)>0:
        diagnoseCommentsDict=object2dict.objects2dicts(diagnoseComments)
        dataChangeService.setDiagnoseCommentsDetailInfo(diagnoseCommentsDict)
        resultDate['comments']=diagnoseCommentsDict
    else:
        resultDate['comments']=None


    thanksNotes=ThanksNote.getThanksNoteByReceiver(db_session,userId)
    if thanksNotes  and  len(thanksNotes)>0:
        thanksNotesDict=object2dict.objects2dicts(thanksNotes)
        dataChangeService.setThanksNoteDetail(thanksNotesDict)
        resultDate['thanksNotes']=thanksNotesDict

    intros=DoctorProfile.getDoctorProfiles(userId,constant.DoctorProfileType.Intro)
    resultDate['intros']=object2dict.objects2dicts(intros)

    resumes=DoctorProfile.getDoctorProfiles(userId,constant.DoctorProfileType.Resume)
    resultDate['resumes']=object2dict.objects2dicts(resumes)

    awards=DoctorProfile.getDoctorProfiles(userId,constant.DoctorProfileType.Award)
    resultDate['awards']=object2dict.objects2dicts(awards)

    others=DoctorProfile.getDoctorProfiles(userId,constant.DoctorProfileType.Other)
    resultDate['others']=object2dict.objects2dicts(others)

    return render_template("doctorSite.html",data=resultDate)




@uc.route('/admin/diagnose/list/all',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Admin)
def getDiagnoseListByAdmin2():

    userId=session['userId']

    hostpitalIds=request.args.get('hospitalId')
    hostpitalList=UserCenter.getDiagnoseListByAdmin(hostpitalIds)
    doctorName=request.args.get('doctorName')
    pageNo=request.args.get('pageNo')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)
    diagnoses=Diagnose.getDiagnoseByAdmin2(db_session,hostpitalList,doctorName,pager)
    diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)


    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)



@uc.route('/admin/diagnose/list/my',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Admin)
def getDiagnoseListByAdmin():
    userId=session['userId']
    # user=User.getById(userId)
    # if user is None:
    #     return  json.dumps(rs.NO_DATA.__dict__,ensure_ascii=False)
    #     #权限查看
    # if UserRole.checkRole(db_session,userId,constant.RoleId.Admin):
    #     return  json.dumps(rs.PERMISSION_DENY.__dict__,ensure_ascii=False)

    status=request.args.get('status')
    if status:
        import string
        status=string.atoi(status)

    startDateStr=request.args.get('startDate')
    startDate=None
    if startDateStr:
        startDate=datetime.strptime(startDateStr,"%Y-%m-%d")
    else:
        startDate=constant.SystemTimeLimiter.startTime

    endDateStr=request.args.get('endDate')
    endDate=None
    if endDateStr:
        endDate=datetime.strptime(endDateStr,"%Y-%m-%d")
    else:
        endDate=constant.SystemTimeLimiter.endTime

    pageNo=request.args.get('pageNo')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)

    diagnoses=Diagnose.getDiagnosesByAdmin(db_session,pager,status,userId,startDate,endDate)
    diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)


@uc.route('/hospital/user/list/unfinish',  methods = ['GET', 'POST'])
#@authenticated('admin',constant.RoleId.Admin)
def getDiagnoseListByHospitalUser():

     userId=session['userId']


     pageNo=request.args.get('pageNumber')
     pageSize=request.args.get('pageSize')
     pager=Pagger(pageNo,pageSize)
     diagnoses=Diagnose.getNeedDealDiagnoseByHospitalUser(db_session,userId,None,pager)
     #type fullFile代表查询文件返回文件全部信息，如果没有只返回FILE URL
     diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses,'fullFile')


     resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
     resultDict=resultStatus.__dict__
     return json.dumps(resultDict,ensure_ascii=False)


@uc.route('/hospital/user/list/all',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.HospitalUser)
def getDiagnoseListByHospitalUser2():

    userId=session['userId']

    status=request.args.get('status')
    if status:
        import string
        status=string.atoi(status)

    startDateStr=request.args.get('startDate')
    startDate=None
    if startDateStr:
        startDate=datetime.strptime(startDateStr,"%Y-%m-%d")
    else:
        startDate=constant.SystemTimeLimiter.startTime

    endDateStr=request.args.get('endDate')
    endDate=None
    if endDateStr:
        endDate=datetime.strptime(endDateStr,"%Y-%m-%d")
    else:
        endDate=constant.SystemTimeLimiter.endTime

    patientName=request.args.get('patientName')
    pageNo=request.args.get('pageNumber')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)
    diagnoses=Diagnose.getDealedDiagnoseByHospitalUser(db_session,userId,patientName,status,startDate,endDate,pager)
    diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)


    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)


@uc.route('/diagnose/list',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Doctor)
def getDiagnoseListByDoctor():
    userId=session['userId']
    # user=User.getById(userId)
    # if user is None:
    #     return  json.dumps(rs.NO_DATA.__dict__,ensure_ascii=False)
    #     #权限查看
    # if UserRole.checkRole(db_session,userId,constant.RoleId.Admin):
    #     return  json.dumps(rs.PERMISSION_DENY.__dict__,ensure_ascii=False)
    doctor=Doctor.getByUserId(userId)
    if doctor:

        status=request.args.get('type')
        if status:
            import string
            status=string.atoi(status)

        startDateStr=request.args.get('startDate')
        startDate=None
        if startDateStr:
            startDate=datetime.strptime(startDateStr,"%Y-%m-%d")
        else:
            startDate=constant.SystemTimeLimiter.startTime

        endDateStr=request.args.get('endDate')
        endDate=None
        if endDateStr:
            endDate=datetime.strptime(endDateStr,"%Y-%m-%d")
        else:
            endDate=constant.SystemTimeLimiter.endTime

        pageNo=request.args.get('pageNo')
        pageSize=request.args.get('pageSize')
        pager=Pagger(pageNo,pageSize)
        diagnoses=Diagnose.getDiagnosesByDoctorId(db_session,doctor.id,pager,status,startDate,endDate)
        diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)
        resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
        resultDict=resultStatus.__dict__
        return json.dumps(resultDict,ensure_ascii=False)
    return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)


@uc.route('/patient/diagnose/list',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.Patient)
def getDiagnoseListByPatient():
    userId=session['userId']
    # user=User.getById(userId)
    # if user is None:
    #     return  json.dumps(rs.NO_DATA.__dict__,ensure_ascii=False)
    #     #权限查看
    # if UserRole.checkRole(db_session,userId,constant.RoleId.Admin):
    #     return  json.dumps(rs.PERMISSION_DENY.__dict__,ensure_ascii=False)

    if userId:

        status=request.args.get('type')
        if status:
            import string
            status=string.atoi(status)
        if status==u'':
            status=None

        startDateStr=request.args.get('startDate')
        startDate=None
        if startDateStr:
            startDate=datetime.strptime(startDateStr,"%Y-%m-%d")
        else:
            startDate=constant.SystemTimeLimiter.startTime

        endDateStr=request.args.get('endDate')
        endDate=None
        if endDateStr:
            endDate=datetime.strptime(endDateStr,"%Y-%m-%d")
        else:
            endDate=constant.SystemTimeLimiter.endTime

        pageNo=request.args.get('pageNo')
        pageSize=request.args.get('pageSize')
        pager=Pagger(pageNo,pageSize)
        diagnoses=Diagnose.getDiagnoseByPatientUser(db_session,userId,status,pager)
        diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)
        resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
        resultDict=resultStatus.__dict__
        return json.dumps(resultDict,ensure_ascii=False)
    return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)
@uc.route('/hospitaluserReal/diagnose/list',  methods = ['GET', 'POST'])
@authenticated('admin',constant.RoleId.HospitalUserReal)
def getDiagnoseListByHospitaluserReal():
    userId=session['userId']

    if userId:

        pageNo=request.args.get('pageNo')
        pageSize=request.args.get('pageSize')
        pager=Pagger(pageNo,pageSize)
        diagnoses=Diagnose.getDiagnoseByHospitalUserReal(db_session,userId,pager)
        diagnosesDict=dataChangeService.userCenterDiagnoses(diagnoses)
        resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosesDict)
        resultDict=resultStatus.__dict__
        return json.dumps(resultDict,ensure_ascii=False)
    return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)

@uc.route('/diagnose/list/needpay',  methods = ['GET', 'POST'])
def needCallBySupportStaff():
    pageNo=request.args.get('pageNumber')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)
    diagnoses=Diagnose.getDiagnosesBySupportStaff(pager)
    diagnosesDict=dataChangeService.getDiagnoseListByKefu(diagnoses)
    data={}
    data['amount']=0
    if diagnosesDict:
        data['amount']=len(diagnosesDict)
    data['list']=diagnosesDict
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,data)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)



@uc.route('/doctor/<int:doctorId>/patientList',  methods = ['GET', 'POST'])
def getPatients(doctorId):
     patients=Diagnose.getPatientListByDoctorId(doctorId)
     patientsDict=object2dict.objects2dicts(patients)
     resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,patientsDict)
     resultDict=resultStatus.__dict__
     return json.dumps(resultDict,ensure_ascii=False)
@uc.route('/diagnoseTemplate/postionList',  methods = ['GET', 'POST'])
def getPostionList():
    diagnoseMethod=request.args.get('diagnoseMethod')
    diagnosePositions=DiagnoseTemplate.getDiagnosePostion(diagnoseMethod)
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnosePositions)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)
@uc.route('/diagnoseTemplate/diagnoseAndImageDesc',  methods = ['GET', 'POST'])
def getDiagnoseAndImageDescList():
    diagnoseMethod=request.args.get('diagnoseMethod')
    diagnosePostion=request.args.get('diagnosePostion')
    if diagnosePostion:
        diagnosePostion+='\n'
    diagnoseAndImageDescs=DiagnoseTemplate.getDiagnoseAndImageDescs(diagnoseMethod,diagnosePostion)
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,diagnoseAndImageDescs)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)



@uc.route('/userFavorties/add',  methods = ['GET', 'POST'])
def addUserFavorties():
    form = UserFavortiesForm(request.form)
    formResult=form.validate()

    userId=session['userId']
    if userId is None:
        return redirect(LOGIN_URL)

    if formResult.status==rs.SUCCESS.status:
        if UserFavorites.checkUerFavorties(db_session,userId,constant.UserFavoritesType.Doctor,form.doctorId):
            return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)

        userFavorites=UserFavorites.getUerFavortiesByDelStatus(db_session,userId,constant.UserFavoritesType.Doctor,form.doctorId)
        if userFavorites:
            userFavorites.status=constant.ModelStatus.Normal
            db_session.commit()
            return json.dumps(formResult.__dict__,ensure_ascii=False)
        else:
            userFavorites=UserFavorites(userId,form.type,form.doctorId,form.hospitalId,form.docId)
            UserFavorites.save(userFavorites)
            #flash('成功添加诊断评论')
            return json.dumps(formResult.__dict__,ensure_ascii=False)
    return json.dumps(formResult.__dict__,ensure_ascii=False)
@uc.route('/userFavorties/<int:id>/cancel',  methods = ['GET', 'POST'])
def cancleUserFavorties(id):
    UserFavorites.cancleFavorites(id)
    return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
@uc.route('/userFavorties/<int:userId>/list',  methods = ['GET', 'POST'])
def getUserFavorties(userId):
    type=request.args.get('type')
    if type is None:
        json.dumps(rs.PARAM_ERROR.__dict__,ensure_ascii=False)

    type=string.atoi(type)
    userFavorites=UserFavorites.getUserFavorties(userId,type)
    userFavoritesDict=dataChangeService.getUserFavoritiesDict(userFavorites)
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,userFavoritesDict)
    return json.dumps(resultStatus.__dict__,ensure_ascii=False)

@uc.route('/diagnose/<int:diagnoseId>/pdf', methods=['GET','POST'])
def generatorPdf(diagnoseId):

    diagnose=Diagnose.getDiagnoseById(diagnoseId)
    if session.has_key('userId'):
        userId=session['userId']
    if userId is None:
        return redirect('/loginPage')

    resHtml = None

    if UserRole.checkRole(db_session,userId,constant.RoleId.Patient) and Patient.is_patient_under_user(int(userId),diagnose.patientId):
        resHtml = renderHtmlFromDiagnose(diagnose)

    if UserRole.checkRole(db_session,userId,constant.RoleId.Admin) and (int(userId) == diagnose.adminId):
        resHtml = renderHtmlFromDiagnose(diagnose)

    if UserRole.checkRole(db_session,userId,constant.RoleId.Doctor) and (int(userId) == diagnose.doctorId):
        resHtml = renderHtmlFromDiagnose(diagnose)

    if UserRole.checkRole(db_session,userId,constant.RoleId.HospitalUser) and (int(userId) == diagnose.uploadUserId):
        resHtml = renderHtmlFromDiagnose(diagnose)

    if resHtml:
        return resHtml
    else:
        return redirect('/error')

def renderHtmlFromDiagnose(diagnose):
    if hasattr(diagnose,'report'):
        report=diagnose.report
        #edit by lichuan , any one can take a look at the html
        # if diagnose and report and report.status==ReportStatus.Commited and report.type==ReportType.Doctor:
        if diagnose and report:
            data={}
            data['techDesc']=report.techDesc
            data['imageDesc']=report.imageDesc
            if hasattr(diagnose,'diagnoseSeriesNumber'):
                data['diagnoseSN'] = diagnose.diagnoseSeriesNumber
            data['diagnoseDesc']=report.diagnoseDesc
            data['seriesNumber']=report.seriesNumber
            data['fileUrl']=report.fileUrl
            createDate=report.createDate
            if createDate:
                createDate=createDate.strftime('%Y-%m-%d')
                data['createDate']=createDate

            postions=dataChangeService.getDiagnosePositonFromDiagnose(diagnose)
            if postions:
                data['postions']=postions
            if hasattr(diagnose,'patient') and diagnose.patient:
                data['gender']=diagnose.patient.gender
                birthDate=diagnose.patient.birthDate
                if birthDate:
                    birthDate=birthDate.strftime('%Y-%m-%d')
                    data['birthDate']=pdf_utils.getAge(birthDate)
                data['name']=diagnose.patient.realname
            if hasattr(diagnose,'doctor'):
                data['doctorName']=diagnose.doctor.username

            if hasattr(diagnose,'adminId'):
                adminUser = User.getById(diagnose.adminId)
                if adminUser.name:
                    data['adminName']= adminUser.name



            html =  render_template('diagnoseResultPdf.html',data=data)
            # fileName=constant.DirConstant.DIAGNOSE_PDF_DIR+'test.pdf'
            # result = open(fileName, 'wb') # Changed from file to filename
            #
            # pdf = pdf_utils.save_pdf(html,result,diagnoseId,fileName)
            # result.close()
            # return render_template("testpdf.html",getAvatar=getAvatar)
            return html
    return None


@uc.route('/gratitude/create',  methods = ['GET', 'POST'])
def addThankNote():
    form =  ThanksNoteForm(request.form)
    formResult=form.validate()
    userId=session.get('userId')

    #userId='5'
    if userId is None:
        json.dumps(rs.NO_LOGIN.__dict__,ensure_ascii=False)

    userId=string.atoi(userId)
    if formResult.status==rs.SUCCESS.status:
        thanksNote=ThanksNote(userId,form.receiver,form.title,form.content)
        ThanksNote.save(db_session,thanksNote)
        doctor=Doctor.getByUserId(userId)
        if doctor:
            if doctor.thankNoteCount:
                doctor.thankNoteCount+=1
            else:
                doctor.thankNoteCount=1
            Doctor.save(doctor)
        return json.dumps(formResult.__dict__,ensure_ascii=False)
    return json.dumps(formResult.__dict__,ensure_ascii=False)

@uc.route('/gratitude/changestatus',  methods = ['GET', 'POST'])
def changeThankNoteStatus():
    id=request.form.get('id')
    status=request.form.get('status')
    userId=session.get('userId')

    #userId='5'

    # if userId is None:
    #     json.dumps(rs.NO_LOGIN.__dict__,ensure_ascii=False)
    #
    # userId=string.atoi(userId)
    if id and status:
        result=ThanksNote.updateThankNote(id,status)
        return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
    return json.dumps(rs.PARAM_ERROR.__dict__,ensure_ascii=False)


@uc.route('/gratitude/draft/list', methods = ['GET', 'POST'])
def getThanksNotesByDraft():
    #status=request.args.get('status')

    pageNo=request.args.get('pageNo')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)

    thanksNotes=ThanksNote.getThankNoteByDraft(pager)
    if thanksNotes is None or len(thanksNotes)<1:
        return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
    thanksNotesDict=object2dict.objects2dicts(thanksNotes)
    dataChangeService.setThanksNoteDetail(thanksNotesDict)
    data={}
    data['amount']=0
    if thanksNotesDict:
        data['amount']=len(thanksNotesDict)
    data['list']=thanksNotesDict
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,data)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)



@uc.route('/gratitude/<int:userid>/list', methods = ['GET', 'POST'])
def getThanksNotes(userid):
    #status=request.args.get('status')

    pageNo=request.args.get('pageNo')
    pageSize=request.args.get('pageSize')
    pager=Pagger(pageNo,pageSize)

    thanksNotes=ThanksNote.getThanksNoteByReceiver(db_session,userid)
    if thanksNotes is None or len(thanksNotes)<1:
        return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
    thanksNotesDict=object2dict.objects2dicts(thanksNotes)
    dataChangeService.setThanksNoteDetail(thanksNotesDict)
    resultStatus=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,thanksNotesDict)
    resultDict=resultStatus.__dict__
    return json.dumps(resultDict,ensure_ascii=False)
@uc.route('/redirectPdf', methods=['GET','POST'])
def testRedirect():
    #return redirect("/pdf")
    #print url_for('user_center.generatorPdf',diagnoseName='ccheng')
    return redirect(url_for('user_center.generatorPdf',diagnoseId=1))




@uc.route('/account/admin', methods=['GET','POST'])
def updateAcountInfo():
    type=request.form.get('type')
    if type:
        type=string.atoi(type)  #医生：1 病人：2
    else:
        type=2
    userId=None
    if session.has_key('userId'):
        userId=session['userId']
    if userId is None:
        return redirect(LOGIN_URL)
    form=UserUpdateForm(request.form)
    paraRs=form.validate()
    if rs.SUCCESS.status==paraRs.status:
        User.update(userId,form.name,form.account,form.mobile,form.address,form.email,form.identityCode,form.yibaoCard)
        if type==1:
            doctor=Doctor(userId)
            doctor.identityPhone=form.identityPhone
            doctor.username=form.name
            hospitalId=Doctor.update(doctor)
            # if hospitalId:
            #     hospital=Hospital(form.hospitalName)
            #     hospital.id=hospitalId
            #     Hospital.updateHospital(hospital)

        return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)

    return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)

@uc.route('/account/info', methods=['GET','POST'])
def getAcountInfo():
    type=request.args.get('type')
    if type:
        type=string.atoi(type)  #医生：1 病人：2
    else:
        type=2
    userId=None
    if session.has_key('userId'):
        userId=session['userId']
    #userId='5'
    if userId is None:
        return redirect(LOGIN_URL)
    user=User.getById(userId)
    if user:
        userDict=object2dict.to_json(user,user.__class__)
        userDict['mobile']=userDict.get('phone')
        if type==2:
            result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,userDict)
            return json.dumps(result.__dict__,ensure_ascii=False)
        elif type==1:
            userDict=dataChangeService.getAccountInfo(userDict)
            userDict['userName']=userDict.get('name')
            result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,userDict)
            return json.dumps(result.__dict__,ensure_ascii=False)
        else:
            return  json.dumps(rs.PARAM_ERROR.__dict__,ensure_ascii=False)

    return json.dumps(rs.NO_LOGIN.__dict__,ensure_ascii=False)



@uc.route('/account/changePasswd', methods=['GET','POST'])
def changePasswd():
    userId=None
    if session.has_key('userId'):
        userId=session['userId']
    if userId is None:
        return redirect(LOGIN_URL)
    form=UserChangePasswdForm(request.form)
    result=form.validate()
    if result.status==rs.SUCCESS.status:
        user = User.getById(userId)
        if user and user.check_password(form.oldPasswd):
            newHashPasswd=generate_password_hash(form.newPasswd)
            User.update(userId,passwd=newHashPasswd)
            return  json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
        else:
            resultStatus=rs.ResultStatus(rs.FAILURE.status,"未登录或者密码错误")
            return json.dumps(resultStatus.__dict__,ensure_ascii=False)
    return json.dumps(result.__dict__,ensure_ascii=False)
@uc.route('/account/uploadAvatar', methods=['GET','POST'])
def avatarfileUpload():
    userId=None
    userId=request.form.get("userId")
    if session.has_key('userId') and userId is None:
        userId=session['userId']
    if userId is None:
        return redirect(LOGIN_URL)
    userId = string.atoi(userId)
    user=User.getById(userId,None)
    if user is None:
        return  json.dumps(rs.ResultStatus(rs.FAILURE.status,"账户不存在"),ensure_ascii=False )

    try:
        if request.method == 'POST':
            file_infos = []
            files = request.files
            for key, file in files.iteritems():
                if file and isPicture(file.filename):
                    filename = file.filename
                    # file_url = oss_util.uploadFile(diagnoseId, filename)
                    from DoctorSpring.util.oss_util import uploadAvatarFromFileStorage
                    fileurl = uploadAvatarFromFileStorage(userId, filename, file,'',{})
                    if fileurl:
                        user.imagePath=fileurl
                        User.update(userId,imagePath=fileurl)
                        file_infos.append(dict(
                                           name=filename,
                                           url=fileurl))
                        return jsonify(files=file_infos)
                else:
                    return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)
    except Exception,e:
        print e.message
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)
def isPicture(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_PICTURE_EXTENSIONS

@uc.route('/doctor/draftList', methods=['GET','POST'])
def doctorListByDraft():
    try:
        pageNo=request.args.get('pageNumber')
        pageSize=request.args.get('pageSize')
        pager=Pagger(pageNo,pageSize)
        doctors=Doctor.getUserListByStatus(pager)
        doctorsDict=dataChangeService.get_doctors_dict(doctors)
        data={}
        data['amount']=0
        if doctorsDict:
            data['amount']=len(doctorsDict.get('doctor'))
        data['list']=doctorsDict.get('doctor')
        result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,data)
        return json.dumps(result.__dict__,ensure_ascii=False)
    except Exception,e:
        LOG.error(e.message)
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)

@uc.route('/doctor/statuschange', methods=['GET','POST'])
def doctorStatusChange():
    try:
        userid=request.form.get('userId')
        status=request.form.get('status')
        if status:
            status=string.atoi(status)
        else:
            status=constant.ModelStatus.Normal
        doctor=Doctor()
        doctor.userId=userid
        doctor.status=status
        Doctor.update(doctor)
        return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
    except Exception,e:
        LOG.error(e.message)
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)


@uc.route('/user/mobile/sendVerifyCode', methods=['GET','POST'])
def getMobileVerifyCode():
    try:
        from DoctorSpring.util import verify_code,sms_utils
        verifyCode= verify_code.generatorVerifyCode()
        LOG.info("产生验证码")
        session['verifyCode']=verifyCode
        telPhoneNo=None
        userId=session.get('userId')
        diagnoseId=request.args.get('diagnoseId')

        diagnose=Diagnose.getDiagnoseById(diagnoseId)

        if diagnose and hasattr(diagnose,'patient') and diagnose.patient:
            telPhoneNo=diagnose.patient.identityPhone
            if telPhoneNo is None and hasattr(diagnose.patient,'user') and diagnose.patient.user:
                telPhoneNo=diagnose.patient.user.phone
        if telPhoneNo is None:
            user=User.getById(userId)
            telPhoneNo=user.phone
        if telPhoneNo:
            smsRc=sms_utils.RandCode()
            template_param = {'param1':verifyCode}
            smsRc.send_emp_sms(telPhoneNo,smsRc.TEMPLATE_ID_1,json.dumps(template_param))
            return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
        else:
            LOG.error("诊断[%s]发送验证码错误"%diagnoseId)
            return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)

    except Exception,e:
        LOG.error(e.message)
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)


@uc.route('/user/mobile/update', methods=['GET','POST'])
def checkVerifyCode():
    code=request.form.get('verifyCode')
    mobile=request.form.get('mobile')
    verifyCode=session.get('verifyCode')
    userId=session.get('userId')

    if verifyCode is None:
        result=rs.ResultStatus(rs.FAILURE.status,"请重新产生验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)
    if code is None:
        result=rs.ResultStatus(rs.FAILURE.status,"验证码不能为空,请输入验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)
    if code == verifyCode:
        if mobile:
            import re
            #p = re.compile(r"((13|14|15|18)d{9}$)")
            if len(mobile)==11:
                user=User.update(userId,mobile=mobile,isBindPhone=constant.UserPhoneBind.Binded);
                if user:
                    return  json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
                else:
                    result=rs.ResultStatus(rs.FAILURE.status,"更新失败")
                    return  json.dumps(result.__dict__,ensure_ascii=False)
            else:
                result=rs.ResultStatus(rs.FAILURE.status,"输入的电话号码格式有问题")
                return  json.dumps(result.__dict__,ensure_ascii=False)
        else:
            result=rs.ResultStatus(rs.FAILURE.status,"请输入电话号码")
            return  json.dumps(result.__dict__,ensure_ascii=False)
    else:
        result=rs.ResultStatus(rs.FAILURE.status,"验证码错误，请重新输入验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)

@uc.route('/user/mobile/VerifyPhone/<string:phoneNumber>', methods=['GET','POST'])
def getMobileVerifyPhone(phoneNumber=None):
    try:
        telPhoneNo=str(phoneNumber)
        if User.is_existing_phone(telPhoneNo):
            LOG.info("verify success:" + phoneNumber)
            return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
        else:
            result=rs.ResultStatus(rs.FAILURE.status,"电话号码不存在")
            #LOG.info("!!!!" + str(result.__dict__) + "!!!!")
            return  json.dumps(result.__dict__,ensure_ascii=False)

    except Exception,e:
        LOG.error(e.message)
        return json.dumps(rs.FAILURE.__dict__,ensure_ascii=False)


#get and check verify code for forgetPwd
@uc.route('/user/mobile/VerifyCode/<string:phoneNumber>', methods=['GET','POST'])
def getMobileVerifyCodePwd(phoneNumber=None):

    from DoctorSpring.util import verify_code,sms_utils

    telPhoneNo=str(phoneNumber)
    verifyCode= verify_code.generatorVerifyCode()
    LOG.info("产生验证码 to " + phoneNumber)
    #LOG.info(type(str(phoneNumber)))
    session['verifyCode']=verifyCode

    smsRc=sms_utils.RandCode()
    template_param = {'param1':verifyCode}
    smsRc.send_emp_sms(telPhoneNo,smsRc.TEMPLATE_ID_1,json.dumps(template_param))
    return json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)


@uc.route('/user/mobile/update/<string:phoneNumber>', methods=['GET','POST'])
def checkVerifyCodePwd(phoneNumber=None):
    code=request.form.get('verifyCode')
    mobile=phoneNumber
    verifyCode=session.get('verifyCode')
    user_id = User.get_id_by_phone(mobile)[0]
    userId = str(int(user_id))

    if verifyCode is None:
        result=rs.ResultStatus(rs.FAILURE.status,"请重新产生验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)
    if code is None:
        result=rs.ResultStatus(rs.FAILURE.status,"验证码不能为空,请输入验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)
    if code == verifyCode:
        return  json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)
    else:
        result=rs.ResultStatus(rs.FAILURE.status,"验证码错误，请重新输入验证码")
        return  json.dumps(result.__dict__,ensure_ascii=False)

#reset password in forgetPwd
@uc.route('/account/resetPasswd/<string:mobileNumber>', methods=['GET','POST'])
def resetPasswd(mobileNumber):
    userId=str(int(User.get_id_by_phone(mobileNumber)[0]))
    form=UserResetPasswdForm(request.form)
    result=form.validate()
    if result.status==rs.SUCCESS.status:
        user = User.getById(userId)
        newHashPasswd=generate_password_hash(form.newPasswd)
        User.update(userId,passwd=newHashPasswd)
    return  json.dumps(rs.SUCCESS.__dict__,ensure_ascii=False)


@uc.route('/pay/<string:alipayHashcode>', methods=['GET','POST'])
def redirectAlipay(alipayHashcode):
    alipayUrl=Diagnose.getAlipayUrl(alipayHashcode)
    if alipayUrl is None:
        return redirect(ERROR_URL)
    #return redirect("/pdf")
    #print url_for('user_center.generatorPdf',diagnoseName='ccheng')
    return redirect(alipayUrl[0])

@uc.route('/hospital/list', methods=['GET','POST'])
def getAllHospitalList():
    hospitals=Hospital.getAllHospitals(db_session)
    hospitalsDict=dataChangeService.getAllHospital(hospitals)
    result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,hospitalsDict)
    return  json.dumps(result.__dict__,ensure_ascii=False)

@uc.route('/department/list', methods=['GET','POST'])
def getAllDepartmentlList():
    departments=Department.getAllDepartments()
    departmentsDict=dataChangeService.getAllDepartments(departments)
    result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,departmentsDict)
    return  json.dumps(result.__dict__,ensure_ascii=False)

@uc.route('/skill/list', methods=['GET','POST'])
def getAllSkillList():
    skills=Skill.getSkills()
    skillsDict=dataChangeService.getAllSkills(skills)
    result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,skillsDict)
    return  json.dumps(result.__dict__,ensure_ascii=False)


@uc.route('/doctor/updateinfo', methods=['GET','POST'])
def updateDoctorInfo():
    form=DoctorUpdateForm(request.form)
    doctor=Doctor(form.userId)
    doctor.departmentId=form.department
    doctor.hospitalId=form.hospital
    doctor.status=form.status
    doctor.title=form.title
    Doctor.update(doctor)
    doctor=Doctor.getByUserId(form.userId)

    if doctor:
        for skill in form.skills:
            doctorsKill=Doctor2Skill(doctor.id,skill)
            Doctor2Skill.save(doctorsKill)
    User.update(form.userId,status=constant.ModelStatus.Normal)
    result=rs.ResultStatus(rs.SUCCESS.status,rs.SUCCESS.msg,None)
    return  json.dumps(result.__dict__,ensure_ascii=False)