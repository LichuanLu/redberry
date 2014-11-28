# coding: utf-8
import datetime
import subprocess
import time


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
        return Diagnose.getPayCount(diagnoseMethod,count,Diagnose.getUserDiscount(diagnose.patientId))

def timeout_command(command, timeout):
    start = datetime.datetime.now()
    process = subprocess.Popen(command, bufsize=10000, stdout=subprocess.PIPE, close_fds=True)
    while process.poll() is None:
        time.sleep(0.1)
        now = datetime.datetime.now()
        if (now - start).seconds> timeout:
            try:
                process.terminate()
            except Exception,e:
                return None
            return None
    out = process.wait()
    if process.stdin:
        process.stdin.close()
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()
    try:
        process.kill()
    except OSError:
        pass
    return out





