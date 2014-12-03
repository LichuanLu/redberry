# coding: utf-8

__author__ = 'lichuan'

from xhtml2pdf import pisa,default
from cStringIO import StringIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import constant,oss_util
from DoctorSpring.models import Diagnose
import config
from flask import abort, render_template, flash

from PyPDF2 import PdfFileWriter, PdfFileReader
from helper import timeout_command


import random
import string

#for pdf to png
# import sys
# import signal
# import os
# import urlparse
# import logging
# from optparse import OptionParser
# import time

# from PyQt4.QtCore import *
# from PyQt4.QtGui import *
# from PyQt4.QtWebKit import *
# from PyQt4.QtNetwork import *


def save_pdf(pdf_data,file,diagnoseId,fileName,identityPhone):
    default.DEFAULT_FONT["helvetica"]="msyh"
    fontFile = os.path.join( constant.DirConstant.ROOT_DIR+ '/DoctorSpring/static/font', 'msyh.ttf')
    pdfmetrics.registerFont(TTFont('msyh',fontFile))
    # from xhtml2pdf.pisa.sx.pisa3 import pisa_default
    pdf = pisa.pisaDocument(StringIO(
        pdf_data.encode("UTF-8")), file,encoding='utf-8')
    file.close()

    output = PdfFileWriter()

    with open(fileName, "rb") as f1:
        input1 = PdfFileReader(f1)

        for i in range(input1.getNumPages()):
            output.addPage(input1.getPage(i))

        #print(identityPhone)
        password = str(int(identityPhone))
        owner_pwd = ''.join(random.choice(string.letters + string.digits) for _ in range(64))
        #print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" + owner_pwd)
        output.encrypt(password, owner_pwd)

        output.write(open("temp.pdf", "wb"))

    os.remove(fileName)
    os.rename("temp.pdf", fileName)

    fileUrl=upload_pdf(fileName,diagnoseId)
    return fileUrl
def upload_pdf(fileName,diagnoseId):
      fileUrl=oss_util.uploadFile(diagnoseId,fileName)
      return fileUrl

def generatorPdf(diagnoseId, identityPhone):
    diagnose=Diagnose.getDiagnoseById(diagnoseId)
    report=None
    if hasattr(diagnose,'report'):
        report=diagnose.report
        if diagnose and report and report.type==constant.ReportType.Doctor:
            data={}
            data['techDesc']=report.techDesc
            data['imageDesc']=report.imageDesc
            data['diagnoseDesc']=report.diagnoseDesc
            data['seriesNumber']=report.seriesNumber
            data['fileUrl']=report.fileUrl
            createDate=report.createDate
            if createDate:
                createDate=createDate.strftime('%Y-%m-%d')
                data['createDate']=createDate
            import  DoctorSpring.views.data_change_service as dataChangeService
            postions=dataChangeService.getDiagnosePositonFromDiagnose(diagnose)
            if postions:
                data['postions']=postions
            if hasattr(diagnose,'patient') and diagnose.patient:
                data['gender']=diagnose.patient.gender
                birthDate=diagnose.patient.birthDate
                if birthDate:
                    birthDate=birthDate.strftime('%Y-%m-%d')
                    data['birthDate']=birthDate
                data['name']=diagnose.patient.realname
            if hasattr(diagnose,'doctor'):
                data['doctorName']=diagnose.doctor.username

            html =  render_template('diagnoseResultPdf.html',data=data)
            fileName=constant.DirConstant.DIAGNOSE_PDF_DIR+'test.pdf'
            result = open(fileName, 'wb') # Changed from file to filename

            url = save_pdf(html,result,diagnoseId,fileName, identityPhone)
            result.close()
            # return render_template("testpdf.html",getAvatar=getAvatar)
            return url
    return None


