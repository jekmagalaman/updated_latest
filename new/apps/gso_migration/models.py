# gso_migration/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.gso_accounts.models import Unit  # <-- add this import

User = get_user_model()

class MigrationUpload(models.Model):
    MIGRATION_TYPE_CHOICES = [
        ('WORK_REPORT', 'Work Accomplishment Report'),
        ('IPMT', 'IPMT Records'),
        ('INVENTORY', 'Inventory Items'),
        ('SERVICE_REQUEST', 'Service Requests'),
    ]

    file = models.FileField(upload_to='migration_files/')
    migration_type = models.CharField(max_length=50, choices=MIGRATION_TYPE_CHOICES)
    target_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, help_text="Select the Unit where this data belongs")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    result_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Data Migration"
        verbose_name_plural = "Data Migrations"

    def __str__(self):
        return f"{self.get_migration_type_display()} ({self.uploaded_at:%Y-%m-%d})"
