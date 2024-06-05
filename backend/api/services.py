from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import FileResponse
from io import BytesIO
from recipes.models import RecipeIngredient


def create_pdf(user):
    data_list = RecipeIngredient.objects.filter(recipe__author=user).values(
        'ingredient__name', 'ingredient__measurement_unit', 'amount'
    )
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Shopping Cart Ingredients:")

    y = 730
    for recipe_ingredient in data_list:
        ingredient_name = recipe_ingredient['ingredient__name']
        measurement_unit = recipe_ingredient['ingredient__measurement_unit']
        amount = recipe_ingredient['amount']
        p.drawString(100, y, f"{ingredient_name}: {amount} {measurement_unit}")
        y -= 20

    p.save()
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename='shopping_cart.pdf'
    )
