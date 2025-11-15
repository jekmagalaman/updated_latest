from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.gso_accounts.models import Unit, User

User = settings.AUTH_USER_MODEL


# -------------------------------------------------------------------
# SUCCESS INDICATOR (clean, no more mapping or ActivityName)
# -------------------------------------------------------------------
class SuccessIndicator(models.Model):
    """
    Success indicators per unit (used for IPMT and WARs).
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)  # e.g., CF1, SF2
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.unit.name}"

class WorkAccomplishmentReport(models.Model):
    """
    Represents a Work Accomplishment Report (WAR), either migrated or live from ServiceRequest.
    Focused on activity-based tracking for IPMT.
    """
    request = models.OneToOneField(
        "gso_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="war",
        null=True, blank=True
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    assigned_personnel = models.ManyToManyField(
        User, related_name="war_personnel", blank=True
    )
    
    # NEW FIELDS FOR MIGRATED DATA
    requesting_office_name = models.CharField(max_length=255, null=True, blank=True)
    personnel_names = models.TextField(null=True, blank=True, help_text="Comma-separated names for migrated WARs")


    date_started = models.DateField()
    date_completed = models.DateField(null=True, blank=True)

    activity_name = models.CharField(max_length=255, blank=True, null=True)  # <-- changed from project_name
    description = models.TextField(blank=True)

     # ✅ New field (manual success indicator)
    success_indicator = models.ForeignKey(
        "SuccessIndicator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wars",
        help_text="Selected success indicator relevant to this work"
    )

    status = models.CharField(
        max_length=50,
        choices=[
            ("Pending", "Pending"),
            ("In Progress", "In Progress"),
            ("Completed", "Completed"),
        ],
        default="Completed",
    )

    material_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    control_number = models.CharField(max_length=100, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def generate_description(self):
        """
        Returns the WAR description, or fallback text if missing.
        """
        if self.description:
            return self.description
        if self.request:
            return f"WAR generated from request {self.request.id}: {self.request.description}"
        return f"WAR for activity {self.activity_name or 'N/A'}"

    def save(self, *args, **kwargs):
        self.total_cost = (self.material_cost or 0) + (self.labor_cost or 0)
        super().save(*args, **kwargs)

    def get_requesting_office(self):
        """Return requesting office from ServiceRequest or migrated field."""
        if self.request and hasattr(self.request, "requesting_office"):
            return self.request.requesting_office.name
        return self.requesting_office_name or "N/A"

    def get_personnel_display(self):
        """Return personnel names either from M2M or from migrated text."""
        personnel_list = self.assigned_personnel.all()
        if personnel_list.exists():
            return ", ".join([p.get_full_name() for p in personnel_list])
        return self.personnel_names or "Unassigned"

    def __str__(self):
        return f"WAR - {self.activity_name or 'No Activity'} ({self.unit.name})"

# -------------------------------------------------------------------
# IPMT (simple, directly linked to WAR success indicator)
# -------------------------------------------------------------------
class IPMT(models.Model):
    """
    IPMT entry generated from Work Accomplishment Reports.
    """
    personnel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)  # e.g., "September 2025"

    # Directly tied to WAR's success indicator
    indicator = models.ForeignKey(SuccessIndicator, on_delete=models.CASCADE)
    accomplishment = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    reports = models.ManyToManyField(WorkAccomplishmentReport, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.personnel} - {self.month} - {self.indicator.code}"