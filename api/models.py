from collections import defaultdict
from datetime import timedelta, date
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.db.models.signals import post_save
from .managers import CustomUserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models import Count, Avg
from haversine import haversine, Unit
from django.core.validators import MaxValueValidator, MinValueValidator

import os, math

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    requires_otp = models.BooleanField(default=False)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    set_preferences = models.BooleanField(default=False)
    contact_number = models.CharField(max_length=11, default="09202750407")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'auth_user'

    def get_full_name(self):
        return self.first_name + " " + self.last_name


class Preferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    art = models.BooleanField(default=False)
    activity = models.BooleanField(default=False)
    culture = models.BooleanField(default=False)
    entertainment = models.BooleanField(default=False)
    history = models.BooleanField(default=False)
    nature = models.BooleanField(default=False)
    religion = models.BooleanField(default=False)
         
    def __str__(self):
        return self.user.email

@receiver(post_save, sender=User)
def create_preferences(sender, instance, created, **kwargs):
   if created:
       Preferences.objects.create(
           user=instance,
       ) 

@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    instance.preferences.save()

class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)  

    def mark_as_used(self):
        self.used = True
        self.save()

class Location(models.Model):
    owner = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=250, unique=True)
    address = models.CharField(max_length=250)
    description = models.CharField(default="No Description Provided.", max_length=1200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_type = models.CharField(
        max_length=1,
        choices=[
            ('1', 'Spot'),
            ('2', 'FoodPlace'),
            ('3', 'Accommodation'),
        ],
        default=1
    )
    is_closed = models.BooleanField(default=False)
    website = models.CharField(blank=True, null=True, default="")
    email = models.EmailField(blank=True, null=True, default="")
    contact = models.CharField(max_length=15, blank=True, null=True, default="")

    def get_distance_from_origin(self, origin_spot):
        spot_coordinates = (self.latitude, self.longitude)
        origin_coordinates = (origin_spot.latitude, origin_spot.longitude)
        return haversine(spot_coordinates, origin_coordinates, unit=Unit.METERS)

    @property
    def get_avg_rating(self):
        avg_rating = self.review_set.aggregate(Avg('rating'))['rating__avg']
        return avg_rating if avg_rating is not None else 0.0

    @property
    def get_num_ratings(self):
        return self.review_set.count()
        

    @property
    def get_min_cost(self):
        if self.location_type == "1":
            spot = Spot.objects.get(id=self.id)
            return spot.get_min_cost

        elif self.location_type == "2":
            foodplace = FoodPlace.objects.get(id=self.id)
            return foodplace.get_min_cost

        return 0

    @property    
    def get_max_cost(self):
        if self.location_type == "1":
            spot = Spot.objects.get(id=self.id)
            return spot.get_max_cost

        elif self.location_type == "2":
            foodplace = FoodPlace.objects.get(id=self.id)
            return foodplace.get_max_cost

        return 0
    
    def save(self, *args, **kwargs):
        super(Location, self).save(*args, **kwargs)

        if self.location_type == '1' and not hasattr(self, 'spot'):
            spot = Spot(location_ptr=self)
            spot.__dict__.update(self.__dict__)
            spot.save()
        elif self.location_type == '2' and not hasattr(self, 'foodplace'):
            foodplace = FoodPlace(location_ptr=self)
            foodplace.__dict__.update(self.__dict__)
            foodplace.save()
        elif self.location_type == '3' and not hasattr(self, 'accommodation'):
            accommodation = Accommodation(location_ptr=self)
            accommodation.__dict__.update(self.__dict__)
            accommodation.save()

    @property
    def nearby_events(self, radius_meters=750):
        current_date = timezone.now().date()

        nearby_events = Event.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date
        )

        spot_coordinates = (self.latitude, self.longitude)
        nearby_events = [
            event for event in nearby_events
            if haversine(spot_coordinates, (event.latitude, event.longitude), unit=Unit.METERS) <= radius_meters
        ]
        # print(nearby_events)

        return nearby_events

    def __str__(self):
        return self.name

class OwnershipRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey("Location", on_delete=models.CASCADE)
    datetime_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'location')
        ordering = ['-datetime_created']

    def __str__(self):
        return f"{self.user.get_full_name()} bookmarked {self.location.name}"

