# gso_migration/admin.py
from django.contrib import admin
from .models import MigrationUpload
from .utils import migrate_excel

@admin.register(MigrationUpload)
class MigrationUploadAdmin(admin.ModelAdmin):
    list_display = ('migration_type', 'target_unit', 'uploaded_by', 'uploaded_at', 'processed')
    readonly_fields = ('uploaded_at', 'result_message', 'processed', 'uploaded_by')
    fields = ('migration_type', 'target_unit', 'file', 'uploaded_by', 'uploaded_at', 'processed', 'result_message')

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

        if not obj.processed:
            try:
                result = migrate_excel(obj.file.path, obj.migration_type, obj.target_unit)
                obj.result_message = result
                obj.processed = True
                obj.save()
                self.message_user(request, f"✅ {result}")
            except Exception as e:
                obj.result_message = f"❌ Error: {str(e)}"
                obj.save()
                self.message_user(request, f"❌ Migration failed: {e}", level='error')
