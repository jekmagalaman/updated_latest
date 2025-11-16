from django.db.models import Q
from apps.gso_requests.models import ServiceRequest
from apps.gso_inventory.models import InventoryItem
from apps.gso_reports.models import WorkAccomplishmentReport, SuccessIndicator
from apps.ai_service.utils import generate_war_description  # AI util
from apps.notifications.models import Notification
from django.utils import timezone
import threading


# -------------------------------
# Request Filtering Helper
# -------------------------------
def filter_requests(queryset, search_query=None, unit_filter=None, status_filter=None):
    if search_query:
        queryset = queryset.filter(
            Q(requestor__username__icontains=search_query)
            | Q(requestor__first_name__icontains=search_query)
            | Q(requestor__last_name__icontains=search_query)
            | Q(unit__name__icontains=search_query)
            | Q(requestor__department__name__icontains=search_query)
        )
    if unit_filter:
        try:
            queryset = queryset.filter(unit_id=int(unit_filter))
        except ValueError:
            pass
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return queryset


# -------------------------------
# Inventory Helper
# -------------------------------
def get_unit_inventory(unit, search_query=None):
    materials = InventoryItem.objects.filter(is_active=True, owned_by=unit)
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    return materials


# -------------------------------
# WAR Creation Helper (Non-blocking AI description)
# -------------------------------
def create_war_from_request(request):
    """
    Auto-generate a Work Accomplishment Report (WAR) when a request is completed.
    Generates AI description in a background thread to avoid blocking the request.
    Personnel can later update the Success Indicator.
    """
    # Combine all task reports (if any)
    task_reports_text = " ".join([t.report_text for t in request.reports.all()])

    # --- Create or fetch WAR linked to this request ---
    war, created = WorkAccomplishmentReport.objects.get_or_create(
        request=request,
        defaults={
            "date_started": request.created_at.date(),
            "date_completed": timezone.now().date(),
            "status": "Completed",
            "activity_name": getattr(request, "title", None) or "General Task",
            "unit": request.unit,
            "success_indicator": getattr(request, "selected_indicator", None),
        },
    )

    # ✅ Ensure WAR is linked to the ServiceRequest
    if war.request_id != request.id:
        war.request = request
        war.save(update_fields=["request"])

    # ✅ Copy assigned personnel to WAR
    if request.assigned_personnel.exists():
        war.assigned_personnel.set(request.assigned_personnel.all())

    # ✅ Ensure WAR has a Success Indicator placeholder
    if not hasattr(war, "success_indicator") or war.success_indicator is None:
        indicator, _ = SuccessIndicator.objects.get_or_create(
            name="Pending Review",
            defaults={"description": "To be defined by assigned personnel or GSO office."},
        )
        war.success_indicator = indicator
        war.save(update_fields=["success_indicator"])

    # ---------------------------
    # Generate AI description asynchronously
    # ---------------------------
    def generate_description_thread(war_instance, req):
        description = generate_war_description(req)
        if description:
            war_instance.description = description
            war_instance.save(update_fields=["description"])

    threading.Thread(
        target=generate_description_thread,
        args=(war, request),
        daemon=True,
    ).start()

    return war

# ---------------------------
# Notification Helper
# ---------------------------
def notify_users(users, message, url=None):
    """
    Send notifications to a list of users, automatically deduplicating.
    `users` can be a list or queryset.
    """
    for user in set(users):  # set() removes duplicates
        Notification.objects.create(
            user=user,
            message=message,
            url=url
        )