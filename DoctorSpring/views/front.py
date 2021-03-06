# coding: utf-8
__author__ = 'Jeremy'

import os.path
import config
from config import LOGIN_URL
import data_change_service as dataChangeService
from flask import request, redirect, url_for, Blueprint, jsonify,json, g, send_from_directory, session
from flask import abort, render_template, flash
from flask_login import login_required
from DoctorSpring.models import Doctor, Hospital, Location, Skill, User, Position, Patient, Diagnose, Pathology, PathologyPostion, File, DiagnoseLog, Comment,UserRole,Message,AlipayLog
from database import db_session
from werkzeug.utils import secure_filename
from forms import DiagnoseForm1, DoctorList, DiagnoseForm2, DiagnoseForm3, DiagnoseForm4
from DoctorSpring.util import result_status as rs, object2dict, constant, oss_util ,sms_utils
from datetime import datetime, date
from DoctorSpring.util.constant import PatientStatus, Pagger, DiagnoseStatus, ModelStatus, FileType, DiagnoseLogAction, RoleId, UserStatus
from DoctorSpring.util.authenticated import authenticated
from DoctorSpring.util.result_status import *
from DoctorSpring.util.pay import alipay
import random
import string
from config import LOGIN_URL,ERROR_URL

from DoctorSpring import app
LOG=app.logger

config = config.rec()
front = Blueprint('front', __name__)

@front.route('/', methods=['GET', 'POST'])
def index():
    return redirect('/homepage')

@front.route('/homepage', methods=['GET', 'POST'])
def homepage():

    resultData={}
    pager = Pagger(1, 6)
    doctors = Doctor.get_doctor_list(0, 0, "", pager)
    doctorsList = dataChangeService.get_doctors_dict(doctors)
    resultData['doctorlist'] = doctorsList
    if len(doctorsList['doctor']) > 0:
        resultData['doctor'] = doctorsList['doctor'][0]
    diagnoseComments=Comment.getRecentComments()
    if diagnoseComments  and  len(diagnoseComments)>0:
        diagnoseCommentsDict=object2dict.objects2dicts_2(diagnoseComments)
        dataChangeService.setDiagnoseCommentsDetailInfo(diagnoseCommentsDict)
        resultData['comments']=diagnoseCommentsDict
    else:
        resultData['comments']=None

    resultData['ishomepage']=True
    if session.has_key('userId'):
        userId=session['userId']
        messageCount=Message.getMessageCountByReceiver(userId)
        resultData['messageCount']=messageCount
        if UserRole.checkRole(db_session,userId,constant.RoleId.Patient):
            resultData['isPatient'] = True

    return render_template("home.html", data=resultData)

@front.route('/applyDiagnose', methods=['GET', 'POST'])
def applyDiagnose():

    if session.has_key('userId'):
        userId=session['userId']
    if userId is None:
        return redirect('/loginPage')

    data = {}
    hospitals = Hospital.getAllHospitals(db_session)
    hospitalsDict = object2dict.objects2dicts(hospitals)
    data['hospitals'] = hospitalsDict

    positions = Position.getPositions()
    positionsDict = object2dict.objects2dicts(positions)
    data['positions'] = positionsDict

    locations = Location.getAllLocations(db_session)
    locationsDict = object2dict.objects2dicts(locations)
    data['locations'] = locationsDict

    #hospital user
    if 'type' in request.args.keys():
        data['type'] = int(request.args.get('type'))
    if 'edit' in request.args.keys() and 'diagnoseid' in request.args.keys():
        new_diagnose = Diagnose.getDiagnoseById(request.args['diagnoseid'])
        data['edit'] = 1
    else:
        new_diagnose = Diagnose.getNewDiagnoseByStatus(ModelStatus.Draft, session['userId'])

    if new_diagnose is not None:
        data['doctor'] = new_diagnose.doctor
        data['patient'] = new_diagnose.patient
        data['pathology'] = new_diagnose.pathology

        new_file = File.getFiles(new_diagnose.pathologyId, constant.FileType.Dicom)
        data['dicomfile'] = new_file
        new_files = File.getFiles(new_diagnose.pathologyId, constant.FileType.FileAboutDiagnose)
        data['fileAboutDiagnose'] = new_files

        pathologyPositions = []
        if hasattr(new_diagnose, 'pathology') and hasattr(new_diagnose.pathology, 'pathologyPostions'):
            pathologyPositions = object2dict.objects2dicts(new_diagnose.pathology.pathologyPostions)
        data['pathologyPositions'] = pathologyPositions


    patients = Patient.get_patient_by_user(session['userId'])
    if patients is None or len(patients) < 1:
        patientdict = []
    else:
        patientdict = object2dict.objects2dicts(patients)

    data['patientdict'] = patientdict

    return render_template("applyDiagnose.html", result=data)


