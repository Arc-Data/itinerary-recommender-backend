import os
import csv
from django.conf import settings
from datetime import time, datetime
from django.core.management.base import BaseCommand
from api.models import FoodPlace, LocationImage, FoodTag
from urllib.parse import unquote

class Command(BaseCommand):
    help = 'Import data from CSV to FoodPlace model'

    def get_time_str(self, time_str):
        if not time_str:
            return None

        try:
            time_formats = ['%H:%M:%S', '%I:%M %p', '%I:%M%p']
            for format_str in time_formats:
                try:
                    return datetime.strptime(time_str, format_str).time()
                except ValueError:
                    pass

            return None
        except Exception as e:
            return None

    def handle(self, *args, **options):
        csv_file = os.path.join(settings.BASE_DIR, 'TravelPackage - FoodPlace.csv')

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1
                is_closed = bool(int(row.get('IsClosed', 0)))

                opening_time_str = row.get('Start')
                closing_time_str = row.get('End')
                
                opening_time = self.get_time_str(opening_time_str)
                closing_time = self.get_time_str(closing_time_str)

                foodplace = FoodPlace.objects.create(
                    name=row['Place'],
                    address=row['Address'],
                    description=row.get('Description', 'No Description Provided.'),
                    latitude=float(row['Latitude']),
                    longitude=float(row['Longitude']),
                    is_closed=is_closed,
                    location_type='2',
                    opening_time = opening_time,
                    closing_time = closing_time
                )

                image_path = unquote(row['Image'])
                LocationImage.objects.create(
                    location=foodplace,
                    image=image_path,
                    is_primary_image=True
                )

                tags = []  
                tag_names = ['Seafood','Vegan-friendly','Chinese','Filipino','Italian','Japanese','Korean','Takeout','Dine-in','Delivery','Cafe','Fastfood','American','Asian','Fusion','European','International']

                for tag_name in tag_names:
                    tag_value = int(row[tag_name])
                    if tag_value == 1:
                        tag, created = FoodTag.objects.get_or_create(name=tag_name)
                        tags.append(tag)
                
                foodplace.tags.set(tags)

                print("Imported " + foodplace.name)
                
        self.stdout.write(self.style.SUCCESS('Data imported successfully'))