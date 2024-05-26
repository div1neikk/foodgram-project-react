from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse


def create_pdf(data_list: list[str]):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] =\
        'attachment; filename="shopping_cart.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, "Shopping Cart Ingredients:")

    y = 730
    for recipe_ingredient in data_list:
        ingredient_name = recipe_ingredient['ingredient__name']
        measurement_unit = recipe_ingredient['ingredient__measurement_unit']
        amount = recipe_ingredient['amount']
        p.drawString(100, y, f"{ingredient_name}: {amount} {measurement_unit}")
        y -= 20

    p.save()
    return response
