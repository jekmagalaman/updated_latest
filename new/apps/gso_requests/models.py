from django.db import models
from django.conf import settings
from apps.gso_accounts.models import Unit, Department
from apps.gso_inventory.models import InventoryItem
from apps.gso_reports.models import SuccessIndicator 


class ServiceRequest(models.Model):
    """
    Represents a service request submitted by a user (requestor).
    Tracks workflow status, assigned personnel, and requested materials.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("In Progress", "In Progress"),
        ("Done for Review", "Done for Review"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Emergency", "Emergency"),
    ]

    # Who made the request
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests"
    )
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    # If request is made on behalf of someone else
    custom_full_name = models.CharField(max_length=255, blank=True, null=True)
    custom_email = models.EmailField(blank=True, null=True)
    custom_contact_number = models.CharField(max_length=50, blank=True, null=True)
    attachment = models.ImageField(upload_to='request_attachments/', blank=True, null=True)

    # 🚨 Emergency flag
    is_emergency = models.BooleanField(default=False)


    # Scheduling
    schedule_start = models.DateTimeField(null=True, blank=True)
    schedule_end = models.DateTimeField(null=True, blank=True)
    schedule_remarks = models.TextField(null=True, blank=True)



    # Details
    activity_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Short standardized activity name (auto-mapped from description)"
    )
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Assignment
    assigned_personnel = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_requests"
    )

    # Materials used
    materials = models.ManyToManyField(
        InventoryItem,
        through="RequestMaterial",
        blank=True,
        related_name="requests"
    )

    # ✅ Personnel-chosen success indicator
    selected_indicator = models.ForeignKey(
        SuccessIndicator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_for_requests",
        help_text="Temporary field where personnel can choose success indicator before WAR generation."
    )

    # === GLOBAL DEFAULT ORDERING (Emergency requests first) ===
    class Meta:
        ordering = ['-is_emergency', '-created_at']

    def __str__(self):
        display_name = self.custom_full_name or self.requestor.get_full_name()
        return f"Request #{self.id} by {display_name} - {self.unit.name}"

    @property
    def assigned_personnel_names(self):
        personnel = self.assigned_personnel.all()
        if personnel.exists():
            return ", ".join([p.get_full_name() or p.username for p in personnel])
        return ""



class RequestMaterial(models.Model):
    """Through model for materials used in a request."""
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    material = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.material.name} x {self.quantity} (Request #{self.request.id})"


class TaskReport(models.Model):
    """Individual report written by personnel assigned to a request."""
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="reports")
    personnel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TaskReport by {self.personnel} (Request #{self.request.id})"
    


class Feedback(models.Model):
    """Feedback form tied to a specific service request."""
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Citizen’s Charter Questions (Part I)
    cc1 = models.CharField(max_length=200, blank=True, verbose_name="Awareness of Citizen's Charter")
    cc2 = models.CharField(max_length=200, blank=True, verbose_name="Knowledge of Office CC")
    cc3 = models.CharField(max_length=200, blank=True, verbose_name="Usefulness of CC")

    # Service Quality Dimensions (Part II)
    sqd1 = models.IntegerField(null=True, blank=True, verbose_name="Staff were courteous and helpful")
    sqd2 = models.IntegerField(null=True, blank=True, verbose_name="Spent reasonable time for transaction")
    sqd3 = models.IntegerField(null=True, blank=True, verbose_name="Clear communication during process")
    sqd4 = models.IntegerField(null=True, blank=True, verbose_name="Accessible and adequate facilities")
    sqd5 = models.IntegerField(null=True, blank=True, verbose_name="Equipped and knowledgeable staff")
    sqd6 = models.IntegerField(null=True, blank=True, verbose_name="Transparent and fair service")
    sqd7 = models.IntegerField(null=True, blank=True, verbose_name="Services met expectations")
    sqd8 = models.IntegerField(null=True, blank=True, verbose_name="Satisfied with overall experience")
    sqd9 = models.IntegerField(null=True, blank=True, verbose_name="Would recommend the service")

    # Optional Suggestions & Contact
    suggestions = models.TextField(blank=True, verbose_name="Suggestions for improvement")
    email = models.EmailField(blank=True, null=True, verbose_name="Email address (optional)")

    # Analytics Fields
    average_score = models.FloatField(default=0, verbose_name="Average satisfaction score")
    sentiment = models.CharField(max_length=20, blank=True, verbose_name="Sentiment (AI-generated)")
    is_visible = models.BooleanField(default=True, verbose_name="Visible in reports")

    date_submitted = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Automatically compute average score when saving."""
        scores = [
            self.sqd1, self.sqd2, self.sqd3, self.sqd4,
            self.sqd5, self.sqd6, self.sqd7, self.sqd8, self.sqd9
        ]
        valid_scores = [s for s in scores if s is not None]
        self.average_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Feedback for Request #{self.request.id} by {self.user.username}"

