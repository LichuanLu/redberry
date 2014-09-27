# coding: utf-8
__author__ = 'jeremyxu'
from DoctorSpring.models.diagnoseDocument import Diagnose
from DoctorSpring.util.constant import DiagnoseMethod,DiagnoseMethodCost

def get_name(user):
    if user is None:
        return ''

    if user.name is not None:
        return user.name

    if user.email is not None:
        return user.email

    if user.phone is not None:
        return user.phone

def getPayCountByDiagnoseId(diagnoseId):
    if diagnoseId is None:
        return
    diagnose=Diagnose.getDiagnoseById(diagnoseId)
    if diagnose and hasattr(diagnose,'pathology') and diagnose.pathology and hasattr(diagnose.pathology,"pathologyPostions") \
    and diagnose.pathology.pathologyPostions:
        diagnoseMethod=diagnose.pathology.diagnoseMethod
        count=len(diagnose.pathology.pathologyPostions)
        money=0
        if diagnoseMethod== DiagnoseMethod.Mri:
              money=DiagnoseMethodCost.Mri*count
        elif diagnoseMethod==DiagnoseMethod.Ct:
            money=DiagnoseMethodCost.Ct*count
        return money