def checkFilesExisting(new_diagnose):
    dicomCount = File.getFileCountbypathologyId(new_diagnose.pathologyId, FileType.Dicom)
    if dicomCount > 0:
        otherCount = File.getFileCountbypathologyId(new_diagnose.pathologyId, FileType.FileAboutDiagnose)
        if otherCount>0:
            return True
    return False


@front.route('/save/diagnose/<formid>', methods=['GET', 'POST'])
def applyDiagnoseForm(formid):
    if (int(formid) == 1) :
        form = DiagnoseForm3(request.form)
        form_result = form.validate()
        if form_result.status == rs.SUCCESS.status:
            if(form.diagnoseId):
                new_diagnose = Diagnose.getDiagnoseById(form.diagnoseId)
            else:
                new_diagnose = Diagnose.getNewDiagnoseByStatus(DiagnoseStatus.Draft, session['userId'])
            if(new_diagnose is None):
                new_diagnose = Diagnose()
                new_diagnose.status = DiagnoseStatus.Draft

            new_diagnose.doctorId = form.doctorId
            new_diagnose.uploadUserId = session['userId']

            Diagnose.save(new_diagnose)
            form_result.data = {'formId': 2, 'diagnoseId': new_diagnose.id}
        return jsonify(form_result.__dict__)
    elif (int(formid) == 2) :
        form = DiagnoseForm1(request.form)
        form_result = form.validate()
        if form_result.status == rs.SUCCESS.status:
            if form.diagnoseId is not None:
                new_diagnose = Diagnose.getDiagnoseById(form.diagnoseId)
            else:
                new_diagnose = Diagnose.getNewDiagnoseByStatus(DiagnoseStatus.Draft, int(session['userId']))
            if(new_diagnose is not None):
                needcreateNewUserByHospitalUser=True
                # 去拿没有draft的用户
                if(form.exist):
                    #select exist patient , from list, when modify exist diagnose
                    new_patient = Patient.get_patient_by_id(form.patientid)
                else:
                    #update draft patient when modify exist diagnose
                    new_patient = Patient.getPatientDraftByPatienId(new_diagnose.patientId)
                    if new_patient:
                        new_patient.realname = form.patientname
                        new_patient.gender = form.patientsex
                        new_patient.birthDate = datetime.strptime(form.birthdate, "%Y-%m-%d")
                        new_patient.identityCode = form.identitynumber
                        new_patient.locationId = form.locationId
                        new_patient.identityPhone = form.phonenumber
                        Patient.save(new_patient)
                        needcreateNewUserByHospitalUser=False
                #create a new patient
                if new_patient is None:
                    new_patient = Patient()
                    new_patient.type = PatientStatus.diagnose
                    new_patient.userID = session['userId']
                    new_patient.realname = form.patientname
                    new_patient.gender = form.patientsex
                    new_patient.birthDate = datetime.strptime(form.birthdate, "%Y-%m-%d")
                    new_patient.identityCode = form.identitynumber
                    new_patient.locationId = form.locationId
                    new_patient.identityPhone = form.phonenumber
                    new_patient.status = ModelStatus.Draft
                    # new_patient.locationId = form.location
                    Patient.save(new_patient)
                new_diagnose.patientId = new_patient.id
                Diagnose.save(new_diagnose)

                # Hospital User 注册用户
                if form.isHospitalUser and (not form.exist) and needcreateNewUserByHospitalUser:
                    userQuery = User.getByPhone(form.phonenumber)
                    if userQuery.count() <= 0:
                        passwd=random.sample('zyxwvutsrqponmlkjihgfedcba1234567890',6)
                        passwd = ''.join(passwd)
                        new_user = User(form.patientname,form.phonenumber, passwd, True)
                        new_user.type = UserStatus.patent
                        new_user.status = ModelStatus.Normal
                        User.save(new_user)
                        new_patient.userID = new_user.id
                        Patient.save(new_patient)
                        new_userrole = UserRole(new_user.id, RoleId.Patient)
                        UserRole.save(new_userrole)
                        sendRegisterMobileMessage(session.get('userId'),new_diagnose,new_user.phone,passwd)
                    else:
                        new_patient.userID = userQuery.first().id
                        Patient.save(new_patient)
                form_result.data = {'formId': 3, }
            else:
                form_result = ResultStatus(FAILURE.status, "找不到第一步草稿")
        return jsonify(form_result.__dict__)
    elif (int(formid) == 3):
        form = DiagnoseForm2(request.form)
        form_result = form.validate()
        if form_result.status == rs.SUCCESS.status:

            if form.diagnoseId is not None:
                new_diagnose = Diagnose.getDiagnoseById(form.diagnoseId)
            else:
                new_diagnose = Diagnose.getNewDiagnoseByStatus(DiagnoseStatus.Draft, int(session['userId']))

            if new_diagnose is not None:
                #直接选择的病例，不是新建或者更改
                isExistingPathology=False
                if form.exist:
                    new_pathology = Pathology.getById(form.pathologyId)
                    isExistingPathology=True
                elif new_diagnose.pathologyId:
                    new_pathology = Pathology.getById(new_diagnose.pathologyId)
                else:
                    new_pathology = Pathology.getByPatientStatus(session['userId'], ModelStatus.Draft)

                if new_pathology is None:
                    new_pathology = Pathology(new_diagnose.patientId)
                if not isExistingPathology:
                    new_pathology.diagnoseMethod = form.dicomtype
                    new_pathology.status = ModelStatus.Draft
                    new_pathology.save(new_pathology)

                    PathologyPostion.deleteByPathologyId(new_pathology.id)
                    for position in form.patientlocation:
                        new_position_id = PathologyPostion(new_pathology.id, position)
                        PathologyPostion.save(new_position_id)

                    File.cleanDirtyFile(form.fileurl, new_pathology.id, FileType.Dicom)
                    if form.fileurl and len(form.fileurl) > 0:
                        for fileurl in form.fileurl:
                            new_file = File.getFilebyId(int(fileurl))
                            new_file.pathologyId = new_pathology.id
                            File.save(new_file)
                new_diagnose.pathologyId = new_pathology.id
                Diagnose.save(new_diagnose)
                form_result.data = {'formId': 4}
            else:
                form_result = ResultStatus(FAILURE.status, "找不到上步的草稿")
        return jsonify(form_result.__dict__)
    elif (int(formid) == 4):
        form = DiagnoseForm4(request.form)
        form_result = form.validate()
        if form_result.status == rs.SUCCESS.status:
            if form.diagnoseId is not None:
                new_diagnose = Diagnose.getDiagnoseById(form.diagnoseId)
            else:
                new_diagnose = Diagnose.getNewDiagnoseByStatus(DiagnoseStatus.Draft, int(session['userId']))
            if(new_diagnose is not None):
                new_pathology = Pathology.getById(new_diagnose.pathologyId)
                if(new_pathology is not None):
                    new_pathology.caseHistory = form.illnessHistory
                    new_pathology.hospitalId = form.hospitalId
                    new_pathology.status = ModelStatus.Normal
                    Pathology.save(new_pathology)

                    File.cleanDirtyFile(form.fileurl, new_pathology.id, FileType.FileAboutDiagnose)
                    if form.fileurl and len(form.fileurl) > 0:
                        for fileurl in form.fileurl:
                            new_file = File.getFilebyId(int(fileurl))
                            new_file.pathologyId = new_pathology.id
                            File.save(new_file)

                    new_patient = Patient.get_patient_by_id(new_diagnose.patientId)
                    new_patient.status = PatientStatus.diagnose
                    #add for need update scenario
                    if new_diagnose.status == constant.DiagnoseStatus.NeedUpdate:
                        new_diagnoselog = DiagnoseLog(new_diagnose.uploadUserId, new_diagnose.id, DiagnoseLogAction.DiagnoseNeedUpateRecommitAction)
                        DiagnoseLog.save(db_session, new_diagnoselog)
                        new_diagnose.status = DiagnoseStatus.Triaging
                        Diagnose.save(new_diagnose)
                    #hospitalUser type=1
                    else:
                        if form.type=='1' and not checkFilesExisting(new_diagnose):
                            new_diagnoselog = DiagnoseLog(new_diagnose.uploadUserId, new_diagnose.id, DiagnoseLogAction.NewDiagnoseAction)
                            DiagnoseLog.save(db_session, new_diagnoselog)
                            #update by lichuan , save diagnose and change to needPay
                            new_diagnose.status = DiagnoseStatus.HospitalUserDiagnoseNeedCommit
                            Diagnose.save(new_diagnose)
                            #end update
                        else:
                            #产生alipay，发送短消息
                            userId= session.get('userId')


                            new_diagnose.ossUploaded=constant.DiagnoseUploaed.Uploaded
                            new_diagnose.status = DiagnoseStatus.NeedPay

                            Diagnose.save(new_diagnose)
                            sendAllMessage(userId,new_diagnose)




                else:
                    form_result = ResultStatus(FAILURE.status, "找不到上步的草稿1")
            else:
                form_result = ResultStatus(FAILURE.status, "找不到上步的草稿2")
        form_result.data = {'isFinal': True}
        return jsonify(form_result.__dict__)
    else:
        return jsonify(ResultStatus(FAILURE.status, "错误的表单号").__dict__)

