from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.gso_accounts.models import Unit, User
from django.db.models import Q
from .models import InventoryItem
from .forms import InventoryItemForm




# -------------------------------
# Helper role checks
# -------------------------------
def is_unit_head(user):
    return user.is_authenticated and getattr(user, "role", None) == "unit_head"

def is_gso(user):
    return user.is_authenticated and getattr(user, "role", None) == "gso"

def is_director(user):
    return user.is_authenticated and getattr(user, "role", None) == "director"

# Combined check for GSO + Director
def can_access_inventory(user):
    return is_gso(user) or is_director(user)



# -------------------------------
# GSO / Director Inventory Views
# -------------------------------
@login_required
@user_passes_test(can_access_inventory)
def gso_inventory(request):
    """Display and filter inventory items for GSO and Director roles."""
    category = request.GET.get("category")
    query = request.GET.get("q")

    items = InventoryItem.objects.all()

    if category:
        items = items.filter(category=category)
    if query:
        items = items.filter(
            Q(name__icontains=query) |
            Q(category__icontains=query) |
            Q(description__icontains=query)
        )

    items = items.order_by("name")
    categories = InventoryItem.objects.values_list("category", flat=True).distinct()
    form = InventoryItemForm()
    forms_per_item = {item.id: InventoryItemForm(instance=item) for item in items}

    context = {
        "inventory_items": items,
        "categories": categories,
        "selected_category": category,
        "search_query": query,
        "form": form,
        "forms_per_item": forms_per_item,
        "units": Unit.objects.all(),
    }
    return render(request, "gso_office/inventory/gso_inventory.html", context)


@login_required
@user_passes_test(can_access_inventory)
def add_inventory_item(request):
    """Add a new inventory item."""
    if request.method == "POST":
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            # Optional: keep user on the same page if form invalid
            return render(request, "gso_office/inventory/gso_inventory.html", {
                "form": form,
                "inventory_items": InventoryItem.objects.all(),
            })
    return redirect("gso_inventory:gso_inventory")


@login_required
@user_passes_test(can_access_inventory)
def update_inventory_item(request, item_id):
    """Update an existing inventory item."""
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == "POST":
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
    return redirect("gso_inventory:gso_inventory")


@login_required
@user_passes_test(can_access_inventory)
def remove_inventory_item(request, item_id):
    """Delete an inventory item."""
    item = get_object_or_404(InventoryItem, id=item_id)
    if request.method == "POST":
        item.delete()
    return redirect("gso_inventory:gso_inventory")










# -------------------------------
# Unit Head Inventory
# -------------------------------
@login_required
def unit_head_inventory(request):
    user = request.user  # Current logged-in unit head

    # ✅ Get the unit assigned to this Unit Head
    unit = user.unit  

    # 🧩 Debug print to verify backend behavior
    print("✅ Logged-in user:", user.username)
    print("✅ Assigned unit:", unit)
    print("✅ Items found for this unit:", list(InventoryItem.objects.filter(owned_by=unit).values_list("name", flat=True)))

    # ✅ If no assigned unit, show empty results
    if not unit:
        inventory_items = InventoryItem.objects.none()
    else:
        # ✅ Show only inventory belonging to this unit
        inventory_items = InventoryItem.objects.filter(owned_by=unit, is_active=True)

    # --- Filters ---
    search_query = request.GET.get("q", "")
    selected_category = request.GET.get("category", "")

    if search_query:
        inventory_items = inventory_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    if selected_category:
        inventory_items = inventory_items.filter(category__iexact=selected_category)

    # --- Category dropdown (unique to this unit) ---
    categories = (
        InventoryItem.objects.filter(owned_by=unit)
        .values_list("category", flat=True)
        .distinct()
    )

    context = {
        "unit": unit,
        "inventory_items": inventory_items,
        "categories": categories,
        "selected_category": selected_category,
        "search_query": search_query,
    }

    return render(request, "unit_heads/unit_head_inventory/unit_head_inventory.html", context)



















# -------------------------------
# Personnel Inventory (placeholder)
# -------------------------------
@login_required
def personnel_inventory(request):
    # Currently personnel cannot see inventory
    return render(request, "personnel/personnel_inventory/personnel_inventory.html")
