# Templator for Coldcard Paper Wallets

- an artist creates the PDF with background artwork
- locations for pubkey, privkey QR's and text blocks are defined mm by mm
- run this program to add placeholders objects for the 2 QR codes, related variable text
- a template file, which looks and acts like a PDF is constructed
- use the resulting (pdf) file on Coldcard as a template
- the Coldcard can find what it needs inside the PDF template and will modify it with final values

# References

- [PDF 1.3?](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/pdf_reference_archives/PDFReference.pdf)
- [PDF 1.7?](https://www.adobe.com/content/dam/acom/en/devnet/pdf/pdfs/PDF32000_2008.pdf)

- [ReportLab manual](https://www.reportlab.com/docs/reportlab-userguide.pdf)