UPLOAD_FOLDER = 'DoctorSpring/static/tmp/'
ALLOWED_EXTENSIONS = set(['doc', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'html', 'zip', 'rar'])
#upload file ,which will be used by hospitaluser ,even more hositaluser not use it where apply diagnose
@front.route('/file/upload', methods=['POST'])
def fileUpload():
    userId=session.get('userId')
    if userId is None:
        return redirect(LOGIN_URL)
    userId=string.atoi(userId)
    type=request.form.get('type')
    diagnoseId=request.form.get("diagnoseId")
    if diagnoseId is None:
        return jsonify({'code': 1,  'message' : "error", 'data': ''})
    diagnoseId=string.atoi(diagnoseId)
    if type:
        type=string.atoi(type)
    else:
        type=constant.FileType.Dicom
    try:
        diagnose=Diagnose.getDiagnoseById(diagnoseId)
        if diagnose and diagnose.pathologyId:
            file_infos = []
            files = request.files
            for key, file in files.iteritems():
                if file and allowed_file(file.filename):
                    filename = file.filename
                    extension=getFileExtension(filename)
                    # file_url = oss_util.uploadFile(diagnoseId, filename)
                    from DoctorSpring.util.oss_util import uploadFileFromFileStorage,size,getFileName
                    fileurl = uploadFileFromFileStorage(diagnoseId, filename, file,'',{},extension)

                    newFileName=getFileName(diagnoseId,filename,extension)
                    size=size(newFileName)
                    new_file = File(type, filename,size, fileurl,diagnose.pathologyId)
                    File.save(new_file)

                    if  type==FileType.Dicom:
                        filesAboutDiagnose=File.getFiles(diagnose.pathologyId,FileType.FileAboutDiagnose)
                        if filesAboutDiagnose and len(filesAboutDiagnose)>0:
                            diagnoseChange=Diagnose()
                            diagnoseChange.id=diagnoseId
                            diagnoseChange.ossUploaded=constant.DiagnoseUploaed.Uploaded
                            #diagnoseChange.status=constant.DiagnoseStatus.NeedPay
                            diagnose.uploadUserId=userId
                            Diagnose.update(diagnoseChange)
                            #sendAllMessage(userId,diagnose)需要提交了才能发信息h
                            new_diagnoselog = DiagnoseLog(diagnose.uploadUserId, diagnose.id, DiagnoseLogAction.NewDiagnoseAction)
                            DiagnoseLog.save(db_session, new_diagnoselog)
                    if type==FileType.FileAboutDiagnose:
                        filesAboutDiagnose=File.getFiles(diagnose.pathologyId,FileType.Dicom)
                        if filesAboutDiagnose and len(filesAboutDiagnose)>0:
                            diagnoseChange=Diagnose()
                            diagnoseChange.id=diagnoseId
                            diagnoseChange.ossUploaded=constant.DiagnoseUploaed.Uploaded
                            #diagnoseChange.status=constant.DiagnoseStatus.NeedPay
                            diagnose.uploadUserId=userId
                            Diagnose.update(diagnoseChange)
                            #sendAllMessage(userId,diagnose)
                            new_diagnoselog = DiagnoseLog(diagnose.uploadUserId, diagnose.id, DiagnoseLogAction.NewDiagnoseAction)
                            DiagnoseLog.save(db_session, new_diagnoselog)


                    file_infos.append(dict(id=new_file.id,
                                           name=filename,
                                           size=size,
                                           url=fileurl))
                else:
                    return jsonify({'code': 1,  'message' : "error", 'data': ''})
            return jsonify(files=file_infos)
    except Exception,e:
        LOG.error( e.message)
        return jsonify({'code': 1,  'message' : "上传出错", 'data': ''})
