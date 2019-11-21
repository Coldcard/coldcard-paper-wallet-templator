# Templator for Coldcard Paper Wallets

Just looking for some cool paper wallet templates? Go to [templates subdir](templates) 
and take any of the PDF files for use on Coldcard.

# How It Works

- an artist creates the PDF with background artwork, blank spots for QR's
- locations for pubkey, privkey QR's and any text blocks are defined mm by mm, in `build.py`
- run `build.py` to add placeholders objects for the 2 QR codes, related variable text
- a template file--which looks and acts like a PDF---is constructed, in `./templates`
- use the resulting (pdf) file on Coldcard via a MicroSD card
- the Coldcard can find what it needs inside the PDF template and will modify it with final values

## Design Tips

- you must include whitespace around the QR code: more the better, and should be fully 'quiet'
- QR will have background white with black pixels ... so do not place over gradient

# TODO

This project isn't done yet!
- [ ] make it easier to add new templates; pull meta data out of build into files
- [ ] build a gallery of useful examples
- [ ] make many seasonal templates, starting with Nov/Dec days

# References

- [PDF 1.3?](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf)
- [PDF 1.7?](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/PDF32000_2008.pdf)

- [ReportLab manual](https://www.reportlab.com/docs/reportlab-userguide.pdf)

# QR Sample images

- Made a zero-border verion 4 image here: <https://www.nayuki.io/page/qr-code-generator-library>
- With 8 pixels per module, like we will be doing.
- Edited with Preview.app
- Command to go from PNG with alpha and some text into simple PNM file:

    `pngtopam -mix -background=#FFF qrsample-pk.png | pamditherbw -threshold | pamtopnm > qrsample-pk.pnm
