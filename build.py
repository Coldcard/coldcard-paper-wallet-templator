#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Render PDF files needed for printing labels.
#
#
import sys, os, csv, PIL, pdb, re, click
import logging
from io import BytesIO
from PIL import Image
from binascii import b2a_hex, a2b_hex
from collections import Counter

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch, cm
#from reportlab.graphics import renderPDF
#from reportlab.graphics.shapes import Drawing 
from reportlab.pdfbase import pdfdoc
from reportlab.lib import colors
from reportlab import rl_config

# just for fonts
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

# These config values allow us to see text in a plain form in resulting PDF
# - see pp/reportlab/rl_settings.py
rl_config.useA85 = 0
rl_config.invariant = 1
rl_config.pageCompression = 0

# These very-specific text values are matched on the Coldcard; cannot be changed.
class placeholders:
    addr = 'ADDRESS_XXXXXXXXXXXXXXXXXXXXXXXXXXXXX'                      # 37 long
    privkey = 'PRIVKEY_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'     # 51 long

    # rather than Tokyo, I chose Chiba Prefecture in ShiftJIS encoding...
    header = b'%PDF-1.3\n%\x90\xe7\x97t\x8c\xa7 Coldcard Paper Wallet Template\n'


# Control the first few bytes of the file ... still valid PDF file tho.
# - had to monkey-patch in this change
# - see pp/reportlab/pdfbase/pdfdoc.py PDFFile() class
class myPDFFile(pdfdoc.PDFFile):
    def __init__(self,unused):
        self.strings = []
        self.write = self.strings.append
        self.offset = 0
        self.add(placeholders.header)
pdfdoc.PDFFile = myPDFFile


class TemplateBuilder(object):
    def __init__(self, input_template, output_fname=None, canvas=None):

        pages = PdfReader(input_template).pages
        self.xobjs = [(pagexobj(x),) for x in pages]

        assert len(pages) == 1, "only supporting a single page"

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
            Whole page is one raster image. XXX untested
        '''
        c = self.canvas

        c.setPageSize((width, height))

        from reportlab.lib.utils import ImageReader

        X_SHIFT = 0
        Y_SHIFT = -0.120 * inch

        # paste in the image
        c.drawImage(ImageReader(img, ident=str(label)), X_SHIFT,Y_SHIFT,
                    width=width, height=height, preserveAspectRatio=True)

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
        c = self.canvas
        c.setTitle("Paper Wallet template for Coldcard")
        c.setAuthor("Templator")
        c.setCreator("Templator")
        c.setProducer("Templator")
        self.canvas.save()


class WalletBuilder(TemplateBuilder):
    def insert_values(self, page_num, *unused):
        c = self.canvas

        if 0:
            c.saveState()
            # change color: black
            c.setFillColorRGB(0,0,0)
            c.setStrokeColorRGB(0,0,0)

            # 12pt font: 
            c.setFont("Courier", 12)

            # these are trival to find in output PDF once A85 encoding is disabled
            c.drawString(1.25*inch, 3.5*inch, placeholders.addr)
            c.drawString(6.25*inch, 3.5*inch, placeholders.privkey)

            c.restoreState()

        self.add_qr_spot('addr', placeholders.addr, 1.5*inch, 4*inch)
        self.add_qr_spot('pk', placeholders.privkey, 6.75*inch, 4*inch)
        self.add_qr_spot('pk', placeholders.privkey, 6.75*inch, 1*inch, inch)


    def add_qr_spot(self, name, subtext, x,y, page_size=2.25*inch, SZ=33*8):

        # make a temp image to get started, data not critical except that
        # must be unique because it gets hashed into eh xobj name

        c = self.canvas
        c.saveState()

        # change color: black
        c.setFillColorRGB(0,0,0)
        c.setStrokeColorRGB(0,0,0)


        img = Image.new('L', (SZ,SZ))
        img.putdata(name.encode('utf-8'))

        from reportlab.lib.utils import ImageReader

        width = height = page_size

        # paste in the image
        c.drawImage(ImageReader(img, ident='qr1'), x, y,
                    width=width, height=height, preserveAspectRatio=True)

        # Hack Zone: 
        # - find image just created, and change it to hex encoded, non-compressed form
        # - also put magic pattern into data, which the Coldcard can find
        # - see: pp/reportlab/pdfgen/pdfimages.py
        # - and: reportlab/pdfgen/canvas.py drawImage()
        # - add: reportlab/pdfbase/pdfdoc.py PDFImageXObject()
        line = c._code[-2] 
        assert line.endswith(' Do')
        handle = line[1:-3]

        ximg = c._doc.idToObject.get(handle)
        assert ximg
        assert ximg.width == ximg.height == SZ      # pixel sizes

        ximg._filters = ('ASCIIHexDecode',)      # kill the Flate (zlib)
        ximg.bitsPerComponent = 1

        # Stream itself, is just hex of raw pixels.
        # - add whitespace as needed, so will split newline each raster line
        # - first line reserved for magic data pattern, rest is dont-care
        # - each byte is 8 pixels of monochrome data
        # - left-to-right, top-to-bottom

        fl = ('QR:%s' % name).encode('ascii').ljust(SZ//8, b'\xff')
        assert len(fl) == (SZ//8)

        # make a placeholder image for sizing/preview purposes. Not a real QR.
        lines = []

        img = Image.open(f'qrsample-{name}.pnm')
        assert img.size == (SZ, SZ), 'need another sample'
        sample = img.tobytes()
        for o in range(0, len(sample), SZ//8):
            lines.append(sample[o:o+(SZ//8)])

        lines[0] = fl
        #ximg.streamContent = fl + '\n' + '\n'.join(('%02X'%(0xff if (i>>2)%2 else 0x00))*(SZ//8)
        #                                                    for i in range(SZ-1)) + '\n'
        ximg.streamContent = '\n'.join(ln.hex().upper() for ln in lines)
        ximg.streamContent += '\n'

        if subtext:
            # pick font size; doesn't try to suit size of QR, more like readable size
            font_size = 8 if len(subtext) > 40 else 11
            c.setFont("Courier", font_size)

            # these strings are trival to find in output PDF once A85 encoding is disabled
            c.drawCentredString(x+(page_size/2), y - 5 - font_size, subtext)

        c.restoreState()

def file_checker(fname):
    raw = open(fname, 'rb').read()

    assert raw.startswith(placeholders.header), 'header wrong/missing'
    assert placeholders.addr.encode('ascii') in raw, "payment addr (text) missing"
    assert placeholders.privkey.encode('ascii') in raw, 'privkey (text) missing'

    lines = raw.split(b'\n')

    max_len = max(len(ln) for ln in lines)
    print(f"Max line length in file: {max_len}")
    assert max_len < 2048, "some lines are too long"

    counts = Counter()
    for n, ln in enumerate(lines):
        if ln == b'stream':
            try:
                fl = a2b_hex(lines[n+1])
                assert fl.startswith(b'QR:')
            except:
                continue

            fl = fl.rstrip(b'\xff').decode('ascii')[3:]
            counts[fl] += 1

    assert len(counts) == 2, "missing QR instances"
    assert all(i==1 for i in counts.values()), "too many images?"

    print("Includes QR's: " + ', '.join(counts))
    print("File checks out ok!")
    

if __name__ == '__main__':

    foo = WalletBuilder('placeholder.pdf', 'output.pdf')
    foo.make_custom()
    foo.finalize()

    file_checker('output.pdf')

    os.system('open output.pdf')

# EOF
