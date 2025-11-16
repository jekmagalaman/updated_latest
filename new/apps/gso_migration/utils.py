# gso_migration/utils.py
import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.gso_requests.models import ServiceRequest
from apps.gso_inventory.models import InventoryItem
from apps.gso_reports.models import WorkAccomplishmentReport, IPMT, SuccessIndicator
from apps.gso_accounts.models import Unit

User = get_user_model()

def safe_text(value, fallback="N/A"):
    if pd.isna(value) or str(value).strip() == "":
        return fallback
    return str(value).strip()

def safe_number(value):
    try:
        if pd.isna(value) or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def migrate_excel(file_path, migration_type, target_unit=None):
    df = pd.read_excel(file_path)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]  # normalize headers
    count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            with transaction.atomic():
                # --- INVENTORY ---
                if migration_type == 'INVENTORY':
                    InventoryItem.objects.create(
                        name=safe_text(row.get('name')),
                        description=safe_text(row.get('description'), ''),
                        quantity=safe_number(row.get('quantity')),
                        unit_of_measurement=safe_text(row.get('unit_of_measurement'), 'pcs'),
                        category=safe_text(row.get('category'), 'N/A'),
                    )

                # --- SERVICE REQUEST ---
                elif migration_type == 'SERVICE_REQUEST':
                    unit = target_unit or Unit.objects.filter(name=row.get('unit')).first()
                    requestor = User.objects.filter(username=row.get('requestor')).first()
                    ServiceRequest.objects.create(
                        requestor=requestor,
                        unit=unit,
                        description=safe_text(row.get('description'), ''),
                        activity_name=safe_text(row.get('activity_name'), 'N/A'),
                        status=safe_text(row.get('status'), 'Pending'),
                    )

                # --- WORK REPORT (WAR) ---
                elif migration_type == 'WORK_REPORT':
                    if pd.isna(row.get('activity_name')) and pd.isna(row.get('description')):
                        continue
                    
                    unit = target_unit or Unit.objects.filter(name=row.get('unit')).first()
                    # Text-only fallback values for migrated data
                    requesting_office_name = safe_text(row.get('requesting_office'), unit.name if unit else "N/A")
                    personnel_names = safe_text(row.get('assigned_personnel'), "Unassigned")

                    WorkAccomplishmentReport.objects.create(
                        unit=unit,
                        date_started=row.get('date_started'),
                        date_completed=row.get('date_completed'),
                        activity_name=safe_text(row.get('activity_name')),
                        description=safe_text(row.get('description')),
                        status=safe_text(row.get('status'), 'Completed'),
                        material_cost=safe_number(row.get('material_cost')),
                        labor_cost=safe_number(row.get('labor_cost')),
                        total_cost=safe_number(row.get('material_cost')) + safe_number(row.get('labor_cost')),
                        control_number=safe_text(row.get('control_number'), None),

                        # New fallback text fields (for migrated records)
                        requesting_office_name=requesting_office_name,
                        personnel_names=personnel_names,
                    )

                # --- IPMT ---
                elif migration_type == 'IPMT':
                    personnel = User.objects.filter(username=row.get('personnel')).first()
                    unit = target_unit or Unit.objects.filter(name=row.get('unit')).first()
                    indicator = SuccessIndicator.objects.filter(id=row.get('indicator_id')).first()
                    IPMT.objects.create(
                        personnel=personnel,
                        unit=unit,
                        month=safe_text(row.get('month')),
                        indicator=indicator,
                        accomplishment=safe_text(row.get('accomplishment'), ''),
                        remarks=safe_text(row.get('remarks'), ''),
                    )

                count += 1

        except Exception as e:
            errors.append(f"Row {index + 1}: {e}")
            continue

    message = f"{count} records imported successfully."
    if errors:
        message += f" {len(errors)} rows failed to import."
        print("\n".join(errors))
    return message
