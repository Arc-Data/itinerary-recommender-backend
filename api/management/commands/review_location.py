from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils import timezone
from api.models import Location, User, Review

class Command(BaseCommand):
    help = 'Create or update reviews for a location with 5-star ratings'

    def add_arguments(self, parser):
        parser.add_argument('location_id', type=int, help="Location ID")
        parser.add_argument('rating', type=int, help="Desired Location Rating")

    def handle(self, *args, **options):
        # Prompt user for location ID
        location_id = options['location_id']
        rating = options['rating']

        if rating > 5 or rating < 1:
            self.stderr.write(self.style.ERROR(f"Invalid rating"))
            return  

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Location with ID {location_id} does not exist"))
            return

        if settings.DEV_MODE == "PRODUCTION":
            user_ids = [91, 100, 101, 102, 103]
        else:
            user_ids = [34, 33, 31]

        for user_id in user_ids:
            user = User.objects.get(pk=user_id)

            review, created = Review.objects.get_or_create(user=user, location=location, defaults={'rating': rating})
            review.comment = f"This is a test review."
            review.rating = rating
            review.datetime_created = timezone.now()
            review.save()

            self.stdout.write(self.style.SUCCESS(f"Review by {user.get_full_name()} created/updated for location '{location.name}' with a {rating}-rating rating"))