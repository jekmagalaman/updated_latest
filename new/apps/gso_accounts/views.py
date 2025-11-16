from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.db.models import Q, Case, When, IntegerField
from .forms import UserEditForm, RequestorProfileUpdateForm, UserForm

from django.contrib.auth.forms import PasswordChangeForm

# -------------------------------
# Role Redirect
# -------------------------------
@login_required
def role_redirect(request):
    role_map = {
        "director": "gso_reports:gso_analytics",  # ✅ unified template
        "gso": "gso_reports:gso_analytics",
        "unit_head": "gso_requests:unit_head_request_management",
        "personnel": "gso_requests:personnel_task_management",
        "requestor": "gso_requests:requestor_request_management",
    }
    target = role_map.get(request.user.role)
    if target:
        return redirect(target)
    return redirect("gso_accounts:login")

User = get_user_model()

# -------------------------------
# GSO Account Management
# -------------------------------
@login_required
def account_management(request):
    users = User.objects.all()

    # Status filter
    status_filter = request.GET.get("status")
    if status_filter:
        users = users.filter(account_status=status_filter)

    # Search filter
    search_query = request.GET.get("q")
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query)
        )

    # Custom role order (highest to lowest)
    role_order = Case(
        When(role="director", then=0),
        When(role="gso", then=1),
        When(role="unit_head", then=2),
        When(role="personnel", then=3),
        When(role="requestor", then=4),
        default=5,
        output_field=IntegerField(),
    )

    users = users.order_by(role_order, 'last_name', 'first_name')  # optional secondary sort

    return render(request, "gso_office/accounts/account_management.html", {"users": users})










# -------------------------------
# Requestor Views
# -------------------------------
@login_required
def requestor_account(request):
    return render(request, "requestor/requestor_account/requestor_account.html")


@login_required
def requestor_profile(request):
    user = request.user

    if request.method == 'POST':
        # Update email if changed
        email = request.POST.get('email', '').strip()
        if email and email != user.email:
            user.email = email
            user.save()
            messages.success(request, "✅ Email updated successfully.")

        # Handle password change
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if current_password and new_password and confirm_password:
            if not user.check_password(current_password):
                messages.error(request, "❌ Incorrect current password.")
            elif new_password != confirm_password:
                messages.error(request, "⚠️ New passwords do not match.")
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "🔒 Password updated successfully.")

        return redirect('requestor_profile')

    return render(request, 'requestor/requestor_account/requestor_account.html', {'user': user})


@login_required
def search_personnel(request):
    """AJAX endpoint: search active personnel by name."""
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        personnel = User.objects.filter(
            role="personnel",
            account_status="active"
        ).filter(Q(first_name__icontains=query) | Q(last_name__icontains=query))[:10]

        results = [{"id": p.id, "name": f"{p.first_name} {p.last_name}"} for p in personnel]

    return JsonResponse(results, safe=False)































# -------------------------------
# Dashboard Views
# -------------------------------
@login_required
def director_dashboard(request):
    # Redirect director immediately to their request management page
    return redirect("gso_requests:director_request_management")

@login_required
def gso_dashboard(request):
    # Redirect to GSO Office request management
    return redirect("gso_requests:request_management")  

@login_required
def unit_head_dashboard(request):
    # Redirect to Unit Head request management
    return redirect("gso_requests:unit_head_request_management")

@login_required
def personnel_dashboard(request):
    # Redirect to Personnel task management
    return redirect("gso_requests:personnel_task_management")

@login_required
def requestor_dashboard(request):
    # Redirect to Requestor request management
    return redirect("gso_accounts:requestor_request_management")












@login_required
def unit_head_account_management(request):
    user = request.user

    # Initialize a blank password form (will re-bind only when password form is submitted)
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        # Profile Update Form
        if 'update_profile' in request.POST:
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')

            # Safely split name into first and last
            if full_name:
                name_parts = full_name.split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            user.email = email
            user.save()

            messages.success(request, "Profile updated successfully!")

        # Password Change Form
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # keeps user logged in
                messages.success(request, "Password changed successfully!")
                return redirect('gso_accounts:unit_head_account_management')
            else:
                messages.error(request, "Please correct the errors below.")

    return render(request, 'unit_heads/unit_head_account_management/unit_head_account_management.html', {
        'user': user,
        'form': password_form
    })














@login_required
def personnel_account_management(request):
    user = request.user

    # Initialize a blank password form (will re-bind only when password form is submitted)
    password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        # Profile Update Form
        if 'update_profile' in request.POST:
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')

            # Safely split name into first and last
            if full_name:
                name_parts = full_name.split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            user.email = email
            user.save()

            messages.success(request, "Profile updated successfully!")

        # Password Change Form
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # keeps user logged in
                messages.success(request, "Password changed successfully!")
                return redirect('gso_accounts:personnel_account_management')
            else:
                messages.error(request, "Please correct the errors below.")

    return render(request, 'personnel/personnel_account_management/personnel_account_management.html', {
        'user': user,
        'form': password_form
    })










# GSO OFFICE ACCOUNTS MANAGENMENT - EDIT USER
@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)

            user.is_active = (user.account_status == "active")

            # Password update
            new_pass = form.cleaned_data.get("new_password")
            confirm_pass = form.cleaned_data.get("confirm_password")

            if new_pass:
                if new_pass == confirm_pass:
                    user.set_password(new_pass)
                else:
                    form.add_error("confirm_password", "Passwords do not match.")
                    return render(request, "gso_office/accounts/account_edit.html", {"form": form, "user": user})

            user.save()
            return redirect("gso_accounts:account_management")
    else:
        form = UserEditForm(instance=user)

    return render(request, "gso_office/accounts/account_edit.html", {"form": form, "user": user})






@login_required
def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data["password"])
            user.save()
            return redirect("gso_accounts:account_management")
    else:
        form = UserForm()
    return render(request, "gso_office/accounts/add_user.html", {"form": form})