@front.route('/file/<int:filetype>/delete', methods=['POST'])
def diagnosefileUpload(filetype):
    userId=session.get('userId')
    diagnoseId=request.args.get('diagnoseId')
    diagnose=Diagnose.getDiagnoseById(diagnoseId)
    if diagnose and userId:
        userId=string.atoi(userId)
        if diagnose.uploadUserId==userId:
            File.deleteFileByPathologyId(diagnose.pathologyId,filetype)

#包括诊断消息,和发短信
def sendAllMessage(userId,diagnose):
    new_diagnoselog = DiagnoseLog(diagnose.uploadUserId, diagnose.id, DiagnoseLogAction.NewDiagnoseAction)
    DiagnoseLog.save(db_session, new_diagnoselog)
    payUrl=generateAliPay(userId,diagnose.id,diagnose)
    if payUrl:
        sendMobileMessage(userId,diagnose.id,diagnose,payUrl)
        #诊断通知
        content=dataChangeService.getPatienDiagnoseMessageContent(diagnose,"您好系统中有一个诊断需要支付才能继续进行，请先支付")
        message=Message(constant.DefaultSystemAdminUserId,userId,'诊断通知',content,constant.MessageType.Diagnose)
        message.url=payUrl
        Message.save(message)
#增加参数diagnose的目的是减少对数据库的请求
def generateAliPay(userId,diagnoseId,diagnose=None):

    if diagnoseId:
        diagnose=Diagnose.getDiagnoseById(diagnoseId)
    else:
        diagnose=Diagnose.getDiagnoseById(diagnose.id)

    if diagnoseId is None and diagnose:
        diagnoseId =  diagnose.id
    if userId is None:
        LOG.warn("诊断生成阿里支付地址出错,用户未登录")

    if isinstance(userId,basestring):
        userId=string.atoi(userId)
    if diagnose is None:
        LOG.error("诊断[diagnoseId=%d]生成阿里支付地址出错,诊断在系统中不存在"%diagnoseId)

    if diagnose and diagnose.uploadUserId!=userId:
        if hasattr(diagnose,'patient') and userId != diagnose.patient.userID:
            LOG.error("诊断[diagnoseId=%d][userId=%d]生成阿里支付地址出错,用户没有权限"%(diagnoseId,userId))

    if diagnose and diagnose.status==constant.DiagnoseStatus.NeedPay and diagnose.ossUploaded==constant.DiagnoseUploaed.Uploaded:
        alipayLog=AlipayLog(userId,diagnoseId,constant.AlipayLogAction.StartApplyAlipay)
        AlipayLog.save(alipayLog)
        description=None
        needPay=None
        if hasattr(diagnose,'pathology') and hasattr(diagnose.pathology,'pathologyPostions'):
            if len(diagnose.pathology.pathologyPostions)>0:
                if diagnose.pathology.diagnoseMethod==constant.DiagnoseMethod.Mri:
                    needPay=diagnose.getPayCount(constant.DiagnoseMethod.Mri,len(diagnose.pathology.pathologyPostions),diagnose.getUserDiscount(diagnose.patientId))
                elif diagnose.pathology.diagnoseMethod==constant.DiagnoseMethod.Ct:
                    needPay=diagnose.getPayCount(constant.DiagnoseMethod.Ct,len(diagnose.pathology.pathologyPostions),diagnose.getUserDiscount(diagnose.patientId))
            else:
                result=rs.ResultStatus(rs.FAILURE.status,"诊断不存在或这状态不对")
                return  json.dumps(result.__dict__,ensure_ascii=False)
        else:
            result=rs.ResultStatus(rs.FAILURE.status,"诊断不存在或这状态不对")
            return  json.dumps(result.__dict__,ensure_ascii=False)

        if hasattr(diagnose,'doctor') and hasattr(diagnose.doctor,'username'):

            description=' 医生(%s)的诊断费用:%f 元'%(diagnose.doctor.username,needPay)
            if hasattr(diagnose.doctor.hospital,'name'):
                description=diagnose.doctor.hospital.name+description
        payUrl=alipay.create_direct_pay_by_user(diagnose.diagnoseSeriesNumber,diagnose.diagnoseSeriesNumber,'咨询费',needPay)
        if payUrl:
            alipayLog=AlipayLog(userId,diagnoseId,constant.AlipayLogAction.GetAlipayUrl)
            alipayLog.description=description
            alipayLog.payUrl=payUrl
            AlipayLog.save(alipayLog)

            updateDiagnose(diagnose.id,payUrl)
            LOG.info("诊断[diagnoseId=%d][userId=%d]生成阿里支付地址成功"%(diagnoseId,userId))
            return payUrl
        else:
            alipayLog=AlipayLog(userId,diagnoseId,constant.AlipayLogAction.GetAlipayUrlFailure)
            AlipayLog.save(alipayLog)

            LOG.error("诊断[diagnoseId=%d][userId=%d]生成阿里支付地址出错,去阿里获取的payurl为空"%(diagnoseId,userId))
    LOG.error("诊断[diagnoseId=%d][userId=%d]生成阿里支付地址出错,其他未知原因"%(diagnoseId,userId))