def location_image_path(instance, filename):
    ext = filename.split('.')[-1]
    folder_name = instance.location.name.replace(" ", "_")
    filename = f"{instance.location.name}.{ext}"
    return os.path.join('location_images', folder_name, filename)


class LocationImage(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=location_image_path, default='location_images/DefaultLocationImage.jpg', max_length=512)
    is_primary_image = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.location.name}"

class Spot(Location):
    expected_duration = models.DurationField(default=timedelta(hours=1))
    tags = models.ManyToManyField("Tag", related_name="spots")
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
    activity = models.ManyToManyField("Activity", related_name="spots")

    def __str__(self):
        return self.name

    @property
    def get_min_cost(self):
        all_fee_types = self.feetype_set.filter(is_required=True)
        all_audience_types = AudienceType.objects.filter(fee_type__in=all_fee_types)

        if all_audience_types.exists():
            min_audience_type = min(all_audience_types, key=lambda at: at.price)
            return min_audience_type.price
        else:
            return 0

    @property
    def get_max_cost(self):
        required_fee_types = self.feetype_set.filter(is_required=True)
        optional_fee_types = self.feetype_set.filter(is_required=False)

        total_optional_fee_price = sum(
            audience_type.price
            for fee_type in optional_fee_types
            for audience_type in fee_type.audience_types.all()
        )

        if required_fee_types.exists():
            max_required_fee = max(
                audience_type.price
                for fee_type in required_fee_types
                for audience_type in fee_type.audience_types.all()
            )
            return max_required_fee + total_optional_fee_price
        else:
            return 0
        
    @property 
    def get_activities(self):
        return [activity.name for activity in self.activity.all()]


class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    
class FoodTag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class FoodPlace(Location):
    tags = models.ManyToManyField("FoodTag", related_name="foodplaces")
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)
 
    def save(self, *args, **kwargs):
        self.location_type = '2'
        super(FoodPlace, self).save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    def get_distance_from_origin(self, origin_foodplace):
        foodplace_coordinates = (self.latitude, self.longitude)
        origin_coordinates = (origin_foodplace.latitude, origin_foodplace.longitude)
        return haversine(foodplace_coordinates, origin_coordinates, unit=Unit.METERS)
    
    @property
    def get_min_cost(self):
        min_food = Food.objects.filter(location=self).order_by('price').first()
        if min_food is not None and hasattr(min_food, 'price'):
            return min_food.price
        else:
            return 300.0

    @property
    def get_max_cost(self):
        max_food = Food.objects.filter(location=self).order_by('-price').first()

        if max_food is not None and hasattr(max_food, 'price'):
            return max_food.price
        else:
            return 300.0

    @property 
    def get_foodtags(self):
        return [tag.name for tag in self.tags.all()]

    

