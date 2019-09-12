#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Render PDF files needed for printing labels.
#
#
import sys, os, csv, PIL, pdb
from io import BytesIO
#from pdfrw.objects.pdfdict import PdfDict
from PIL import Image

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch, cm
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.barcode.code128 import Code128
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing 
from reportlab.lib import colors
from reportlab import rl_config

# just for fonts
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

# see  pp/reportlab/rl_settings.py
rl_config.useA85 = 0
rl_config.pageCompression = 0


import logging

class TemplateBuilder(object):
    def __init__(self, input_template, output_fname=None, canvas=None):

        pages = PdfReader(input_template).pages
        self.xobjs = [(pagexobj(x),) for x in pages]

        if output_fname:
            # probably an object, not filename, but whatevers
            self.canvas = Canvas(output_fname)
        else:
            self.canvas = canvas

        assert self.canvas, 'cant write?'

        self.qr_set = set()

    def insert_values(self, page_num, *values):
        raise NotImplemented

    def make_custom(self, *values):
        c = self.canvas

        for page_num, xobjlist in enumerate(self.xobjs):

            x = y = 0
            for xobj in xobjlist:
                x += xobj.BBox[2]
                y = max(y, xobj.BBox[3])

            c.setPageSize((x,y))
            x,y = 0,0

            # render background template data
            for xobj in xobjlist:
                c.saveState()
                c.translate(x, y)
                c.doForm(makerl(c, xobj))
                c.restoreState()

                # put our data on "top"
                self.insert_values(page_num, *values)

                x += xobj.BBox[2]

            c.showPage()

    def make_image_page(self, img, label=None, width=4*inch, height=6*inch, footnote=None):
        '''
            Whole page is one image.
        '''
        c = self.canvas

        c.setPageSize((width, height))

        from reportlab.lib.utils import ImageReader

        X_SHIFT = 0
        Y_SHIFT = -0.120 * inch

        # paste in the image
        c.drawImage(ImageReader(img, ident=str(label)), X_SHIFT,Y_SHIFT,
                    width=width, height=height, preserveAspectRatio=True)

        if footnote:
            # Add some tiny text in corning or something. Used for
            # internall additions to the label.
            #self.simple_text(footnote, x=width/2, y=(0.05*inch))
            self.simple_text(footnote, x=width-(0.05*inch), y=(0.10*inch))

        c.showPage()

    def simple_text(self, msg, x=1*inch, y=1*inch):
        # draw a single line of simple stuff

        c = self.canvas

        c.saveState()

        c.setFillColorRGB(0,0,0)
        c.setStrokeColorRGB(0,0,0)
        c.setFont("Courier-Bold", 6)

        # centered horizontally at target spot
        #c.drawCentredString(x, y, msg)
        # right-justified
        c.drawRightString(x, y, msg)

        c.restoreState()

    
    def finalize(self):
        self.canvas.save()


class WalletBuilder(TemplateBuilder):
    def insert_values(self, page_num, *unused):
        c = self.canvas
        c.saveState()

        # change color: black
        c.setFillColorRGB(0,0,0)
        c.setStrokeColorRGB(0,0,0)

        # 12pt font: 
        c.setFont("Courier", 12)

        # these are trival to find in output PDF once A85 encoding is disabled
        c.drawString(1.25*inch, 3.5*inch, '1depositaddressexamplehere')
        c.drawString(6.25*inch, 3.5*inch, '5privatekeywoudlbehereforexample')

        c.restoreState()

        self.add_qr_spot(1.5*inch, 4*inch, c, 'qr1')
        self.add_qr_spot(6.75*inch, 4*inch, c, 'qr2')


    def add_qr_spot(self, x,y, c, name, SZ=32*8):
        img = Image.new('L', (SZ,SZ))
        img.putdata(name.encode('utf-8'))       # this gets hashed into the xobj name

        from reportlab.lib.utils import ImageReader

        width = 2*inch
        height = 2*inch

        # paste in the image
        c.drawImage(ImageReader(img, ident='qr1'), x, y,
                    width=width, height=height, preserveAspectRatio=True)

        if 1:
            # hack: find image just created, and convert to hex encoded, non-compressed form
            # see: pp/reportlab/pdfgen/pdfimages.py
            # and: reportlab/pdfgen/canvas.py drawImage()
            # add: reportlab/pdfbase/pdfdoc.py PDFImageXObject()
            line = c._code[-2] 
            assert line.endswith(' Do')
            handle = line[1:-3]

            ximg = c._doc.idToObject.get(handle)
            assert ximg
            assert ximg.width == ximg.height == SZ

        if 1:
            ximg._filters = ('ASCIIHexDecode',)      # kill the Flate (zlib)

        if 0:
            ximg.bitsPerComponent = 8
            ximg.streamContent = '\n'.join(('%02X'%(i*2))*128 for i in range(128))

        if 1:
            ximg.bitsPerComponent = 1
            ximg.streamContent = '\n'.join(('%02X'%(0xff if (i>>2)%2 else 0x00))*(SZ//8)
                                                            for i in range(SZ))

        #pdb.set_trace()


if __name__ == '__main__':

    foo = WalletBuilder('placeholder.pdf', 'output.pdf')
    foo.make_custom()
    foo.finalize()

    os.system('open output.pdf')

# EOF