def updateDiagnose(diagnoseId,alipayUrl):
    if diagnoseId:
        diagnose=Diagnose()
        diagnose.id=diagnoseId
        diagnose.alipayUrl=alipayUrl
        diagnose.alipayHashCode=getAlipayHashCode()
        Diagnose.update(diagnose)
def getAlipayHashCode():
    from DoctorSpring.util.verify_code import generatorAlipayHashCode
    alipayHashcode= generatorAlipayHashCode()
    if Diagnose.existAlipayHashCode(alipayHashcode):
        alipayHashcode=getAlipayHashCode()
    return alipayHashcode

def sendMobileMessage(userId,diagnoseId,diagnose=None,message=None):
    telPhoneNo=None

    if diagnoseId:
        diagnose=Diagnose.getDiagnoseById(diagnoseId)
    else:
        diagnose=Diagnose.getDiagnoseById(diagnose.id)

    if diagnose and hasattr(diagnose,'patient') and diagnose.patient:
        telPhoneNo=diagnose.patient.identityPhone
        if telPhoneNo is None and hasattr(diagnose.patient,'user') and diagnose.patient.user:
             telPhoneNo=diagnose.patient.user.phone
    if telPhoneNo is None:
        user=User.getById(userId)
        telPhoneNo=user.phone
    if telPhoneNo:
        smsRc=sms_utils.RandCode()
        param1=diagnose.diagnoseSeriesNumber
        param3=constant.MobileMessageConstant.UrlPrefix+diagnose.alipayHashCode
        param4=constant.MobileMessageConstant.KefuPhone
        from DoctorSpring.util.helper import getPayCountByDiagnoseId
        param2=getPayCountByDiagnoseId(diagnose.id)
        template_param = {'param1':param1,'param2':param2,'param3':param3,'param4':param4}
        smsRc.send_emp_sms(telPhoneNo,smsRc.TEMPLATE_PAY,json.dumps(template_param))

