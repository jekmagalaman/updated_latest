import os
import datetime
from django.conf import settings
import shutil
import glob
import time
import subprocess


def backup_database():
    """Creates a PostgreSQL database backup (.sql file)."""
    print("Starting database backup...")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f'gso_backup_{timestamp}.sql')

    # === Database settings ===
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings.get('HOST', 'localhost')
    db_port = db_settings.get('PORT', '5432')

    # === Path to pg_dump ===
    PG_DUMP_PATH = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"

    # === Set password in environment temporarily ===
    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    try:
        subprocess.run([
            PG_DUMP_PATH,
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "-F", "p",
            "-f", backup_file,
            db_name
        ], check=True, env=env)
        print(f"Database backup created: {backup_file}")
    except subprocess.CalledProcessError as e:
        print(f"Database backup failed: {e}")
    except FileNotFoundError:
        print("pg_dump not found. Check your PostgreSQL installation path.")
    finally:
        env.pop("PGPASSWORD", None)

    return backup_file


def backup_media():
    """Creates a ZIP archive of uploaded media files."""
    print("Starting media backup...")

    src = settings.MEDIA_ROOT
    if not src or not os.path.exists(src):
        print("MEDIA_ROOT does not exist or is empty. Skipping media backup.")
        return None

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    archive_name = os.path.join(backup_dir, f'media_backup_{timestamp}')
    shutil.make_archive(archive_name, 'zip', src)

    print(f"Media backup created: {archive_name}.zip")
    return f"{archive_name}.zip"


def cleanup_old_backups(days=7):
    """Deletes backup files older than the specified number of days."""
    print(f"Cleaning up backups older than {days} days...")

    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        print("No backup directory found. Skipping cleanup.")
        return

    cutoff = time.time() - (days * 86400)

    for file in glob.glob(os.path.join(backup_dir, '*')):
        if os.path.getctime(file) < cutoff:
            os.remove(file)
            print(f"Deleted old backup: {file}")

    print("Old backup cleanup completed.")


def run_full_backup():
    """Runs the full backup process (database + media + cleanup)."""
    print("Starting full backup process...")
    db_file = backup_database()
    media_file = backup_media()
    cleanup_old_backups(days=7)
    print("Backup process completed!")
    return db_file, media_file
