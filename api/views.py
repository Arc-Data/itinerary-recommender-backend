from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated

from .managers import *
from .models import *
from .serializers import *

import datetime
import numpy as np

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserRegistrationView(CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)

class LocationPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationQuerySerializers
    filter_backends = [SearchFilter]
    search_fields = ['name']

    action = {
        'list': 'list',
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('query', None)
        hide = self.request.query_params.get('hide', None) 


        if query:
            queryset = queryset.filter(name__istartswith=query)

        if hide:
            queryset = queryset.filter(is_closed=False)

        queryset = queryset.exclude(location_type=3)

        return queryset

class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationQuerySerializers
    filter_backends = [SearchFilter]
    search_fields = ['name']

    action = {
        'list': 'list',
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('query', None)
        hide = self.request.query_params.get('hide', None) 
        location_type = self.request.query_params.get('type', None)

        if query:
            queryset = queryset.filter(name__istartswith=query)

        if hide:
            queryset = queryset.filter(is_closed=False)

        if location_type and location_type != "null": 
            if location_type == "spot":
                queryset = queryset.filter(location_type=1)
            elif location_type == "foodplace":
                queryset = queryset.filter(location_type=2)
            elif location_type == "accommodation":
                queryset = queryset.filter(location_type=3)
            
        
        return queryset
    
class CustomNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

class PaginatedLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationQuerySerializers
    filter_backends = [SearchFilter]
    search_fields = ['name']
    pagination_class = CustomNumberPagination

    action = {
        'list': 'list',
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('query', None)
        hide = self.request.query_params.get('hide', None) 
        location_type = self.request.query_params.get('type', None)

        if query:
            queryset = queryset.filter(name__istartswith=query)

        if hide:
            queryset = queryset.filter(is_closed=False)

        if location_type:
            if location_type == "spot":
                queryset = queryset.filter(location_type=1)
            elif location_type == "foodplace":
                queryset = queryset.filter(location_type=2)
            elif location_type == "accommodation":
                queryset = queryset.filter(location_type=3)

        return queryset
    
@api_view(['GET'])
def get_related_days(request, itinerary_id):
    itinerary = Itinerary.objects.get(id=itinerary_id)

    days = Day.objects.filter(itinerary=itinerary)
    day_serializer = DaySerializers(days, many=True)

    return Response(day_serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_itinerary_list(request):
    user = request.user
    itineraries = Itinerary.objects.filter(user=user)
    serializer = ItineraryListSerializers(itineraries, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_itinerary(request, itinerary_id):
    try:
        itinerary = Itinerary.objects.get(id=itinerary_id)
    except Itinerary.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.user != itinerary.user:
        return Response({'message': "Access Denied"}, status=status.HTTP_403_FORBIDDEN)

    itinerary_serializer = ItinerarySerializers(itinerary)

    return Response(itinerary_serializer.data, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_itinerary(request, itinerary_id):
    itinerary = Itinerary.objects.get(id=itinerary_id)

    if not itinerary:
        return Response(status=status.HTTP_404_NOT_FOUND)

    itinerary.delete()
    
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_ordering(request):
    items = request.data.get("items")

    for order, item in enumerate(items):
        itinerary_item = ItineraryItem.objects.get(id=item["id"])
        itinerary_item.order = order
        itinerary_item.save()

    return Response({'message': 'Ordering Updated Successfully'}, status=status.HTTP_200_OK)

@api_view(["PATCH"])
def edit_itinerary_name(request, itinerary_id):
    name = request.data.get("name")
    itinerary = Itinerary.objects.get(id=itinerary_id)
    itinerary.name = name
    itinerary.save()

    return Response(status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_location(request, id):
    user = request.user
    try:
        location = Location.objects.get(pk=id)
    except Location.DoesNotExist:
        return Response({'error': 'Location not found'}, status=404)

    serializer = LocationSerializers(location, context={'user': user})
    data = serializer.data

    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_itinerary(request):
    start_date = request.data.get('start_date') 
    end_date = request.data.get('end_date')  

    itinerary_data = {
        'user': request.user.id,  
        'number_of_people': request.data.get('number_of_people', 1),
        'budget': request.data.get('budget', 0),
    }
    itinerary_serializer = ItinerarySerializers(data=itinerary_data)

    if itinerary_serializer.is_valid():
        itinerary = itinerary_serializer.save()
        current_date = datetime.datetime.strptime(start_date, '%m/%d/%Y')
        end_date = datetime.datetime.strptime(end_date, '%m/%d/%Y')
        
        order = 1
        while current_date <= end_date:
            Day.objects.create(
                date=current_date,
                itinerary=itinerary,
                order=order
            )

            order = order + 1
            current_date += timedelta(days=1)
        
        return Response({'id': itinerary.id}, status=status.HTTP_201_CREATED)

    return Response(itinerary_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_day_item(request, day_id):
    try:
        item = ItineraryItem.objects.get(pk=day_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except ItineraryItem.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
def create_itinerary_item(request):
    day_id = request.data.get("day")
    location_id = request.data.get("location")
    order = request.data.get("order")

    try:
        location = Location.objects.get(pk=location_id)
    except Location.DoesNotExist:
        return Response({"error": "Location not found"}, status=status.HTTP_404_NOT_FOUND)

    itinerary_item = ItineraryItem.objects.create(day_id=day_id, location=location, order=order)
    serializer = ItineraryItemSerializer(itinerary_item)

    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET"])
def location(request):
    if request.method == "GET":
        location = Location.objects.all()
        serializer = LocationQuerySerializers(location, many=True)
        return Response(serializer.data)
    
@api_view(["GET"])
def spot(request, pk):
    if request.method == "GET":
        spot = get_object_or_404(Spot, id=pk)
        serializer = SpotDetailSerializers(spot)
        return Response(serializer.data)

@api_view(["PATCH"]) 
@permission_classes([IsAuthenticated])
def update_preferences(request):
    user = request.user
    preferences = user.preferences

    preferences.art = request.data.get("Art")
    preferences.activity = request.data.get("Activity")
    preferences.culture = request.data.get("Culture")
    preferences.entertainment = request.data.get("Entertainment")
    preferences.history = request.data.get("History")
    preferences.nature = request.data.get("Nature")
    preferences.religion = request.data.get("Religion")

    preferences.save()

    user.set_preferences = True
    user.save()

    return Response({'message': "Preferences Updated Successfully"}, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_content_recommendations(request):
    user = request.user

    preferences = [
        user.preferences.history,
        user.preferences.nature,
        user.preferences.religion,
        user.preferences.art, 
        user.preferences.activity,
        user.preferences.entertainment,
        user.preferences.culture
    ]

    preferences = np.array(preferences, dtype=int)

    manager = RecommendationsManager()
    recommendation_ids = manager.get_content_recommendations(preferences)

    recommendations = []
    for id in recommendation_ids:
        recommendation = ModelItinerary.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = ModelItinerarySerializers(recommendations, many=True)

    return Response({
        'recommendations': recommendation_serializers.data
        }, status=status.HTTP_200_OK)

@api_view(["POST"])
def update_itinerary_calendar(request, itinerary_id):
    start_date = request.data.get("startDate")
    end_date = request.data.get("endDate")

    itinerary = Itinerary.objects.get(pk=itinerary_id)
    Day.objects.filter(itinerary=itinerary).delete()

    start_date = datetime.datetime.strptime(start_date, '%m/%d/%Y').date()
    end_date = datetime.datetime.strptime(end_date, '%m/%d/%Y').date()

    days = []

    while start_date <= end_date:
        day = Day.objects.create(
            date=start_date,
            itinerary=itinerary
        )

        days.append(day)
        start_date += timedelta(days=1)


    day_serializers = DaySerializers(days, many=True)

    return Response({
        'message': "Calendar Updated Successfully",
        'days': day_serializers.data
        }, status=status.HTTP_200_OK)

@api_view(["POST"]) 
def apply_recommendation(request, model_id):
    day_id = request.data.get("day_id")
    day = Day.objects.get(id=day_id)

    ItineraryItem.objects.filter(day=day).delete()

    model = ModelItinerary.objects.get(id=model_id)

    items = []
    for idx, location in enumerate(model.locations.all()):
        item = ItineraryItem.objects.create(
            day=day,
            location=location,
            order=idx
        )
        items.append(item)

    day_serializer = DaySerializers(day)

    return Response({
        'message': 'Successfully applied recommendation',
        'day': day_serializer.data
        }, status=status.HTTP_200_OK)

@api_view(["POST"])
def edit_day_color(request, day_id):
    color = request.data.get("color")
    day = Day.objects.get(id=day_id)
    day.color = color
    day.save()

    day_serializer = DaySerializers(day)

    return Response({
        'message': "Updated Day Color Successfully",
        'day': day_serializer.data
        }, status=status.HTTP_200_OK)

@api_view(["DELETE"])
def delete_day(request, day_id):
    try:
        print("Im here")
        day = Day.objects.get(id=day_id)
        day.delete()
        return Response({
            'message': "Delete Success"
        }, status=status.HTTP_204_NO_CONTENT)
    except Day.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_location_reviews(request, location_id):
    user = request.user 
    if request.method == "GET":
        paginator = PageNumberPagination()
        paginator.page_size = 5

        reviews = Review.objects.filter(location_id=location_id).exclude(user=user).order_by('-datetime_created')
        result_page = paginator.paginate_queryset(reviews, request)
        review_serializer = ReviewSerializers(result_page, many=True)
        
        return paginator.get_paginated_response(review_serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_review(request, location_id):
    review = Review.objects.filter(location_id=location_id, user=request.user).first()
    if review:
        review_serializer = ReviewSerializers(review)
        return Response(review_serializer.data, status=status.HTTP_200_OK)

    return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bookmarks(request):
    user = request.user
    bookmarks = Bookmark.objects.filter(user=user)

    serializer = BookmarkLocationSerializer(bookmarks, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bookmark(request, location_id):
    user = request.user
    location = Location.objects.get(id=location_id)
    existing_bookmark = Bookmark.objects.filter(user=user, location=location).first()

    if existing_bookmark:
        existing_bookmark.delete()
        return Response({'message': 'Bookmark deleted.'}, status=status.HTTP_200_OK)
    else:
        Bookmark.objects.create(user=user, location=location)
        return Response({'message': 'Bookmark added.'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, location_id):
    comment = request.data.get("comment")
    rating = request.data.get("rating")

    existing_review = Review.objects.filter(user=request.user, location_id=location_id).first()
    if existing_review:
        return Response({'error': 'Review already exists for this location and user.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        review = Review.objects.create(
            user=request.user,
            location_id=location_id,
            comment=comment,
            rating=rating
        )
        serializers = ReviewSerializers(review)
        return Response(serializers.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': f'Error creating review: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_review(request, location_id):
    try:
        review = Review.objects.get(location_id=location_id, user=request.user)

        review.comment = request.data.get('comment', review.comment)
        review.rating = request.data.get('rating', review.rating)
        review.save()

        review_serializer = ReviewSerializers(instance=review)

        return Response(review_serializer.data, status=status.HTTP_200_OK)
    except Review.DoesNotExist:
        return Response({'message': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'message': f'Error updating review: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_review(request, location_id):
    try:
        review = Review.objects.get(location_id=location_id, user=request.user)
        review.delete()
        return Response({'message': 'Review deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
    except Review.DoesNotExist:
        return Response({'message': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_location(request):
    location_type = request.data.get("type")
    name = request.data.get("name")
    address = request.data.get("address")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")
    description = request.data.get("description")
    image = request.data.get("image")

    location = Location.objects.create(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        description=description,
        location_type=location_type,
        is_closed=True
    )

    if location_type == 1:
        spot = Spot.objects.get(id=location.id)
        spot.min_fee = request.data.get("min_fee", spot.min_fee)
        spot.max_fee = request.data.get("max_fee", spot.max_fee)
        spot.opening_time = request.data.get("opening_time", spot.opening_time)
        spot.closing_time = request.data.get("min_fee", spot.closing_time)
        spot.save()

    if image:
        LocationImage.objects.create(
            image=image,
            location=location,
            is_primary_image=True
        )

    serializer = LocationSerializers(location)
    data = serializer.data

    response_data = {
        'id': data['id'],
        'message': "Created successfully",
    }

    return Response(status=status.HTTP_200_OK)

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(["PATCH"])
def edit_location(request, id):
    location_type = request.data.get("type")
    name = request.data.get("name")
    address = request.data.get("address")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")
    description = request.data.get("description")

    location = Location.objects.get(id=id)
    
    location.type = location_type
    location.name = name
    location.address = address
    location.latitude = latitude
    location.longitude = longitude
    location.description = description

    location.save()

    return Response(status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_location(request, id):
    try:
        location = Location.objects.get(id=id)
        location.delete()   
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Location.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_location_recommendations(request, location_id):
    user = request.user 
    manager = RecommendationsManager()
    recommendation_ids = manager.get_location_recommendation(user, location_id)

    recommendations = []
    for id in recommendation_ids:
        recommendation = Location.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = RecommendedLocationSerializer(recommendations, many=True)

    return Response({
        'recommendations': recommendation_serializers.data
        }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_homepage_recommendations(request):
    user = request.user
    visited_list = set()

    itineraries = Itinerary.objects.filter(user=user)

    preferences = [
        int(user.preferences.history),
        int(user.preferences.nature),
        int(user.preferences.religion),
        int(user.preferences.art), 
        int(user.preferences.activity),
        int(user.preferences.entertainment),
        int(user.preferences.culture)
    ]

    for itinerary in itineraries:
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            items = ItineraryItem.objects.filter(day=day)
            visited_list.update(item.location.id for item in items)

    visited_list = set(visited_list)

    manager = RecommendationsManager()
    recommendation_ids = manager.get_homepage_recommendation(user, preferences, visited_list)

    recommendations = []
    for id in recommendation_ids:
        recommendation = Location.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = RecommendedLocationSerializer(recommendations, many=True)

    return Response({
        'recommendations': recommendation_serializers.data
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    if request.method == 'GET':
        users = User.objects.filter(is_superuser=False)
        serializer = UserSerializers(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.delete()   
        return Response(status=status.HTTP_204_NO_CONTENT)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user_serializer = UserSerializers(user)
        data = user_serializer.data
        return Response(data)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_ownership_request(request):
    user = request.user
    print(user)

    name = request.data.get('name')
    address = request.data.get('address')
    longitude = request.data.get('longitude')
    latitude = request.data.get('latitude')
    location_type = request.data.get('type')
    website = request.data.get('website')
    contact = request.data.get('contact')
    email = request.data.get('email')
    image = request.data.get('image')

    print(image)

    location = Location.objects.create(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        location_type=location_type,
        website=website,
        contact=contact,
        email=email
    )

    OwnershipRequest.objects.create(
        user=user,
        location=location
    )

    if image:
        LocationImage.objects.create(
            image=image,
            location=location,
            is_primary_image=True
        )

    return Response(status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ownership_requests(request):
    user = request.user
    requests = OwnershipRequest.objects.filter(user=user, is_approved=False)
    serializers = OwnershipRequestSerializer(requests, many=True)

    return Response(serializers.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_ownership_requests(request):
    requests = OwnershipRequest.objects.filter(is_approved=False)
    print(requests)
    serializer = OwnershipRequestSerializer(requests, many=True)
    print(serializer.data)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def approve_request(request, request_id):
    approval_request = OwnershipRequest.objects.get(id=request_id)
    approval_request.is_approved=True
    approval_request.save()

    user = approval_request.user
    location = approval_request.location
    location.owner = user
    location.save()

    return Response(status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_day_as_completed(request, day_id):
    day = Day.objects.get(id=day_id)
    day.completed = False if day.completed else True
    day.save()

    return Response(status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_completed_days(request):
    user = request.user
    itineraries = Itinerary.objects.filter(user=user)
    completed_days = []

    for itinerary in itineraries:
        days = Day.objects.filter(itinerary=itinerary)

        for day in days:
            if ItineraryItem.objects.filter(day=day).count() != 0:
                completed_days.append(day)

    serializer = DayRatingsSerializer(completed_days, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_completed_day(request, day_id):
    day = Day.objects.get(id=day_id)

    serializers = DayRatingSerializer(day)
    return Response(serializers.data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
def mark_day_complete(request, day_id):
    day = Day.objects.get(id=day_id)
    day.completed = True
    day.save()

    serializer = DayRatingSerializer(day)
    return Response(serializer.data,status=status.HTTP_200_OK)

@api_view(['PATCH'])
def mark_days_complete(request):
    ids = request.data.get('ids')
    
    for id in ids:
        day = Day.objects.get(id=id)
        day.completed = True 
        day.save()

    return Response(status=status.HTTP_200_OK)

@api_view(["POST"])
def rate_day(request, day_id):
    rating = request.data

    day = Day.objects.get(id=day_id)
    day.rating = rating
    day.save()

    serializer = DayRatingSerializer(day)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_active_trips(request):
    user = request.user
    itineraries = Itinerary.objects.filter(user=user)
    current_date = datetime.datetime.now().date()

    days = []
    for itinerary in itineraries:
        matching_days = Day.objects.filter(itinerary=itinerary, date__lte=current_date, completed=False)
        matching_days = matching_days.annotate(num_items=Count('itineraryitem')).filter(num_items__gt=0)

        days.extend(matching_days)

    serializer = DayRatingsSerializer(days, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_business(request):
    user = request.user
    location = Location.objects.filter(owner=user)
    serializer = LocationBusinessSerializer(location, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_specific_business(request, location_id):
    user = request.user
    try: 
        if user.is_staff:
            location = Location.objects.get(id=location_id)
        else:
            location = Location.objects.get(owner=user, id=location_id)
    except (Location.DoesNotExist):
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)
    
    if location.location_type == "1":
        spot = Spot.objects.get(id=location_id)
        serializer = SpotBusinessManageSerializer(spot)
        return Response({'business': serializer.data}, status=status.HTTP_200_OK)
    
    serializer = LocationBusinessManageSerializer(location)
    return Response({'business': serializer.data}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_business(request, location_id):
    user = request.user
    try:
        if user.is_staff:
            location = Location.objects.get(id=location_id)
        else:
            location = Location.objects.get(owner=user, id=location_id)
    except Location.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    location.name = request.data.get('name', location.name)
    location.address = request.data.get('address', location.address)
    location.longitude = request.data.get('longitude', location.longitude)
    location.latitude = request.data.get('latitude', location.latitude)
    location.description = request.data.get('description', location.description)
    location.save()

    if request.data.get('location_type') == "1":
        spot = Spot.objects.get(id=location_id)
        
        spot.opening_time = request.data.get('opening_time', spot.opening_time)
        spot.closing_time = request.data.get('closing_time', spot.closing_time)
        spot.description = request.data.get('description', spot.description)
        spot.min_fee = request.data.get('min_fee', spot.min_fee)
        spot.max_fee = request.data.get('max_fee', spot.max_fee)
        spot.save()    

    return Response(status=status.HTTP_200_OK)


    # location.website = request.data.get('website', location.website)
    # location.contact = request.data.get('contact', location.contact)
    # location.email = request.data.get('email', location.email)
    



@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user_business(request, location_id):
    user = request.user
    try: 
        location = Location.objects.filter(owner=user, id=location_id)
    except (Location.DoesNotExist):
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)
    location.delete()
    return Response(status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_set_preferences(request):
    return request.user.set_preferences


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_food(request, location_id):
    try:
        location = FoodPlace.objects.get(id=location_id, owner=request.user)
    except FoodPlace.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    item = request.data.get('item')
    price = request.data.get('price')
    image = request.FILES.get('image')

    food = Food.objects.create(
        location=location,
        item=item,
        price=price,
        image=image,
    )

    serializer = FoodSerializer(food)
    print(serializer.data)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_food(request, location_id, food_id):
    try:
        location = FoodPlace.objects.get(id=location_id, owner=request.user)
        food = Food.objects.get(id=food_id, location=location)
    except (FoodPlace.DoesNotExist, Food.DoesNotExist):
        return Response({"error": "Food or Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    food.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_details(request, location_id):
    try:
        location = FoodPlace.objects.get(id=location_id)
    except FoodPlace.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    foods = Food.objects.filter(location=location)
    serializer = FoodSerializer(foods, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_preference_percentages(request):
    preferences_count = Preferences.objects.aggregate(
        total_users=Count('user'),
        art_users=Count('user', filter=models.Q(art=True)),
        activity_users=Count('user', filter=models.Q(activity=True)),
        culture_users=Count('user', filter=models.Q(culture=True)),
        entertainment_users=Count('user', filter=models.Q(entertainment=True)),
        history_users=Count('user', filter=models.Q(history=True)),
        nature_users=Count('user', filter=models.Q(nature=True)),
        religion_users=Count('user', filter=models.Q(religion=True))
    )

    preference_percentages = {}
    total_users = preferences_count['total_users']
    for preference, count in preferences_count.items():
        if preference != 'total_users' and preference.endswith('_users'):
            preference_name = preference[:-6]
            preference_percentages[preference_name] = (count / total_users) * 100

    return Response({'preference_percentages': preference_percentages}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_counts(request):
    user_count = User.objects.count()
    location_count = Location.objects.count()
    spot_count = Spot.objects.count()
    accommodation_count = Accommodation.objects.count()
    food_place_count = FoodPlace.objects.count()
    itinerary_count = Itinerary.objects.count()

    counts = {
        'user_count': user_count,
        'location_count': location_count,
        'spot_count': spot_count,
        'accommodation_count': accommodation_count,
        'food_place_count': food_place_count,
        'itinerary_count': itinerary_count,
    }

    return Response({'dashboard_datacount':counts}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_top_spots(request):
    top_spots = Spot.objects.annotate(
        average_rating=Avg('review__rating'),
        total_reviews=Count('review')
    ).exclude(total_reviews=0).order_by('-average_rating', '-total_reviews')[:10]

    spots = LocationTopSerializer(top_spots, many=True)
    return Response({'top_spots': spots.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_top_accommodations(request):
    top_accommodations = Accommodation.objects.annotate(
        average_rating=Avg('review__rating'),
        total_reviews=Count('review')
    ).exclude(total_reviews=0).order_by('-average_rating', '-total_reviews')[:10]

    accommodations = LocationTopSerializer(top_accommodations, many=True)
    return Response({'top_accommodations': accommodations.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_top_foodplaces(request):
    top_food_places = FoodPlace.objects.annotate(
        average_rating=Avg('review__rating'),
        total_reviews=Count('review')
    ).exclude(total_reviews=0).order_by('-average_rating', '-total_reviews')[:10]

    food_places = LocationTopSerializer(top_food_places, many=True)
    return Response({'top_food_places': food_places.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_top_bookmarks(request):
    top_bookmarked_locations = (
        Location.objects.annotate(bookmark_count=Count('bookmark'))
            .filter(bookmark_count__gt=0)
            .order_by('-bookmark_count')[:10]
    )
    serializer = BookmarkCountSerializer(top_bookmarked_locations, many=True)
    return Response({'top_bookmarks':serializer.data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_itinerary(request, itinerary_id):
    number_of_people = request.data.get("number_of_people")
    budget = request.data.get("budget")
    itinerary = Itinerary.objects.get(id=itinerary_id)

    if request.user != itinerary.user:
        return Response({'message': "Access Denied"}, status=status.HTTP_403_FORBIDDEN)
    else:
        itinerary.number_of_people = number_of_people
        itinerary.budget = budget
        itinerary.save()
        return Response({'message': "Itinerary budget and group updated"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_service(request, location_id):
    print(request.data)
    try:
        location = Accommodation.objects.get(id=location_id, owner=request.user)
    except Accommodation.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    item = request.data.get('item')
    description = request.data.get('description')
    price = request.data.get('price')
    image = request.FILES.get('image')


    service = Service.objects.create(
        location=location,
        item=item,
        description=description,
        price=price,
        image=image,
    )

    serializer = ServiceSerializer(service)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_service(request, location_id, service_id):
    try:
        location = Accommodation.objects.get(id=location_id, owner=request.user)
        service = Service.objects.get(id=service_id, location=location)
    except (Accommodation.DoesNotExist, Service.DoesNotExist):
        return Response({"error": "Food or Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    service.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_service_details(request, location_id):
    try:
        location = Accommodation.objects.get(id=location_id)
    except Accommodation.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    service = Service.objects.filter(location=location)
    serializer = ServiceSerializer(service, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_completed_days(request):
    completed_days = Day.objects.filter(completed=True, rating__gt=0)

    serializer = CompletedDaySerializer(completed_days, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_all_events(request):
    events = Event.objects.all()
    serializer = EventSerializerAdmin(events, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_event(request):
    print(request.data)

    name = request.data.get('name')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    description = request.data.get('description')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    if start_date and end_date:
        start_date = datetime.datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.datetime.strptime(end_date, '%m/%d/%Y').date()
    else:
        return Response({'error': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)


    Event.objects.create (
        name=name,
        start_date=start_date,
        end_date=end_date,
        latitude=latitude,
        longitude=longitude,
        description=description
    )

    return Response(status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_event(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    name = request.data.get('name')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    description = request.data.get('description')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    start_date = datetime.datetime.strptime(start_date, '%m/%d/%Y').date()
    end_date = datetime.datetime.strptime(end_date, '%m/%d/%Y').date()

    event.name = name
    event.start_date = start_date
    event.end_date = end_date
    event.description = description
    event.latitude = latitude
    event.longitude = longitude

    event.save()

    return Response(status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_event(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    event.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_business_stats(request, location_id):
    try:
        location = Location.objects.get(id=location_id)
    except Location.DoesNotExist:
        return Response({'error': 'Location not found or you do not have access'}, status=status.HTTP_404_NOT_FOUND)

    total_bookmarks = Bookmark.objects.filter(location=location).count()
    average_rating = Review.objects.filter(location=location).aggregate(Avg('rating'))['rating__avg']
    average_rating = round(average_rating, 2) if average_rating is not None else 0
    total_reviews = Review.objects.filter(location=location).count()
    total_visits = ItineraryItem.objects.filter(
        location=location,
        day__completed=True
    ).count()

    total_planned = ItineraryItem.objects.filter(
        location=location,
    ).count()

    stats = {
        'total_bookmarks': total_bookmarks,
        'average_rating': average_rating,
        'total_reviews': total_reviews,
        'total_visits': total_visits,
        'total_planned': total_planned,
    }

    return Response(stats, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_top_locations_itinerary(request):
    top_locations = Location.objects.filter(
        itineraryitem__day__completed=True
    ).annotate(
        total_occurrences=Count('itineraryitem__day')
    ).order_by('-total_occurrences')[:10]

    serializer = TopLocationItinerarySerializer(top_locations, many=True)

    return Response({'top_locations_itinerary': serializer.data}, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_event(request, event_id):
    event = Event.objects.get(id=event_id)
    serializer = EventSerializerAdmin(event)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_fee(request, location_id):
    spot = Spot.objects.get(id=location_id)
    name = request.data.get('name')
    is_required = request.data.get('is_required')

    fee = FeeType.objects.create(
        spot=spot,
        name=name,
        is_required=is_required
    )

    serializer = FeeTypeSerializer(fee)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
def get_fees(request, location_id):
    spot = Spot.objects.get(id=location_id)
    print(spot)
    fees = FeeType.objects.filter(spot=spot)
    print(fees)
    serializer = FeeTypeSerializer(fees, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fee(request, fee_id):
    fee = FeeType.objects.filter(id=fee_id)
    serializer = FeeTypeSerializer(fee)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_fee(request, audience_id):
    audience_fee = AudienceType.objects.get(id=audience_id)
    name = request.data.get('name') 
    price = request.data.get('price')
    description = request.data.get('description')

    audience_fee.name = name
    audience_fee.price = price
    audience_fee.description = description
    audience_fee.save()

    return Response(status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_fee(request, fee_id, audience_id):
    pass

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_function(request):
    user = request.user 
    visited_list = set()

    itineraries = Itinerary.objects.filter(user=user)
    
    for itinerary in itineraries:
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            items = ItineraryItem.objects.filter(day=day)
            visited_list.update(item.location.id for item in items)

    visited_list = set(visited_list)

    print(visited_list)

    preferences = [
        int(user.preferences.history),
        int(user.preferences.nature),
        int(user.preferences.religion),
        int(user.preferences.art), 
        int(user.preferences.activity),
        int(user.preferences.entertainment),
        int(user.preferences.culture)
    ]

    manager = RecommendationsManager()
    manager.custom_recommendation(user, preferences, visited_list)

    return Response(status=status.HTTP_200_OK)