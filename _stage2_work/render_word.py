from pathlib import Path
import win32com.client
import fitz
root=Path.cwd() / '_stage2_work'
word=win32com.client.DispatchEx('Word.Application')
word.Visible=False
word.DisplayAlerts=0
document=None
try:
    document=word.Documents.Open(str(root / 'qa-export.docx'),ReadOnly=True,AddToRecentFiles=False)
    document.ExportAsFixedFormat(str(root / 'qa-export.pdf'),17)
    document.SaveAs2(str(root / 'qa-word-saved.docx'),16,AddToRecentFiles=False)
finally:
    if document is not None:
        document.Close(False)
    word.Quit()
with fitz.open(root / 'qa-export.pdf') as pdf:
    for number,page in enumerate(pdf,1):
        page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(root / f'qa-page-{number}.png'))
    print(f'Native Word rendered {len(pdf)} pages.')
