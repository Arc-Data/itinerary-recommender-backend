import os
import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from api.models import Spot, CustomFee

class Command(BaseCommand):
    help = 'Migrate custom fee models to spot max and min fee'

    def handle(self, *args, **options):
        fees = CustomFee.objects.all()
        for fee in fees:
            spot = fee.spot
            spot.min_fee = fee.min_cost
            spot.max_fee = fee.max_cost
            spot.save()
            print(spot.name)

        self.stdout.write(self.style.SUCCESS('Migrated successfully'))