import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Accommodation, Service

class Command(BaseCommand):
    help = 'Import food items from CSV and associate them with FoodPlaces'

    def handle(self, *args, **options):
        csv_file_path = os.path.join(settings.BASE_DIR, 'TravelPackage - Service.csv')

        accommodations = Accommodation.objects.all()

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1
                place_name = row.get('Place')
                item_name = row.get('Item')
                description = row.get('Description')
                price = float(row.get('Price', 0))
                image_path = row.get('Image')

                try:
                    accommodation = accommodations.get(name=place_name)
                except Accommodation.DoesNotExist:
                    print("Accommodation not detected: ", place_name)
                    continue

                service_item = Service.objects.create(
                    location=accommodation,
                    item=item_name,
                    price=price,
                    description=description,
                    image=image_path
                )

                print(f"Imported service '{item_name}' for {place_name}")

        self.stdout.write(self.style.SUCCESS('Services imported successfully'))