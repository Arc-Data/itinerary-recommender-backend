# your_app/management/commands/run_server_profiler.py
import os
from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from memory_profiler import profile

class Command(BaseCommand):
    help = 'Run the development server with memory profiler'

    @profile
    def handle(self, *args, **options):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")
        execute_from_command_line(["manage.py", "runserver", "--noreload"])
