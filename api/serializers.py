from django.contrib.auth import get_user_model
from .models import *
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import make_password
from django.db.models import Avg

from datetime import datetime

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['full_name'] = user.get_full_name()
        token['set_preferences'] = user.set_preferences
        return token


#Model Serializers
class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password', 'is_superuser', 'is_staff', 'is_active', 'date_joined', 'groups', 'user_permissions', 'last_login']

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        user = get_user_model().objects.create(**validated_data)
        return user

class SpotSerializers(serializers.ModelSerializer):
    min_fee = serializers.SerializerMethodField()
    max_fee = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Spot
        fields = ('min_fee', 'max_fee', 'opening_time', 'closing_time', 'tags')

    def get_min_fee(self, obj):
        return obj.get_min_cost
    
    def get_max_fee(self, obj):
        return obj.get_max_cost

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all()] 

class FoodPlaceSerializers(serializers.ModelSerializer):
    fee = serializers.SerializerMethodField()
    class Meta:
        model = FoodPlace
        fields = ['fee']

    def get_fee(self, obj):
        query_set = Food.objects.filter(location=obj.id)

        if query_set.exists():
            price_aggregation = query_set.aggregate(min_price=models.Min('price'), max_price=models.Max('price'))
            min_price = price_aggregation.get('min_price')
            max_price = price_aggregation.get('max_price') 
        else:
            min_price = 300.0
            max_price = 300.0
        
        return {
            'min': min_price, 
            'max': max_price
        }

class FoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Food
        fields = ['id', 'item', 'price', 'image']

class AccommodationSerializers(serializers.ModelSerializer):
    class Meta:
        model = Accommodation
        fields = []

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'item', 'description', 'price', 'image']

class ReviewSerializers(serializers.ModelSerializer):
    user = UserSerializers()
    class Meta:
        model = Review
        exclude = ['location']

