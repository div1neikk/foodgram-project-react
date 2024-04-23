import io

from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfgen import canvas


def create_pdf(data_list: list[str]):
    buffer = io.BytesIO()
    file = canvas.Canvas(buffer)
    pdfmetrics.registerFont(ttfonts.TTFont('Vera',
                                           'Vera.ttf'))
    file.setFont("Vera", 15)
    y = 750
    for item in data_list:
        name = item["ingredient__name"]
        unit = item["ingredient__measurement_unit"]
        row = f'- {name} - {item["amount"]} {unit}'
        file.drawString(100, y, row)
        y -= 30
    file.showPage()
    file.save()
    buffer.seek(0)
    return buffer