def sendRegisterMobileMessage(userId,diagnose,phoneNumber,passwd):
    if userId and diagnose:
        new_diagnoselog = DiagnoseLog(userId, diagnose.id, DiagnoseLogAction.SendMessageToUser)
        DiagnoseLog.save(db_session, new_diagnoselog)
    if phoneNumber:
        smsRc=sms_utils.RandCode()
        template_param = {'param1':passwd}
        smsRc.send_emp_sms(phoneNumber,smsRc.TEMPLATE_REGISTER,json.dumps(template_param))

@front.route('/file/disable', methods=['POST','GET'])
@login_required
def disableFile():
    try:
        disgnoseId=request.form.get('diagnoseId')
        type=request.form.get('type')
        if disgnoseId is None :
            disgnoseId=string.atoi(disgnoseId)
        if type is None:
            type=constant.FileType.Dicom
        else:
            type=string.atoi(type)
        diagnose=Diagnose.getDiagnoseById(disgnoseId)
        if diagnose and diagnose.pathologyId:
            pathologyId=diagnose.pathologyId
            result=File.deleteFileByPathologyId(pathologyId,type)
            if result>0:
                diagnose.ossUploaded = constant.DiagnoseUploaed.NoUploaded
                Diagnose.save(diagnose)
                return jsonify(rs.SUCCESS.__dict__, ensure_ascii=False)
        return jsonify(rs.FAILURE.__dict__, ensure_ascii=False)


    except Exception,e:
        LOG.error( e.message)
        return redirect(ERROR_URL)



