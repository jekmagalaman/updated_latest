# apps/gso_requests/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden

from .models import ServiceRequest, RequestMaterial, Unit, TaskReport, Feedback
from apps.gso_accounts.models import User
from apps.gso_inventory.models import InventoryItem
from .utils import filter_requests, get_unit_inventory, create_war_from_request, notify_users
from apps.gso_reports.models import WorkAccomplishmentReport, SuccessIndicator

# -------------------------------
# Role checks
# -------------------------------
def is_gso(user): return user.is_authenticated and user.role == "gso"
def is_unit_head(user): return user.is_authenticated and user.role == "unit_head"
def is_requestor(user): return user.is_authenticated and user.role == "requestor"
def is_director(user): return user.is_authenticated and user.role == "director"


# -------------------------------
# Request Management Views (single template)
# -------------------------------
@login_required
def request_management(request):
    requests_qs = ServiceRequest.objects.select_related("requestor", "unit").prefetch_related("assigned_personnel").order_by("-is_emergency", "-created_at")


    # Apply filters
    requests_qs = filter_requests(
        requests_qs,
        search_query=request.GET.get("q"),
        unit_filter=request.GET.get("unit"),
    )

    units = Unit.objects.all()

    # Pass user role to template for role-specific buttons
    user_role = request.user.role

    return render(request, "gso_office/request_management/request_management.html", {
        "requests": requests_qs,
        "units": units,
        "search_query": request.GET.get("q"),
        "unit_filter": request.GET.get("unit"),
        "user_role": user_role,  # for template role checks
    })

@login_required
@user_passes_test(is_director)
def approve_request(request, pk):
    req = get_object_or_404(ServiceRequest, pk=pk)
    if req.status != "Pending":
        return HttpResponseForbidden("This request cannot be approved.")

    req.status = "Approved"
    req.save()
    return redirect("gso_requests:request_management")













# -------------------------------
# Unit Head Views
# -------------------------------
@login_required
@user_passes_test(is_unit_head)
def unit_head_request_management(request):
    requests_qs = ServiceRequest.objects.filter(
        unit=request.user.unit
    ).exclude(status__in=["Completed", "Cancelled"]).order_by("-is_emergency", "-created_at")


    # Apply filters
    requests_qs = filter_requests(
        requests_qs,
        search_query=request.GET.get("q"),
        status_filter=request.GET.get("status"),
    )

    return render(request, "unit_heads/unit_head_request_management/unit_head_request_management.html", {
        "requests": requests_qs
    })













