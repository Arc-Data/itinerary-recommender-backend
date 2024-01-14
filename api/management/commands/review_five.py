from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils import timezone
from api.models import Location, User, Review

class Command(BaseCommand):
    help = 'Create or update reviews for a location with 5-star ratings'

    def handle(self, *args, **options):
        # Prompt user for location ID
        location_id = input('Enter the ID of the location to review: ')

        try:
            location = Location.objects.get(pk=location_id)
        except Location.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Location with ID {location_id} does not exist"))
            return

        user_ids = [91, 100, 101, 102, 103]

        for user_id in user_ids:
            user = User.objects.get(pk=user_id)

            # Create or update review
            review, created = Review.objects.get_or_create(user=user, location=location, defaults={'rating': 5})
            review.comment = f"This is a test review."
            review.rating = 5
            review.datetime_created = timezone.now()
            review.save()

            self.stdout.write(self.style.SUCCESS(f"Review by {user.get_full_name()} created/updated for location '{location.name}' with a 5-star rating"))