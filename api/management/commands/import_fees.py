import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Spot, FeeType, AudienceType

class Command(BaseCommand):
    help = 'Import fee types and audience types from CSV and associate them with spots'

    def handle(self, *args, **options):
        csv_file_path = os.path.join(settings.BASE_DIR, 'TravelPackage - Fees.csv')

        spots = Spot.objects.all()

        with open(csv_file_path, 'r') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                count += 1
                spot_name = row.get('Place')
                fee_type_name = row.get('Fee Type')
                is_required = bool(int(row.get('is_required', 0)))
                audience_name = row.get('audience')
                audience_price = float(row.get('price', 0))
                audience_description = row.get('Description', '')

                try:
                    spot = spots.get(name=spot_name)
                except Spot.DoesNotExist:
                    print("Spot not detected: ", spot_name)
                    continue
                
                fee_type, created = FeeType.objects.get_or_create(
                    spot=spot,
                    name=fee_type_name,
                    is_required=is_required
                )

                if not audience_name:
                    print(f"Row {count}: Missing audience name for spot '{spot_name}', skipping.")

                audience_type, audience_type_created = AudienceType.objects.get_or_create(
                    fee_type=fee_type,
                    name=audience_name,
                    defaults={'price': audience_price, 'description': audience_description}
                )

                if not audience_type_created:
                    print(f"Row {count}: Audience '{audience_name}' already exists for spot '{spot_name}'.")
                else:
                    print(f"Row {count}: Imported fee type '{fee_type_name}' with audience '{audience_name}' for {spot_name}")

        self.stdout.write(self.style.SUCCESS('Fee types and audience types imported successfully'))