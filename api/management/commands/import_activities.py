import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from api.models import Spot, Activity

class Command(BaseCommand):
    help = 'Add activities to existing spots based on CSV data'

    def handle(self, *args, **options):
        csv_file = os.path.join(settings.BASE_DIR, 'TravelPackage - Activities.csv')

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1

                spot_name = row['Location']

                try:
                    spot = Spot.objects.get(name=spot_name)

                    # Activities
                    activities = []
                    activity_names = ['Sightseeing', 'Swimming', 'Hiking', 'Photography', 'Island Hopping', 'Shopping', 'Meditation', 'Diving', 'Camping', 'Boating', 'Cultural Exploration', 'Movie Watching', 'Food Trip', 'Nature Walks']

                    for activity_name in activity_names:
                        activity_value = int(row.get(activity_name, 0))
                        if activity_value == 1:
                            activity, created = Activity.objects.get_or_create(name=activity_name)
                            activities.append(activity)

                    spot.activity.set(activities)

                    print(f"Added activities to {spot_name}")
                    
                except ObjectDoesNotExist:
                    raise ObjectDoesNotExist(f"Spot with name {spot_name} does not exist. Please create the spot first.")

        self.stdout.write(self.style.SUCCESS('Activities added to spots successfully'))