class Accommodation(Location):

    def save(self, *args, **kwargs):
        self.location_type = '3'
        super(Accommodation, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class Itinerary(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    number_of_people = models.PositiveIntegerField(default=1)
    budget = models.FloatField(default=0)
    name = models.CharField(max_length=60, default="My Trip")
    
    class Meta:
        ordering = ['-id']

class Day(models.Model):
    date = models.DateField()
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE)
    color = models.CharField(max_length=7, default="#184E77")
    completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    rating = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['date']

class ItineraryItem(models.Model):
    day = models.ForeignKey(Day, on_delete=models.CASCADE, null=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.day.date} - {self.location.name} - {self.order}"

    def get_transportation_type(self):
        if self.order == 0:
            return 0
        else:
            previous_item = ItineraryItem.objects.get(order=self.order - 1, day=self.day)
            previous_location = previous_item.location
            distance = self.location.get_distance_from_origin(previous_location)
            print(distance)
            print(self.order, self.location.name, previous_location.name, distance)


            if self.location.location_type == '1':
                spot = Spot.objects.get(id=self.location.id)
                if previous_location.location_type == '1':
                    previous_spot = Spot.objects.get(id=previous_location.id)
                    if previous_spot.activity.filter(name="Boating").exists() or previous_spot.activity.filter(name="Island Hopping").exists():
                        print("Other Transportation (Boat, Mixed, etc.)")
                        return {
                            "name": "Other Transportation (Boat, Mixed, etc.)", 
                            "meters": distance
                        }
                # consider din dapat kung spot ba yung previous location
                # if previous_location.activity.filter()
                elif  spot.activity.filter(name="Boating").exists() or spot.activity.filter(name="Island Hopping").exists(): 
                    print("Other Transportation (Boat, Mixed, etc.)")
                    return {
                        "name": "Other Transportation (Boat, Mixed, etc.)",
                        "meters": distance
                    }
            if distance <= 500:
                return {
                    "name": "Walk",
                    "meters": distance
                }
            else:  
                return {
                    "name": "Car",
                    "meters": distance
                }

class ModelItineraryLocationOrder(models.Model):
    itinerary = models.ForeignKey("ModelItinerary", on_delete=models.CASCADE)
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']

class ModelItinerary(models.Model):
    locations = models.ManyToManyField("Spot")

    @property
    def total_min_cost(self):
        location_orders = self.modelitinerarylocationorder_set.all().order_by('order')
        return sum(location_order.spot.get_min_cost for location_order in location_orders)

    @property
    def total_max_cost(self):
        location_orders = self.modelitinerarylocationorder_set.all().order_by('order')
        return sum(location_order.spot.get_max_cost for location_order in location_orders)

    # @property
    # def get_tags(self):
    #     tags_list = []

    #     for location_order in self.modelitinerarylocationorder_set.all().order_by('order'):
    #         location = location_order.spot
    #         if location.location_type == '1':
    #             tags_list.extend(tag.name for tag in location.tags.all())

    #     return set(tags_list)

    @property
    def get_tags(self):
        return set(tag.name for location_order in self.modelitinerarylocationorder_set.all().order_by('order')
                if location_order.spot.location_type == '1'
                for tag in location_order.spot.tags.all())
   
    @property
    def get_activities(self):
        activities = defaultdict(int)
        for order in self.modelitinerarylocationorder_set.all():
            spot_activities = order.spot.get_activities

            for activity in spot_activities:
                activities[activity] += 1

        return activities

    @property
    def get_location_names(self):
        location_orders = self.modelitinerarylocationorder_set.all().order_by('order')
        return [location_order.spot.name for location_order in location_orders]

class Review(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True)
    comment = models.TextField()
    rating = models.PositiveIntegerField()
    datetime_created = models.DateTimeField(auto_now_add=True)

class Food(models.Model):
    location = models.ForeignKey(FoodPlace, on_delete=models.CASCADE)
    item = models.CharField(max_length=100)
    price = models.FloatField()
    image = models.ImageField(blank=True, null=True, upload_to='location_food/')

class Service(models.Model):
    location = models.ForeignKey(Accommodation, on_delete=models.CASCADE)
    item = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    price = models.FloatField()
    image = models.ImageField(blank=True, null=True, upload_to='location_service/')


class Event(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.CharField(max_length=900)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['start_date']
    

class Activity(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    
class FeeType(models.Model):
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} Fee - Spot: {self.spot}"

class AudienceType(models.Model):
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE, related_name='audience_types')
    name = models.CharField(max_length=50)
    price = models.FloatField()
    description = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - Price: {self.price} - FeeType: {self.fee_type}"
    
class Driver(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True, default="")
    contact = models.CharField(max_length=15, default="")
    facebook = models.CharField(max_length=60, blank=True, null=True, default="")
    additional_information = models.CharField(default="No Description Provided.", max_length=500)

    car = models.CharField(max_length=30)
    car_type = models.CharField(
        max_length=1,
        choices=[
            ('1', 'Sedan'),
            ('2', 'Van'),
            ('3', 'SUV'),
        ],
        default=1
    )
    max_capacity = models.PositiveIntegerField(
        default=1,
        validators=[
            MaxValueValidator(12),
            MinValueValidator(1)
        ]
    )
    plate_number = models.CharField(max_length=7)
    image = models.ImageField(blank=True, null=True, upload_to='drivers/', default='drivers/DefaultDriverImage.png')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class ContactForm(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.CharField(max_length=220)
    date_created = models.DateTimeField(auto_now_add=True)
    admin_responded = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_created']

@receiver(post_save, sender=Spot)
def create_default_fee(sender, instance, created, **kwargs):
    if created:
        FeeType.objects.create(spot=instance, name="Entrance Fee")
        print("Created Default Fee Type for location: ", instance.name)

@receiver(post_save, sender=FeeType)
def create_default_audience_type(sender, instance, created, **kwargs):
    if created:
        AudienceType.objects.create(fee_type=instance, name="General", price=0)
        print("Created Default Audience Type")