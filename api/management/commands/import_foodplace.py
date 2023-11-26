import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import FoodPlace, LocationImage
from urllib.parse import unquote

class Command(BaseCommand):
    help = 'Import data from CSV to FoodPlace model'

    def handle(self, *args, **options):
        csv_file = os.path.join(settings.BASE_DIR, 'TravelPackage - FoodPlace.csv')

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1
                is_closed = bool(int(row.get('IsClosed', 0)))

                foodplace = FoodPlace.objects.create(
                    name=row['Place'],
                    address=row['Address'],
                    description=row.get('Description', 'No Description Provided.'),
                    latitude=float(row['Latitude']),
                    longitude=float(row['Longitude']),
                    is_closed=is_closed,
                    location_type='2',
                )

                image_path = unquote(row['Image'])
                LocationImage.objects.create(
                    location=foodplace,
                    image=image_path,
                    is_primary_image=True
                )

                print("Imported " + foodplace.name)
        self.stdout.write(self.style.SUCCESS('Data imported successfully'))