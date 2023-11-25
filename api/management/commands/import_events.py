import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Event
from datetime import datetime

class Command(BaseCommand):
    help = 'Import events from CSV file'

    def handle(self, *args, **options):
        csv_file = os.path.join(settings.BASE_DIR, 'TravelPackage - Events.csv')

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                event = Event(
                    name=row['Name'],
                    start_date=datetime.strptime(row['Start'], '%m/%d/%Y').date(),
                    end_date=datetime.strptime(row['End'], '%m/%d/%Y').date(),
                    latitude=float(row['Latitude']),
                    longitude=float(row['Longitude']),
                    description=row['Description'],
                )
                event.save()

                print("Imported " + event.name)

        self.stdout.write(self.style.SUCCESS('Successfully imported events'))