def generatorHtml(diagnoseId, identityPhone):
    diagnose=Diagnose.getDiagnoseById(diagnoseId)
    report=None
    if hasattr(diagnose,'report'):
        report=diagnose.report
        if diagnose and report and report.type==constant.ReportType.Doctor:
            data={}
            data['techDesc']=report.techDesc
            data['imageDesc']=report.imageDesc
            data['diagnoseDesc']=report.diagnoseDesc
            data['seriesNumber']=report.seriesNumber
            data['fileUrl']=report.fileUrl
            createDate=report.createDate
            if createDate:
                createDate=createDate.strftime('%Y-%m-%d')
                data['createDate']=createDate
            import  DoctorSpring.views.data_change_service as dataChangeService
            postions=dataChangeService.getDiagnosePositonFromDiagnose(diagnose)
            if postions:
                data['postions']=postions
            if hasattr(diagnose,'patient') and diagnose.patient:
                data['gender']=diagnose.patient.gender
                birthDate=diagnose.patient.birthDate
                if birthDate:
                    birthDate=birthDate.strftime('%Y-%m-%d')
                    data['birthDate']=birthDate
                data['name']=diagnose.patient.realname
            if hasattr(diagnose,'doctor'):
                data['doctorName']=diagnose.doctor.username

            html =  render_template('diagnoseResultPdf.html',data=data)
            fileName=constant.DirConstant.DIAGNOSE_PDF_DIR+'diagnose'+str(diagnoseId)+'Html.html'
            result = open(fileName, 'w+b') # Changed from file to filename
            result.write(html)
            result.close()

            fileLink = 'file://'+fileName
            pdfLink = constant.DirConstant.DIAGNOSE_PDF_DIR+'diagnose'+str(diagnoseId)+'Pdf.pdf'
            print fileLink
            print pdfLink
            returnCode = generate_pdf_from_html(fileLink,pdfLink)
            # return render_template("testpdf.html",getAvatar=getAvatar)
            if(returnCode == 0):
                #add encrypt for pdf
                output = PdfFileWriter()
                with open(pdfLink, "r+") as f1:
                    input1 = PdfFileReader(f1)

                    for i in range(input1.getNumPages()):
                        output.addPage(input1.getPage(i))
                    #print(identityPhone)
                    password = str(int(identityPhone))
                    owner_pwd = ''.join(random.choice(string.letters + string.digits) for _ in range(64))
                    #print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" + owner_pwd)
                    output.encrypt(password, owner_pwd)
                    f1.seek(0)
                    output.write(f1)
                    f1.truncate()
                    fileUrl=upload_pdf(pdfLink,diagnoseId)
                    return fileUrl
            else:
                return None
    return None

def generate_pdf_from_html(fileLink,pdfLink):
    commands = [config.WKHTMLTOPDF_COMMAND1,config.WKHTMLTOPDF_COMMAND2,config.WKHTMLTOPDF_COMMAND3,config.WKHTMLTOPDF_COMMAND4,fileLink,pdfLink]
    out = timeout_command(commands,300)
    return out
## generate from html to png testing----------
#
# VERSION="20091224"
# LOG_FILENAME = 'webkit2png.log'
# logger = logging.getLogger('webkit2png');
#
# def generatorHtml(diagnoseId, identityPhone):
#     diagnose=Diagnose.getDiagnoseById(diagnoseId)
#     report=None
#     if hasattr(diagnose,'report'):
#         report=diagnose.report
#         if diagnose and report and report.type==constant.ReportType.Doctor:
#             data={}
#             data['techDesc']=report.techDesc
#             data['imageDesc']=report.imageDesc
#             data['diagnoseDesc']=report.diagnoseDesc
#             data['seriesNumber']=report.seriesNumber
#             data['fileUrl']=report.fileUrl
#             createDate=report.createDate
#             if createDate:
#                 createDate=createDate.strftime('%Y-%m-%d')
#                 data['createDate']=createDate
#             import  DoctorSpring.views.data_change_service as dataChangeService
#             postions=dataChangeService.getDiagnosePositonFromDiagnose(diagnose)
#             if postions:
#                 data['postions']=postions
#             if hasattr(diagnose,'patient') and diagnose.patient:
#                 data['gender']=diagnose.patient.gender
#                 birthDate=diagnose.patient.birthDate
#                 if birthDate:
#                     birthDate=birthDate.strftime('%Y-%m-%d')
#                     data['birthDate']=birthDate
#                 data['name']=diagnose.patient.realname
#             if hasattr(diagnose,'doctor'):
#                 data['doctorName']=diagnose.doctor.username
#
#             html =  render_template('diagnoseResultPdf.html',data=data)
#             fileName=constant.DirConstant.DIAGNOSE_PDF_DIR+'diagnose'+str(diagnoseId)+'Html.html'
#             result = open(fileName, 'w+b') # Changed from file to filename
#             result.write(html)
#             result.close()
#
#             fileLink = 'file://'+fileName
#             imageLink = constant.DirConstant.DIAGNOSE_PDF_DIR+'diagnose'+str(diagnoseId)+'Image.png'
#             generate_png_from_html(fileLink,imageLink)
#             # return render_template("testpdf.html",getAvatar=getAvatar)
#             return imageLink
#     return None