@login_required
@user_passes_test(is_unit_head)
def unit_head_request_detail(request, pk):
    service_request = get_object_or_404(ServiceRequest, pk=pk)

    # --- All personnel in the same unit (active) ---
    all_personnel = User.objects.filter(
        role="personnel",
        unit=service_request.unit,
        is_active=True
    ).order_by("id")

    personnel_status = []
    for p in all_personnel:
        active_tasks = p.assigned_requests.filter(status__in=["Pending", "Approved", "In Progress"])
        personnel_status.append({
            "user": p,
            "busy": active_tasks.exists(),
            "active_tasks": active_tasks,
            "latest_task": active_tasks.order_by('-created_at').first() if active_tasks.exists() else None
        })

    # --- Materials for the same unit ---
    materials = InventoryItem.objects.filter(
        is_active=True,
        owned_by=service_request.unit
    ).order_by("id")

    # --- Progress Reports ---
    reports = service_request.reports.select_related("personnel").order_by("-created_at")

    # --- Linked WAR (if already created) ---
    war = getattr(service_request, "war", None)

    # --- All available success indicators for that unit ---
    indicators = SuccessIndicator.objects.filter(
        unit=service_request.unit,
        is_active=True
    ).order_by("code")

    # --- Handle Form Submissions ---
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        action = request.POST.get("action")

        # === Save/Update Success Indicator ===
        if "save_success_indicator" in request.POST:
            si_id = request.POST.get("success_indicator")
            if si_id:
                si = get_object_or_404(SuccessIndicator, id=si_id, unit=service_request.unit)
                service_request.selected_indicator = si
                service_request.save(update_fields=["selected_indicator"])
                messages.success(request, "✅ Success Indicator updated for this request.")
            else:
                messages.warning(request, "⚠️ Please select a valid Success Indicator.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === Assign Personnel ===
        if form_type == "assign_personnel":
            assigned_ids = request.POST.getlist("personnel_ids")
            service_request.assigned_personnel.set(assigned_ids)

            for pid in assigned_ids:
                user = User.objects.get(pk=pid)
                active_tasks = user.assigned_requests.filter(status__in=["Pending", "Approved", "In Progress"])
                if active_tasks.exists():
                    messages.warning(
                        request,
                        f"⚠️ {user.get_full_name()} is currently busy with {active_tasks.count()} task(s)."
                    )

            messages.success(request, "✅ Personnel assignments saved successfully.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === Assign Materials ===
        elif form_type == "assign_materials":
            # Restore previously used materials
            for rm in service_request.requestmaterial_set.all():
                rm.material.quantity += rm.quantity
                rm.material.save()
            service_request.requestmaterial_set.all().delete()

            material_ids = request.POST.getlist("material_ids")
            for material_id in material_ids:
                qty = request.POST.get(f"quantity_{material_id}")
                if qty and int(qty) > 0:
                    material = get_object_or_404(InventoryItem, pk=material_id, owned_by=service_request.unit)
                    qty = int(qty)
                    if material.quantity < qty:
                        messages.error(request, f"❌ Not enough {material.name} in stock.")
                        return redirect("gso_requests:unit_head_request_detail", pk=pk)

                    material.quantity -= qty
                    material.save()
                    RequestMaterial.objects.create(
                        request=service_request,
                        material=material,
                        quantity=qty
                    )

            messages.success(request, "✅ Material assignments saved successfully.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === Approve Completion (Generate WAR) ===
        elif action == "approve" and service_request.status == "Done for Review":
            service_request.status = "Completed"
            service_request.completed_at = timezone.now()
            service_request.save(update_fields=["status", "completed_at"])

            war = create_war_from_request(service_request)
            if war and service_request.selected_indicator:
                war.success_indicator = service_request.selected_indicator
                war.save(update_fields=["success_indicator"])

            messages.success(request, "✅ Request marked as Completed. WAR created.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === Reject Completion ===
        elif action == "reject" and service_request.status == "Done for Review":
            service_request.status = "In Progress"
            service_request.save(update_fields=["status"])
            messages.warning(request, "⚠️ Request sent back to In Progress.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === MARK AS EMERGENCY ===
        elif action == "set_emergency":
            service_request.is_emergency = True
            service_request.status = "Emergency"
            service_request.save(update_fields=["is_emergency", "status"])
            messages.success(request, "🚨 Request has been marked as EMERGENCY.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

        # === REMOVE EMERGENCY TAG ===
        elif action == "unset_emergency":
            service_request.is_emergency = False
            # Restore status to Pending (or In Progress if you prefer)
            service_request.status = "Pending"
            service_request.save(update_fields=["is_emergency", "status"])
            messages.info(request, "❎ Emergency tag removed from this request.")
            return redirect("gso_requests:unit_head_request_detail", pk=pk)

    # --- Assigned Materials (for editing) ---
    assigned_materials = {
        rm.material.id: rm.quantity for rm in service_request.requestmaterial_set.all()
    }

    # --- Render Template ---
    return render(request, "unit_heads/unit_head_request_management/request_detail.html", {
        "req": service_request,
        "personnel_status": personnel_status,
        "materials": materials,
        "reports": reports,
        "assigned_materials": assigned_materials,
        "war": war,
        "indicators": indicators,
    })





















@login_required
@user_passes_test(is_unit_head)
def unit_head_request_history(request):
    requests_qs = ServiceRequest.objects.filter(
        unit=request.user.unit,
        status__in=["Completed", "Cancelled"]
    ).order_by("-created_at")

    requests_qs = filter_requests(requests_qs, search_query=request.GET.get("q"))
    return render(request, "unit_heads/unit_head_request_history/unit_head_request_history.html", {
        "requests": requests_qs
    })



@login_required
def unit_head_material_detail(request, item_id):
    item = get_object_or_404(InventoryItem, id=item_id)
    return render(request, "unit_heads/unit_head_inventory/unit_head_material_detail.html", {
        "material": item,
    })







# -------------------------------
# Personnel Views
# -------------------------------
@login_required
def personnel_task_management(request):
    tasks = ServiceRequest.objects.filter(assigned_personnel=request.user).exclude(status__in=["Completed", "Cancelled"]).distinct()
    tasks = filter_requests(tasks, search_query=request.GET.get("q"), status_filter=request.GET.get("status"))
    return render(request, "personnel/personnel_task_management/personnel_task_management.html", {"tasks": tasks})










@login_required
def personnel_task_detail(request, pk):
    from apps.gso_reports.models import SuccessIndicator
    from apps.gso_inventory.models import InventoryItem
    from django.db import transaction

    task = get_object_or_404(ServiceRequest, pk=pk, assigned_personnel=request.user)
    materials = task.requestmaterial_set.select_related("material")
    reports = task.reports.select_related("personnel").order_by("-created_at")
    indicators = SuccessIndicator.objects.filter(is_active=True).order_by("code")

    # ✅ Materials available in inventory for this unit
    available_materials = InventoryItem.objects.filter(
        is_active=True,
        owned_by=task.unit
    ).order_by("name")

    # ✅ Dictionary of already assigned materials (material_id → quantity)
    assigned_materials = {m.material.id: m.quantity for m in materials}

    if request.method == "POST":
        # Start Task
        if "start" in request.POST and task.status == "Approved":
            task.status = "In Progress"
            task.started_at = timezone.now()
            task.save()

        # Mark Done
        elif "done" in request.POST and task.status == "In Progress":
            indicator_id = request.POST.get("success_indicator")
            if indicator_id:
                try:
                    task.selected_indicator_id = int(indicator_id)
                    task.save(update_fields=["selected_indicator"])
                except ValueError:
                    pass

            task.status = "Done for Review"
            task.done_at = timezone.now()
            task.save()

        # Add Report
        elif "add_report" in request.POST:
            report_text = request.POST.get("report_text", "").strip()
            if report_text:
                TaskReport.objects.create(request=task, personnel=request.user, report_text=report_text)

        # Save Indicator
        elif "save_indicator" in request.POST:
            indicator_id = request.POST.get("success_indicator")
            if indicator_id:
                try:
                    task.selected_indicator_id = int(indicator_id)
                    task.save(update_fields=["selected_indicator"])
                    messages.success(request, "Success indicator saved.")
                except ValueError:
                    messages.error(request, "Invalid indicator selected.")

        # 🆕 Assign Multiple Materials
        elif request.POST.get("action") == "assign_materials":
            selected_ids = request.POST.getlist("material_ids")

            with transaction.atomic():
                # Restore inventory for previously assigned materials (in case of change)
                for req_mat in materials:
                    inv_item = req_mat.material
                    inv_item.quantity += req_mat.quantity
                    inv_item.save()
                    req_mat.delete()

                # Assign new selected materials
                for mid in selected_ids:
                    qty_field = f"quantity_{mid}"
                    try:
                        quantity = int(request.POST.get(qty_field, 0))
                        material = InventoryItem.objects.get(pk=mid, owned_by=task.unit)

                        if quantity <= 0:
                            continue
                        if material.quantity < quantity:
                            messages.warning(request, f"Not enough stock for {material.name}.")
                            continue

                        # Deduct from inventory
                        material.quantity -= quantity
                        material.save()

                        # Create new RequestMaterial
                        task.requestmaterial_set.create(
                            material=material,
                            quantity=quantity
                        )
                    except (ValueError, InventoryItem.DoesNotExist):
                        continue

            messages.success(request, "Materials updated successfully.")
            return redirect("gso_requests:personnel_task_detail", pk=task.id)

        return redirect("gso_requests:personnel_task_detail", pk=task.id)

    return render(request, "personnel/personnel_task_management/personnel_task_detail.html", {
        "task": task,
        "materials": materials,
        "reports": reports,
        "indicators": indicators,
        "available_materials": available_materials,
        "assigned_materials": assigned_materials,  # ✅ Pass to template
    })



















@login_required
def personnel_history(request):
    history = ServiceRequest.objects.filter(assigned_personnel=request.user, status="Completed").order_by("-created_at")
    return render(request, "personnel/personnel_history/personnel_history.html", {"history": history})


@login_required
def personnel_inventory(request):
    materials = get_unit_inventory(request.user.unit, search_query=request.GET.get("q"))
    return render(request, "personnel/personnel_inventory/personnel_inventory.html", {"materials": materials})












# -------------------------------
# Requestor Views
# -------------------------------
@login_required
@user_passes_test(is_requestor)
def requestor_request_management(request):
    requests_qs = ServiceRequest.objects.filter(requestor=request.user).order_by("-created_at")
    units = Unit.objects.all()
    return render(request, "requestor/requestor_request_management/requestor_request_management.html", {
        "requests": requests_qs,
        "units": units,
    })


@login_required
@user_passes_test(is_requestor)
def add_request(request):
    if request.method == "POST":
        ServiceRequest.objects.create(
            requestor=request.user,
            unit_id=request.POST.get("unit"),
            description=request.POST.get("description"),
            status="Pending",
            department=request.user.department,
            custom_full_name=request.POST.get("custom_full_name") or "",
            custom_email=request.POST.get("custom_email") or "",
            custom_contact_number=request.POST.get("custom_contact_number") or "",
            attachment=request.FILES.get("attachment"),
        )
        return redirect("gso_requests:requestor_request_management")
    


    


@login_required
@user_passes_test(is_requestor)
def cancel_request(request, pk):
    req = get_object_or_404(ServiceRequest, pk=pk, requestor=request.user)
    if req.status in ["Pending", "Approved"]:
        req.status = "Cancelled"
        req.save()
    return redirect("gso_requests:requestor_request_management")


@login_required
@user_passes_test(is_requestor)
def requestor_request_history(request):
    history = ServiceRequest.objects.filter(
        requestor=request.user,
        status__in=["Completed", "Cancelled"]
    ).order_by("-created_at")
    return render(request, "requestor/requestor_request_history/requestor_request_history.html", {
        "request_history": history
    })




# -------------------------------
# SUCCESS INDICATOR (Personnel + Unit Head)
# -------------------------------

@login_required
def update_success_indicator_personnel(request, request_id):
    """
    Allow assigned personnel to propose/update a success indicator for their completed task.
    """
    service_request = get_object_or_404(ServiceRequest, id=request_id, assigned_personnel=request.user)
    war = WorkAccomplishmentReport.objects.filter(request=service_request).first()

    if not war:
        messages.error(request, "No Work Accomplishment Report found for this request.")
        return redirect("gso_requests:personnel_task_detail", pk=request_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if name:
            indicator, _ = SuccessIndicator.objects.get_or_create(name=name)
            if description:
                indicator.description = description
                indicator.save(update_fields=["description"])
            war.success_indicator = indicator
            war.save(update_fields=["success_indicator"])
            messages.success(request, "Success Indicator updated successfully.")
            return redirect("gso_requests:personnel_task_detail", pk=request_id)

        messages.warning(request, "Indicator name is required.")

    return render(request, "personnel/personnel_success_indicator_form.html", {
        "task": service_request,
        "war": war,
    })


@login_required
def update_success_indicator_unit_head(request, request_id):
    """
    Allow Unit Head to review/update a success indicator for their unit’s request.
    """
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    war = WorkAccomplishmentReport.objects.filter(request=service_request).first()

    if not war:
        messages.error(request, "No Work Accomplishment Report found for this request.")
        return redirect("gso_requests:unit_head_request_detail", pk=request_id)

    # Restrict to same unit
    if request.user.role != "unit_head" or service_request.unit != request.user.unit:
        return HttpResponseForbidden("Not authorized to edit this indicator.")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if name:
            indicator, _ = SuccessIndicator.objects.get_or_create(name=name)
            if description:
                indicator.description = description
                indicator.save(update_fields=["description"])
            war.success_indicator = indicator
            war.save(update_fields=["success_indicator"])
            messages.success(request, "Success Indicator updated successfully.")
            return redirect("gso_requests:unit_head_request_detail", pk=request_id)

        messages.warning(request, "Indicator name is required.")

    return render(request, "unit_head/unit_head_success_indicator_form.html", {
        "req": service_request,
        "war": war,
    })

# -------------------------------
# Feedback Views
# -------------------------------
@login_required
def submit_feedback(request):
    """Handles submission of the Client Satisfaction Measurement form."""
    from django.http import JsonResponse

    if request.method == "POST":
        try:
            req = get_object_or_404(ServiceRequest, id=request.POST.get("request_id"))
            user = request.user

            # ✅ Prevent duplicate feedbacks
            if Feedback.objects.filter(request=req, user=user).exists():
                return JsonResponse({
                    "success": False,
                    "already_submitted": True,
                    "error": "You have already submitted feedback for this request."
                })

            feedback = Feedback.objects.create(
                request=req,
                user=user,
                cc1=request.POST.get("cc1", ""),
                cc2=request.POST.get("cc2", ""),
                cc3=request.POST.get("cc3", ""),
                suggestions=request.POST.get("suggestions", ""),
                email=request.POST.get("email", "")
            )

            for i in range(1, 10):
                val = request.POST.get(f"sqd{i}")
                setattr(feedback, f"sqd{i}", int(val) if val else None)
            feedback.save()

            # 🔔 Notification: GSO, Director, and Unit Head(s)
            # GSO & Director
            recipients_gso_director = User.objects.filter(role__in=["gso", "director"], is_active=True)
            notify_users(
                recipients_gso_director,
                message=f"📝 Feedback submitted for request #{req.id} by {user.get_full_name()}",
                url=f"/gso_requests/{req.id}/"
            )

            # Unit Head(s) of the request's unit
            recipients_unit_heads = User.objects.filter(role="unit_head", unit=req.unit, is_active=True)
            notify_users(
                recipients_unit_heads,
                message=f"📝 Feedback submitted for request #{req.id} by {user.get_full_name()}",
                url=f"/unit_head/request/{req.id}/"
            )

            return JsonResponse({
                "success": True,
                "message": "Thank you for your feedback!",
                "request_id": req.id
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid method"})

# ---- New view for modal content ----
@login_required
def request_detail_partial(request, pk):
    """Returns just the modal HTML for one request (used via AJAX)"""
    req = get_object_or_404(ServiceRequest, pk=pk)
    return render(request, "gso_office/partials/request_modal_content.html", {
        "req": req,
        "user_role": request.user.role,  # <-- add this
    })