@front.route('/dicomfile/upload', methods=['POST'])
def dicomfileUpload():
    diagnoseId=request.form.get('diagnoseId')
    if diagnoseId is None:
        return jsonify({'code': 1,  'message' : "error", 'data': ''})
    diagnoseId = string.atoi(diagnoseId)
    try:
        if request.method == 'POST':
            file_infos = []
            files = request.files
            for key, file in files.iteritems():
                if file and allowed_file(file.filename):
                    filename = file.filename
                    extension=getFileExtension(filename)
                    # file_url = oss_util.uploadFile(diagnoseId, filename)
                    from DoctorSpring.util.oss_util import uploadFileFromFileStorage,getFileName,size
                    fileurl = uploadFileFromFileStorage(diagnoseId, filename, file,'',{},extension)

                    newFileName=getFileName(diagnoseId,filename,extension)
                    size=size(newFileName)

                    new_file = File(FileType.Dicom, filename, size, fileurl,None)
                    File.save(new_file)


                    file_infos.append(dict(id=new_file.id,
                                           name=filename,
                                           size=size,
                                           url=fileurl))
                else:
                    return jsonify({'code': 1,  'message' : "error", 'data': ''})
            return jsonify(files=file_infos)
    except Exception,e:
        print e.message
        return jsonify({'code': 1,  'message' : "error", 'data': ''})

@front.route('/patientreport/upload', methods=['POST'])
@login_required
def patientReportUpload():
    diagnoseId=request.form.get('diagnoseId')
    if diagnoseId is None:
        return jsonify({'code': 1,  'message' : "error", 'data': ''})
    diagnoseId = string.atoi(diagnoseId)
    try:
        if request.method == 'POST':
            file_infos = []
            files = request.files
            for key, file in files.iteritems():
                if file and allowed_file(file.filename):
                    filename = file.filename
                    extension=getFileExtension(filename)
                    # file_url = oss_util.uploadFile(diagnoseId, filename)
                    from DoctorSpring.util.oss_util import uploadFileFromFileStorage,getFileName,size
                    fileurl = uploadFileFromFileStorage(diagnoseId, filename, file,'',{},extension)

                    newFileName=getFileName(diagnoseId,filename,extension)
                    size=size(newFileName)
                    new_file = File(FileType.FileAboutDiagnose, filename, size , fileurl,None)
                    File.save(new_file)

                    file_infos.append(dict(id=new_file.id,
                                           name=filename,
                                           size=size,
                                           url=fileurl))

                else:
                    return jsonify({'code': 1,  'message' : "error", 'data': ''})
            return jsonify(files=file_infos)
    except Exception,e:
        print e.message
        return jsonify({'code': 1,  'message' : "error", 'data': ''})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def getFileExtension(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1]

@front.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER,
                               filename)



@front.route('/doctors/list.json')
# /doctors/list.json?hospitalId=1&sectionId=0&doctorname=ddd&pageNumber=1&pageSize=6
def doctor_list_json():
    form = DoctorList(request)
    form_result = form.validate()
    if form_result.status == rs.SUCCESS.status:
        pager = Pagger(form.pageNumber, form.pageSize)
        pager.count = Doctor.get_doctor_count(form.hospitalId, form.sectionId, form.doctorname, pager)
        doctors = Doctor.get_doctor_list(form.hospitalId, form.sectionId, form.doctorname, pager)
        if doctors is None or len(doctors) < 1:
            return jsonify(rs.SUCCESS.__dict__, ensure_ascii=False)
        doctorsDict = dataChangeService.get_doctors_dict(doctors, form.pageNumber, pager.count/pager.pageSize+1)
        resultStatus = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, doctorsDict)
        return jsonify(resultStatus.__dict__, ensure_ascii=False)
    return jsonify(FAILURE)


@front.route('/patient/<int:patientId>/listExtendFiles.json')
# /doctors/list.json?hospitalId=1&sectionId=0&doctorname=ddd&pageNumber=1&pageSize=6
def getPatientFile(patientId):
    userId=None
    if session.has_key('userId'):
        userId=session['userId']
    if userId is None:
        return redirect(LOGIN_URL)

    if patientId is None or patientId<0 :
        return  jsonify(FAILURE)
    patient=Patient.get_patient_by_id(patientId)
    if patient is None or patient.userID!=string.atoi(userId):
        return  jsonify(FAILURE)

    pathologs=Pathology.getByPatientId(patientId)
    files=[]
    if pathologs and len(pathologs)>0:
       for patholog in pathologs:
           files.extend(File.getFilebypathologyId(patholog.id),constant.FileType.FileAboutDiagnose)
    fileResults=None
    if len(files)>0:
        fileResults=dataChangeService.getFilesResult(files)
    resultStatus = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, fileResults)
    return jsonify(resultStatus.__dict__)

