import os, csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Spot, ModelItinerary, ModelItineraryLocationOrder

class Command(BaseCommand):
    help = "Import data from CSV to ModelItinerary Model"

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, 'TravelPackage - ModelItinerary.csv')

        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            
            for idx, row in enumerate(reader, start=1):
                locations = [loc.strip() for loc in row[0].split(',') if loc.strip()]
                spots = []

                for location in locations:
                    try:
                        spot = Spot.objects.get(name=location)
                        spots.append(spot)
                    except Spot.DoesNotExist:
                        print("Location not detected: ", location)

                # print(spots[4], spots[9])
                model_itinerary = ModelItinerary.objects.create()
                print(idx, [spot.id for spot in spots])
                
                for order, spot in enumerate(spots):
                    print(spot)
                    ModelItineraryLocationOrder.objects.create(
                        itinerary=model_itinerary,
                        spot=spot,
                        order=order
                    )
                