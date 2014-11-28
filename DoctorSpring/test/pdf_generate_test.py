__author__ = 'lichuan'
import unittest
from xhtml2pdf import pisa,default
from cStringIO import StringIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from DoctorSpring.util import constant

from DoctorSpring.models import Diagnose

from flask import abort, render_template, flash

from PyPDF2 import PdfFileWriter, PdfFileReader
import random
import string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, flowables
import subprocess
# -*- coding: utf-8 -*-

from xhtml2pdf import pisa
from StringIO import StringIO

from reportlab.platypus import Frame, Image
from reportlab.lib import utils
from reportlab.lib.units import cm,inch

# Utility function
def convertHtmlToPdf(source):
    # open output file for writing (truncated binary)

    pdf = StringIO()
    pisaStatus = pisa.CreatePDF(StringIO(source.encode('utf-8')), pdf)

    # return True on success and False on errors
    print "Success: ", pisaStatus.err
    return pdf


class PdfTestCase(unittest.TestCase):



    def test_generatePdf(self):

        default.DEFAULT_FONT["helvetica"]="msyh"
        fontFile = os.path.join( constant.DirConstant.ROOT_DIR+ '/DoctorSpring/static/font', 'msyh.ttf')
        pdfmetrics.registerFont(TTFont('msyh',fontFile))


        with open(constant.DirConstant.ROOT_DIR+'/DoctorSpring/templates/diagnoseResultPdfTest.html', "rb") as html:
            pdf_data = html.read()

        print pisa.showLogging()
        pdf = convertHtmlToPdf(pdf_data)
        fd = open("test3.pdf", "w+b")
        fd.write(pdf.getvalue())
        fd.close()

    def test_generatePdf2(self):
        link = 'file://'+constant.DirConstant.ROOT_DIR+'/DoctorSpring/templates/diagnoseResultPdfTest.html';
        target = constant.DirConstant.ROOT_DIR+'/DoctorSpring/templates';
        print(target);
        print(link);
        subprocess.call(["webkit2png", "-o","NAME", "-g", "1000", "1260",
                         "-t", "30",'-D',target,link])


    def get_image(path, width=1*inch):
        img = utils.ImageReader(path)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        return Image(path, width=width, height=(width * aspect))

    def test_generatePdf3(self):
        from reportlab.pdfgen import canvas
        from StringIO import StringIO



        # Using ReportLab to insert image into PDF
        imgTemp = StringIO()


        imgDoc = canvas.Canvas(imgTemp,pagesize=(792,809))

        # Draw image on Canvas and save PDF in buffer
        imgPath = "/dev_lic/python_ws/python-webkit2png/build/scripts-2.7/t1131.png"

        image = Image(imgPath)

        # aspect = float(1187) / 792
        # width = 8.5 * inch
        # # height=(width * aspect)
        # height = 11 * inch
        # image._restrictSize(width, height)


        imgDoc.drawImage(imgPath, 0, 0, 792, 809)    ## at (399,760) with size 160x160
        imgDoc.save()

        # Use PyPDF to merge the image-PDF into the template
        # page = PdfFileReader(file("document.pdf","rb")).getPage(0)
        overlay = PdfFileReader(StringIO(imgTemp.getvalue())).getPage(0)
        # page.mergePage(overlay)

        #Save the result
        output = PdfFileWriter()
        output.addPage(overlay)
        output.write(file("output7.pdf","w+b"))