#Location-related Serializers
class LocationQuerySerializers(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()
    fee = serializers.SerializerMethodField()
    ratings = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ('tags', 'id', 'name', 'primary_image', 'address', 'schedule', 'fee', 'ratings')

    def get_schedule(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(id=obj.id)
            return {
                "opening": spot.opening_time,
                "closing": spot.closing_time 
            } 

        return None    
    
    def get_fee(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(id=obj.id)
            return {
                "min": spot.get_min_cost,
                "max": spot.get_max_cost
            }

        elif obj.location_type =="2" :
            query_set = Food.objects.filter(location=obj.id)

            if query_set.exists():
                price_aggregation = query_set.aggregate(min_price=models.Min('price'), max_price=models.Max('price'))
                min_price = price_aggregation.get('min_price')
                max_price = price_aggregation.get('max_price') 
            else:
                min_price = 300.0
                max_price = 300.0
        
            return {
                'min_price': min_price, 
                'max_price': max_price
            }
        
        return None

    def get_tags(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(id=obj.id)
            return [tag.name for tag in spot.tags.all()]

        return None

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary_image=True).first()

        if primary_image:
            return primary_image.image.url

        return "/media/location_images/Placeholder.png"

    def get_ratings(self, obj):
        reviews = Review.objects.filter(location_id=obj.id)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews.exists() else 0

        return {
            'total_reviews': reviews.count(),
            'average_rating': round(average_rating, 2),
        }

    
class LocationPlanSerializers(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    max_cost = serializers.SerializerMethodField()
    min_cost = serializers.SerializerMethodField()
    opening = serializers.SerializerMethodField()
    closing = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'primary_image', 'address', 'longitude', 'latitude', 'min_cost', 'max_cost', 'opening', 'closing', 'location_type']

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary_image=True).first()

        if primary_image:
            return primary_image.image.url

        return None
    
    def get_max_cost(self, obj):
        return obj.get_max_cost
            
    def get_min_cost(self, obj):
        return obj.get_min_cost

    def get_opening(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(pk=obj.id)

            if spot:
                return spot.opening_time
        return None

    def get_closing(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(pk=obj.id)

            if spot:
                return spot.closing_time
        return None

class LocationBasicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Location
        fields = '__all__'

class LocationSerializers(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()
    rating_percentages = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ('id', 'location_type', 'name', 'address', 'description', 'latitude', 'longitude',  'images', 'details', 'rating_percentages', 'is_bookmarked', 'owner')

    def get_details(self, obj):
        if obj.location_type == '1':
            serializer = SpotSerializers(Spot.objects.get(pk=obj.id))
            return serializer.data
        elif obj.location_type == '2':
            serializer = FoodPlaceSerializers(FoodPlace.objects.get(pk=obj.id))
            return serializer.data
        elif obj.location_type == '3':
            serializer = AccommodationSerializers(Accommodation.objects.get(pk=obj.id))
            return serializer.data
        
        return None
    
    def get_is_bookmarked(self, obj):
        user = self.context.get("user")
        return Bookmark.objects.filter(location=obj, user=user).exists()

    def get_rating_percentages(self, obj):
        reviews = Review.objects.filter(location_id=obj.id)

        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews.exists() else 0

        count_5_star = reviews.filter(rating=5).count()
        count_4_star = reviews.filter(rating=4).count()
        count_3_star = reviews.filter(rating=3).count()
        count_2_star = reviews.filter(rating=2).count()
        count_1_star = reviews.filter(rating=1).count()

        highest_count = max(count_5_star, count_4_star, count_3_star, count_2_star, count_1_star)

        percentage_5_star = (count_5_star / highest_count) if highest_count > 0 else 0
        percentage_4_star = (count_4_star / highest_count) if highest_count > 0 else 0
        percentage_3_star = (count_3_star / highest_count) if highest_count > 0 else 0
        percentage_2_star = (count_2_star / highest_count) if highest_count > 0 else 0
        percentage_1_star = (count_1_star / highest_count) if highest_count > 0 else 0

        rating_data = [
            {'rating': 5, 'count': count_5_star, 'percentage': percentage_5_star},
            {'rating': 4, 'count': count_4_star, 'percentage': percentage_4_star},
            {'rating': 3, 'count': count_3_star, 'percentage': percentage_3_star},
            {'rating': 2, 'count': count_2_star, 'percentage': percentage_2_star},
            {'rating': 1, 'count': count_1_star, 'percentage': percentage_1_star},
        ]

        return {
            'total_reviews': reviews.count(),
            'average_rating': round(average_rating, 2),
            'ratings': rating_data,
        }

    def get_images(self, obj):
        images = [image.image.url for image in obj.images.all()]
        
        if not images:
            default_image_url = "/media/location_images/Placeholder.png"
            return [default_image_url]

        return images


class LocationTopSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'average_rating', 'total_reviews']

    def get_average_rating(self, obj):
        reviews = Review.objects.filter(location=obj)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews.exists() else 0
        return average_rating

    def get_total_reviews(self, obj):
        return Review.objects.filter(location=obj).count()


class LocationBusinessSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'primary_image', 'name', 'address']
        
    def get_primary_image(self, obj):
        images = obj.images.filter(is_primary_image=True)

        if images:
            return images[0].image.url

        return "/media/location_images/Placeholder.png"

class LocationBusinessManageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    class Meta:
        model = Location
        exclude = []
    
    def get_image(self, obj):
        images = obj.images.filter(is_primary_image=True)

        if images:
            return images[0].image.url

        return "/media/location_images/Placeholder.png"
    
#Spot-related Serializers
class SpotDetailSerializers(serializers.ModelSerializer):
    location_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Spot
        exclude = []

    def get_location_reviews(self, obj):
        location_reviews = obj.review_set.all()
        return ReviewSerializers(location_reviews, many=True).data


class SpotPopularSerializers(serializers.ModelSerializer):

    class Meta:
        model = Spot
        fields = ['id', 'name', 'description']

#Itinerary Serializers
class ItineraryListSerializers(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    trip_duration = serializers.SerializerMethodField()

    class Meta:
        model = Itinerary 
        fields = '__all__'

    def get_image(self, object):
        days = Day.objects.filter(itinerary=object)

        for day in days:
            items = ItineraryItem.objects.filter(day=day)

            if items:
                location = items[0].location
                url = LocationImage.objects.get(is_primary_image=True, location=location).image.url
                return url

        return "/media/location_images/DefaultLocationImage.jpg"

    def get_trip_duration(self, object):
        days = Day.objects.filter(itinerary=object)

        if not days:
            return "No set duration yet"

        first_day = days.first()
        num_of_days = "days" if len(days) > 1 else "day"

        formatted_date = datetime.strptime(str(first_day.date), '%Y-%m-%d').strftime('%B %#d')

        return f"{formatted_date} • {len(days)} {num_of_days}"


class ItinerarySerializers(serializers.ModelSerializer):
    class Meta:
        model = Itinerary
        fields = ['id', 'budget', 'number_of_people', 'user', 'name']
            
    
class ItineraryItemSerializer(serializers.ModelSerializer):
    details = LocationPlanSerializers(source='location', read_only=True)

    class Meta:
        model = ItineraryItem
        fields = ['id', 'location', 'day', 'details']

class ItineraryItemNameSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()

    class Meta:
        model = ItineraryItem
        fields = ['id', 'location']

    def get_location(self, obj):
        return {'id':obj.location.id,'name': obj.location.name}

class DayDetailSerializers(serializers.ModelSerializer):
    class Meta:
        model = Day
        fields = '__all__'

class DaySerializers(serializers.ModelSerializer):
    itinerary_items = ItineraryItemSerializer(source='itineraryitem_set', many=True)
    date_status = serializers.SerializerMethodField()

    class Meta:
        model = Day
        fields = '__all__'
    
    def get_date_status(self, obj):
        current_date = timezone.now().date()
        if obj.date == current_date:
            return "ongoing"
        elif obj.date < current_date:
            return "past due"
        else:
            return "soon"


class DayRatingsSerializer(serializers.ModelSerializer):
    locations = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    day_number = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Day
        fields = ['id', 'date', 'locations', 'name', 'day_number', 'image', 'itinerary', 'completed', 'rating']

    def get_name(self, obj):
        return obj.itinerary.name

    def get_day_number(self, obj):
        return f"Day {obj.order}"

    def get_locations(self, obj):
        items = ItineraryItem.objects.filter(day=obj)

        location_names = []
        for item in items:
            location_names.append(item.location.name)

        return location_names
    
    def get_image(self, obj):
        item = ItineraryItem.objects.filter(day=obj).first()
        
        if item:
            return LocationImage.objects.get(location=item.location, is_primary_image=True).image.url

class DayRatingSerializer(serializers.ModelSerializer):
    locations = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    day_number = serializers.SerializerMethodField()

    class Meta: 
        model = Day
        fields = ['id', 'date', 'locations', 'day_number', 'name', 'completed', 'rating']

    def get_name(self, obj):
        return obj.itinerary.name

    def get_day_number(self, obj):
        return f"Day {obj.order}"

    def get_locations(self, obj):
        items = ItineraryItem.objects.filter(day=obj)

        locations = []
        for item in items:
            serializer = LocationPlanSerializers(item.location)
            locations.append(serializer.data)
        
        return locations

class CompletedDaySerializer(serializers.ModelSerializer):
    itinerary_items = serializers.SerializerMethodField()

    class Meta:
        model = Day
        fields = ['id', 'rating', 'itinerary_items']

    def get_itinerary_items(self, obj):
        itinerary_items = ItineraryItem.objects.filter(day=obj, location__location_type='1')
        return ItineraryItemNameSerializer(itinerary_items, many=True).data

class LocationRecommenderSerializers(serializers.ModelSerializer):
    fee = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'fee', 'schedule']
    
    def get_fee(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(pk=obj.id)

            if spot:
                return {
                    "min": spot.get_min_cost,
                    "max": spot.get_max_cost
                } 

        return None
    
    def get_schedule(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(pk=obj.id)

            if spot:
                return {
                    "opening": spot.opening_time,
                    "closing": spot.closing_time 
                }

        return None    

class ModelItinerarySerializers(serializers.ModelSerializer):
    locations = LocationRecommenderSerializers(many=True)

    class Meta:
        model = ModelItinerary
        fields = '__all__'

#Bookmark Serializers
class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = '__all__'

class RecentBookmarkSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ('id', 'name', 'primary_image')

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary_image=True).first()

        if primary_image:
            return primary_image.image.url

        return None
    
class BookmarkLocationSerializer(serializers.ModelSerializer):
    details = LocationQuerySerializers(source='location', read_only=True)

    class Meta:
        model = Bookmark
        fields = ['id', 'details']

class BookmarkCountSerializer(serializers.Serializer):
    location_id = serializers.IntegerField(source='id')
    bookmark_count = serializers.IntegerField()

#Recommender Serializers
class RecommendedLocationSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    ratings = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = ('id', 'name', 'primary_image', 'tags', 'ratings')

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary_image=True).first()

        if primary_image:
            return primary_image.image.url

        return None
    
    def get_tags(self, obj):
        if obj.location_type == "1":
            spot = Spot.objects.get(pk=obj.id)
        
            if spot:
                return [tag.name for tag in spot.tags.all()]
        
        return None
    
    def get_ratings(self, obj):
        reviews = Review.objects.filter(location_id=obj.id)
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews.exists() else 0

        return {
            'total_reviews': reviews.count(),
            'average_rating': average_rating
        }


#Ownership Request
class OwnershipRequestSerializer(serializers.ModelSerializer):
    details = LocationBasicSerializer(source='location', read_only=True)
    requester = UserSerializers(source='user')
    image = serializers.SerializerMethodField()

    class Meta:
        model = OwnershipRequest
        fields = ('id', 'is_approved', 'timestamp', 'details', 'requester', 'image')

    def get_image(self, obj):
        primary_image = obj.location.images.filter(is_primary_image=True).first()

        if primary_image:
            return primary_image.image.url
        return None