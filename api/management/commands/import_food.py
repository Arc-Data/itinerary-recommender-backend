import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Food, FoodPlace

class Command(BaseCommand):
    help = 'Import food items from CSV and associate them with FoodPlaces'

    def handle(self, *args, **options):
        csv_file_path = os.path.join(settings.BASE_DIR, 'TravelPackage - FoodItem.csv')

        # Assuming 'Place' column in FoodItems.csv matches 'name' in FoodPlace model
        food_places = FoodPlace.objects.all()

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1
                place_name = row.get('Place')
                item_name = row.get('Item')
                price = float(row.get('Price', 0))
                image_path = row.get('Image')

                try:
                    food_place = food_places.get(name=place_name)
                except FoodPlace.DoesNotExist:
                    print("FoodPlace not detected: ", place_name)
                    continue

                # Assuming the image file already exists in the specified path
                food_item = Food.objects.create(
                    location=food_place,
                    item=item_name,
                    price=price,
                    image=image_path
                )

                print(f"Imported food item '{item_name}' for {place_name}")

        self.stdout.write(self.style.SUCCESS('Food items imported successfully'))