@front.route('/doctor/recommanded')
def doctor_rec():

    doctor = None

    if 'doctorId' in request.args.keys():
        doctorId = request.args['doctorId']
        doctor = Doctor.get_doctor(doctorId,"")
    elif 'diagnoseId' in request.args.keys():
        diagnoseId = int(request.args['diagnoseId'])
        diagnose = Diagnose.getDiagnoseById(diagnoseId)
        if diagnose is not None:
            doctor = diagnose.doctor
    else:
        doctor = Doctor.get_doctor(0, True)

    if doctor is None:
        return jsonify(rs.SUCCESS.__dict__, ensure_ascii=False)
    doctors_dict = dataChangeService.get_doctor(doctor)
    resultStatus = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, doctors_dict)
    return jsonify(resultStatus.__dict__, ensure_ascii=False)


@front.route('/doctor/list')
def doctor_list():
    result = {}
    hospitals = Hospital.getAllHospitals(db_session)
    hospitalsDict = object2dict.objects2dicts(hospitals)
    result['hospitals'] = hospitalsDict

    skills = Skill.getSkills()
    skillsDict = object2dict.objects2dicts(skills)
    result['skills'] = skillsDict
    result['isdoctorlist'] = True
    return render_template("doctorList.html", data=result)


@front.route('/patient/profile.json')
def patient_profile():
    if 'patientId' in request.args.keys():
        patientId = request.args['patientId']
        patient = Patient.get_patient_by_id(patientId)
        resultStatus = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, patient.__dict__)
        if patient is None:
            return jsonify(resultStatus.__dict__)
        resultStatus.data = dataChangeService.get_patient(patient)
        return jsonify(resultStatus.__dict__)
    return jsonify(SUCCESS.__dict__)


@front.route('/pathlogy/list.json')
def pathlogy_list():
    if 'patientId' in request.args.keys():
        patientId = request.args['patientId']
        pathlogys = Pathology.getByPatientId(patientId)
        if pathlogys is None or len(pathlogys) < 1:
            return jsonify(rs.SUCCESS.__dict__, ensure_ascii=False)
        pathlogysDict = dataChangeService.get_pathology_list(pathlogys)
        resultStatus = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, pathlogysDict)
        return jsonify(resultStatus.__dict__, ensure_ascii=False)
    return jsonify(SUCCESS.__dict__)


@front.route('/pathlogy/dicominfo.json')
def get_pathology():
    if 'pathologyId' in request.args.keys():
        new_pathology = Pathology.getById(request.args['pathologyId'])
        if new_pathology is not None:
            pathologyDict = dataChangeService.get_pathology(new_pathology)
            result = rs.ResultStatus(rs.SUCCESS.status, rs.SUCCESS.msg, pathologyDict)
            return jsonify(result.__dict__, ensure_ascii=False)
    return jsonify(rs.SUCCESS.__dict__, ensure_ascii=False)


@front.route('/loginPage', methods=['GET', 'POST'])
def loginPage():
    return render_template("loginPage.html")


@front.route('/error', methods=['GET', 'POST'])
def errorPage():
    return render_template("errorpage.html")


@front.route('/userCenter/<int:userId>', methods=['GET', 'POST'])
def userCenter(userId):
    userRole=UserRole.getUserRole(db_session,userId)
    if userRole:
        if userRole.roleId==constant.RoleId.Admin:
            return redirect('/admin/fenzhen')
        if userRole.roleId==constant.RoleId.Doctor:
            return redirect('/doctorhome')
        if userRole.roleId==constant.RoleId.HospitalUser:
            return redirect('/hospital/user')
        if userRole.roleId==constant.RoleId.Patient:
            return redirect('/patienthome')
        if userRole.roleId==constant.RoleId.Kefu:
            return redirect('/admin/kefu')
    return render_template("errorPage.html")

@front.route('/help/center', methods=['GET', 'POST'])
def helpCenterPage():
    result = {}
    result['ishelpcenter'] = True
    return render_template("helpcenter.html",data=result)

@front.route('/help/doc', methods=['GET', 'POST'])
def helpDocPage():
    return render_template("helpdoc.html")


@front.route('/about', methods=['GET', 'POST'])
def aboutPage():
    return render_template("about.html")