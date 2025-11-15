from django import forms
from .models import InventoryItem

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "category", "quantity", "unit_of_measurement", "description", "owned_by"]
        labels = {
            "name": "Material Name",
            "category": "Category",
            "quantity": "Quantity",
            "unit_of_measurement": "Unit",
            "description": "Description",
            "owned_by": "Unit Owner",  # or "Assigned Unit"
        }