# def generate_png_from_html(fileLink,imageLink):
#     if 'http_proxy' in os.environ:
#         proxy_url = urlparse.urlparse(os.environ.get('http_proxy'))
#         proxy = QNetworkProxy(QNetworkProxy.HttpProxy, proxy_url.hostname, proxy_url.port)
#         QNetworkProxy.setApplicationProxy(proxy)
#
#     options = {}
#     link = fileLink
#     target = imageLink
#     # link = 'http://www.google.com'
#     options['output'] = target
#     # Prepare output ("1" means STDOUT)
#     if options['output'] is None:
#         options['output'] = sys.stdout
#     else:
#         options['output'] = open(options['output'], "w")
#
#     options['url'] = link
#     options['width'] = 1280
#     options['height'] = 1656
#     # options['ratio'] = 'expand'
#
#
#     logger.debug("Version %s, Python %s, Qt %s", VERSION, sys.version, qVersion());
#
#     # Technically, this is a QtGui application, because QWebPage requires it
#     # to be. But because we will have no user interaction, and rendering can
#     # not start before 'app.exec_()' is called, we have to trigger our "main"
#     # by a timer event.
#     def __main_qt():
#         # Render the page.
#         # If this method times out or loading failed, a
#         # RuntimeException is thrown
#         try:
#             # Initialize WebkitRenderer object
#             renderer = WebkitRenderer()
#             renderer.logger = logger
#             renderer.width = options['width']
#             renderer.height = options['height']
#             # renderer.timeout = options.timeout
#             # renderer.wait = options.wait
#             # renderer.format = 'jpeg'
#             # renderer.grabWholeWindow = options.window
#             # renderer.renderTransparentBackground = options.transparent
#             # renderer.encodedUrl = options.encoded_url
#             # if options.cookies:
#             #     renderer.cookies = options.cookies
#             #
#             # if options['scaleToWidth'] or options['scaleToHeight']:
#             #     renderer.scaleRatio = options['ratio']
#             #     renderer.scaleToWidth = options['scaleToWidth']
#             #     renderer.scaleToHeight = options['scaleToHeight']
#             #
#             # if options.features:
#             #     if "javascript" in options.features:
#             #         renderer.qWebSettings[QWebSettings.JavascriptEnabled] = True
#             #     if "plugins" in options.features:
#             #         renderer.qWebSettings[QWebSettings.PluginsEnabled] = True
#
#             renderer.render_to_file(url=options['url'], file_object=options['output'])
#             options['output'].close()
#             QApplication.exit(0)
#         except RuntimeError, e:
#             logger.error("main: %s" % e)
#             print >> sys.stderr, e
#             QApplication.exit(1)
#
#     # Initialize Qt-Application, but make this script
#     # abortable via CTRL-C
#     app = init_qtgui(display = None, style=None)
#     signal.signal(signal.SIGINT, signal.SIG_DFL)
#
#     QTimer.singleShot(0, __main_qt)
#     sys.exit(app.exec_())
#
#
# # def fetch_resources(uri, rel):
# #     path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
# #     return path
#
# def init_qtgui(display=None, style=None, qtargs=None):
#     """Initiates the QApplication environment using the given args."""
#     if QApplication.instance():
#         logger.debug("QApplication has already been instantiated. \
#                         Ignoring given arguments and returning existing QApplication.")
#         return QApplication.instance()
#
#     qtargs2 = [sys.argv[0]]
#
#     if display:
#         qtargs2.append('-display')
#         qtargs2.append(display)
#         # Also export DISPLAY var as this may be used
#         # by flash plugin
#         os.environ["DISPLAY"] = display
#
#     if style:
#         qtargs2.append('-style')
#         qtargs2.append(style)
#
#     qtargs2.extend(qtargs or [])
#
#     return QApplication(qtargs2)
## generate from html to png testing end----------
