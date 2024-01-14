from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.core.files.storage import default_storage
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.crypto import get_random_string
from django.db.models import Q, Max, Sum
from datetime import datetime
import calendar

import pandas as pd
import json

from .managers import *
from .models import *
from .serializers import *
from .utils import generate_otp

import random
import numpy as np

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            error_detail_code = e.detail['non_field_errors'][0]
            return Response({"detail": error_detail_code}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)
        return response

class UserRegistrationView(CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except Exception as e:
            email_error = serializer.errors.get('email', None)

            if email_error:
                return Response({'detail': 'This email is already in use'},status=status.HTTP_400_BAD_REQUEST)

            return Response(status=status.HTTP_400_BAD_REQUEST)

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
        # requests = [request.location.id for request in OwnershipRequest.objects.filter(is_approved=False)]
        # queryset = queryset.exclude(id__in=requests)

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
        # requests = [request.location.id for request in OwnershipRequest.objects.filter(is_approved=False)]
        # queryset = queryset.exclude(id__in=requests)

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
    
@api_view(["POST"])
def generate_user_otp(request):
    user = request.user
    otp_code = generate_otp(user)

    subject = "Verify its you"
    message = f"Use the {otp_code} to verify your account."
    from_email = settings.EMAIL_FROM
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)
    return Response(status=status.HTTP_200_OK)
    
@api_view(["POST"])
def verify_otp_user(request):
    code = request.data.get('code')
    user = request.user
    otp = OTP.objects.get(user=user)

    if not otp:
        return Response({'detail': 'How does this happen'}, status=status.HTTP_400_BAD_REQUEST)

    if otp.is_expired:
        return Response({'detail': "OTP already expired"})

    if otp.otp != code:
        return Response({'detail': 'Code does not match'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.requires_otp = False
    user.save()

    return Response({'detail': 'Success'}, status=status.HTTP_200_OK)

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
    
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email')

    try:
        user = User.objects.get(email=email)
    except:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    reset_instance, created = PasswordReset.objects.get_or_create(user=user)
    reset_instance.key = get_random_string(length=20)
    reset_instance.used = False
    reset_instance.save()

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"{settings.FRONTEND_URL}/reset/{uidb64}/{reset_instance.key}"

    subject = 'Reset Your Password'
    message = f'You have requested to reset your password. Use the link to proceed.\n\n{reset_link}'
    from_email = settings.EMAIL_FROM
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)

    return Response({'message': "Password reset email sent successfully"}, status=status.HTTP_200_OK)

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def reset_password(request, uidb64, token):
    if request.method == 'GET':
        try:
            user_id = str(urlsafe_base64_decode(uidb64), 'utf-8')
            user = get_object_or_404(User, pk=user_id)
            reset_instance = get_object_or_404(PasswordReset, user=user, key=token, used=False)
        except:
            return Response({'message': 'Invalid Reset Link'}, status=status.HTTP_400_BAD_REQUEST)
    
        return Response({'message': 'Valid Reset Link'}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        try:
            user_id = str(urlsafe_base64_decode(uidb64), 'utf-8')
            user  = User.objects.get(pk=user_id)
            reset_instance = get_object_or_404(PasswordReset, user=user, key=token, used=False)

            new_password = request.data.get('password')
            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()

            reset_instance.mark_as_used()

            return Response({'message': 'Password reset successful', 'email': user.email}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'message': 'Invalid Reset Link'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'message': 'An error occured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user 
    old_password = serializer.validated_data.get('old_password')
    new_password = serializer.validated_data.get('new_password')

    if not user.check_password(old_password):
        return Response({'detail': 'Old Password is Incorrect'}, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()

    return Response({'detail': 'Password set successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def change_password_with_token(request, uidb64, token):
    try:
        user_id = str(urlsafe_base64_decode(uidb64), 'utf-8')
        user = get_object_or_404(User, pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'message': 'Invalid user or token'}, status=status.HTTP_400_BAD_REQUEST)

    if default_token_generator.check_token(user, token):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data.get('new_password')

        user.set_password(new_password)
        user.save()

        return Response({'detail': 'Password changed successfully'}, status=status.HTTP_200_OK)
    else:
        return Response({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

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
def update_ordering(request, day_id):
    items = request.data.get("items")

    for order, item in enumerate(items):
        itinerary_item = ItineraryItem.objects.get(id=item["id"])
        itinerary_item.order = order
        itinerary_item.save()

    serializer = ItineraryItemSerializer(items, many=True)

    day = Day.objects.get(id=day_id)
    itinerary_items = ItineraryItem.objects.filter(day=day)
    serializer = ItineraryItemSerializer(itinerary_items, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

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

@api_view(['GET'])
def get_visited_locations(request):
    user = request.user
    locations = []

    for itinerary in Itinerary.objects.filter(owner=user):
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            for item in ItineraryItem.objects.filter(day=day):
                locations.append(item.location)

    for review in Review.objects.filter(user=user):
        if review.location not in location:
            locations.append(review.location)

    serializers = RecommendedLocationSerializer(locations, many=True)
    return Response(serializers.data, status=status.HTTP_200_OK)

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
        current_date = datetime.strptime(start_date, '%m/%d/%Y')
        end_date = datetime.strptime(end_date, '%m/%d/%Y')
        
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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_content_recommendations(request):
    user = request.user
    budget = request.data
    visited_list = set()
    activity_list = defaultdict(int)

    preferences = [
        user.preferences.activity,
        user.preferences.art, 
        user.preferences.culture,
        user.preferences.entertainment,
        user.preferences.history,
        user.preferences.nature,
        user.preferences.religion,
    ]

    # get all itineraries concerned with a single user, and all related days which are marked as completed
    # and add all related locations as "visited" while taking note of the frequencies of activities involved
    # in those visits
    for itinerary in Itinerary.objects.filter(user=user):
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            for item in ItineraryItem.objects.filter(day=day):
                location = item.location
                visited_list.add(location.id)
    
                if location.location_type == '1':
                    spot = Spot.objects.get(id=location.id)
                    for activity in spot.get_activities:
                        activity_list[activity] += 1

    # treat reviews as a sign that a user has already visited a location, therefore check if there are reviews with
    # related locations not added to the visited_list and are a spot in order to obtain the frequencies of 
    # activities not mentioned
    for review in Review.objects.filter(user=user):
        location = review.location

        if location.location_type == '1' and location.id not in visited_list:
            spot = Spot.objects.get(id=location.id)
            for activity in spot.get_activities:
                activity_list[activity] += 1    

    visited_list.update(review.location.id for review in Review.objects.filter(user=user))
    preferences = np.array(preferences, dtype=int)

    manager = RecommendationsManager()
    recommendation_ids = manager.get_content_recommendations(preferences, budget, visited_list, activity_list)
    random.shuffle(recommendation_ids)

    recommendations = []
    for id in recommendation_ids[:3]:
        recommendation = ModelItinerary.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = ModelItinerarySerializers(
        recommendations, 
        many=True,
        context={'visited_list': visited_list}
    )

    return Response({
        'recommendations': recommendation_serializers.data
        }, status=status.HTTP_200_OK)

@api_view(["POST"])
def update_itinerary_calendar(request, itinerary_id):
    start_date = request.data.get("startDate")
    end_date = request.data.get("endDate")

    itinerary = Itinerary.objects.get(pk=itinerary_id)

    start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
    end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

    days = []

    while start_date <= end_date:
        day, created = Day.objects.get_or_create(
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
    location_orders = model.modelitinerarylocationorder_set.all()

    items = []
    for location_order in location_orders:
        item = ItineraryItem.objects.create(
            day=day,
            location=location_order.spot,
            order=location_order.order
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
    website = request.data.get('website')
    contact = request.data.get('contact')
    email = request.data.get('email')

    location = Location.objects.create(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        description=description,
        location_type=location_type,
        is_closed=False,
        website=website,
        contact=contact,
        email=email,
    )

    if location_type == '1':
        spot = Spot.objects.get(id=location.id)
        tag_names = json.loads(request.data.get("tags", []))
        activities = json.loads(request.data.get("activities",[]))

        spot.opening_time = request.data.get("opening_time")
        spot.closing_time = request.data.get("closing_time")

        for tag_name in tag_names:
            tag = Tag.objects.get(name=tag_name)
            spot.tags.add(tag)

        for activity_name in activities:
            activity, created = Activity.objects.get_or_create(name=activity_name)
            spot.activity.add(activity)
        spot.save()
        

    if location_type == '2':
        foodplace = FoodPlace.objects.get(id=location.id)
        foodplace.opening_time = request.data.get("opening_time")
        foodplace.closing_time = request.data.get("closing_time")
        
        for tag_name in tag_names:
            tag, created = FoodTag.objects.get_or_create(name=tag_name)
            foodplace.tags.add(tag)

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

    return Response(response_data, status=status.HTTP_200_OK)



@api_view(["PATCH"])
def edit_location(request, id):
    location_type = request.data.get("type")
    name = request.data.get("name")
    address = request.data.get("address")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")
    description = request.data.get("description")
    website = request.data.get('website')
    contact = request.data.get('contact')
    email = request.data.get('email')

    location = Location.objects.get(id=id)
    
    location.type = location_type
    location.name = name
    location.address = address
    location.latitude = latitude
    location.longitude = longitude
    location.description = description
    location.website = website
    location.contact = contact
    location.email = email

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
    location_tags = Spot.objects.get(id=location_id).tags.all()
    all_tags = Tag.objects.all().order_by('name')

    origin_binned_tags = [1 if tag in location_tags else 0 for tag in all_tags]
    
    visited_list = set()
    for itinerary in Itinerary.objects.filter(user=user):
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            items = ItineraryItem.objects.filter(day=day)
            visited_list.update(item.location.id for item in items)

    manager = RecommendationsManager()
    recommendation_ids = manager.get_location_recommendation(user, origin_binned_tags, location_id, visited_list)

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
        int(user.preferences.activity),
        int(user.preferences.art), 
        int(user.preferences.culture),
        int(user.preferences.entertainment),
        int(user.preferences.history),
        int(user.preferences.nature),
        int(user.preferences.religion),
    ]

    for itinerary in itineraries:
        for day in Day.objects.filter(itinerary=itinerary, completed=True):
            items = ItineraryItem.objects.filter(day=day)
            visited_list.update(item.location.id for item in items)

    # get the user's review of specific places as an indication that leaving a review = visited
    visited_list.update(review.location.id for review in Review.objects.filter(user=user))
    manager = RecommendationsManager()
    recommendation_ids = manager.get_homepage_recommendation(user, preferences, visited_list)

    recommendations = []
    for id in recommendation_ids:
        recommendation = Location.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = RecommendedLocationSerializer(recommendations, many=True, context={'visited_list': visited_list})

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

    name = request.data.get('name')
    address = request.data.get('address')
    longitude = request.data.get('longitude')
    latitude = request.data.get('latitude')
    location_type = request.data.get('type')
    website = request.data.get('website')
    contact = request.data.get('contact')
    email = request.data.get('email')
    image = request.data.get('image')
    description = request.data.get('description')
    
    if location_type == '1' or location_type == '2':
        tag_names = json.loads(request.data.get("tags", []))
    
    if location_type == '1':
        activities = json.loads(request.data.get("activities",[]))

    location = Location.objects.create(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude,
        location_type=location_type,
        website=website,
        contact=contact,
        email=email,
        description=description
    )

    if location_type == '1':
        spot = Spot.objects.get(id=location.id)
        spot.opening_time = request.data.get("opening_time")
        spot.closing_time = request.data.get("closing_time")

        for tag_name in tag_names:
            tag = Tag.objects.get(name=tag_name)
            spot.tags.add(tag)
        
        for activity_name in activities:
            activity, created = Activity.objects.get_or_create(name=activity_name)
            spot.activity.add(activity)
        
        spot.save()

    if location_type == '2':
        foodplace = FoodPlace.objects.get(id=location.id)
        foodplace.opening_time = request.data.get("opening_time")
        foodplace.closing_time = request.data.get("closing_time")

        for tag_name in tag_names:
            tag, created = FoodTag.objects.get_or_create(name=tag_name)
            foodplace.tags.add(tag)

    OwnershipRequest.objects.create(
        user=user,
        location=location,
        status='1'
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
    serializer = OwnershipRequestSerializer(requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_ownership_request(request, request_id):
    data = request.data
    print(data)

    approval_request = OwnershipRequest.objects.get(id=request_id)
    return Response(status=status.HTTP_200_OK)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def approve_request(request, request_id):
    approval_status = request.data
    
    approval_request = OwnershipRequest.objects.get(id=request_id)
    approval_request.status = approval_status

    if status == 2:
        approval_request.is_approved = True

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
    current_date = datetime.now().date()

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

    serializer = LocationBusinessManageSerializer(location)
    return Response({'business': serializer.data}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def edit_business(request, location_id):
    data = json.loads(request.data.get('data', {}))
    user = request.user
    try:
        if user.is_staff:
            location = Location.objects.get(id=location_id)
        else:
            location = Location.objects.get(owner=user, id=location_id)
    except Location.DoesNotExist:
        return Response({"error": "Location not found or you do not have permission"}, status=status.HTTP_404_NOT_FOUND)

    location.name = data.get('name', location.name)
    location.address = data.get('address', location.address)
    location.contact = data.get('contact', location.contact)
    location.email = data.get('email', location.email)
    location.website = data.get('contact', location.website)
    location.longitude = data.get('longitude', location.longitude)
    location.latitude = data.get('latitude', location.latitude)
    location.description = data.get('description', location.description)
    
    location.save()

    if data.get('location_type') == "1":
        spot = Spot.objects.get(id=location_id)
        new_tags = data.get('tags', [])
        existing_tags = [spot.name for spot in spot.tags.all()]

        removed_tags = set(existing_tags) - set(new_tags)
        for tag_name in removed_tags:
            tag = Tag.objects.get(name=tag_name)
            spot.tags.remove(tag)

        added_tags = set(new_tags) - set(existing_tags)
        for tag_name in added_tags:
            tag = Tag.objects.get(name=tag_name)
            spot.tags.add(tag)

        spot.opening_time = data.get('opening_time', spot.opening_time)
        spot.closing_time = data.get('closing_time', spot.closing_time)
        spot.save()

    if data.get('location_type') == "2":
        foodplace = FoodPlace.objects.get(id=location_id)
        foodplace.opening_time = data.get('opening_time', foodplace.opening_time)
        foodplace.closing_time = data.get('closing_time', foodplace.closing_time)
        foodplace.save()     

    if 'image' in request.FILES:
        image = request.FILES['image']

        location_image = LocationImage.objects.get(
            location=location,
            is_primary_image=True,
        )

        old_image_path = location_image.image.path
        default_storage.delete(old_image_path)

        location_image.image = image
        location_image.save() 

    return Response(status=status.HTTP_200_OK)


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
    user = request.user
    try:
        if user.is_staff:
            location = FoodPlace.objects.get(id=location_id)
        else:
            location = FoodPlace.objects.get(id=location_id, owner=user)
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
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_food(request, location_id, food_id):
    user = request.user
    try:
        if user.is_staff:
            location = FoodPlace.objects.get(id=location_id)
        else:
            location = FoodPlace.objects.get(id=location_id, owner=user)
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
    counts = []
    total_users = preferences_count['total_users']
    for preference, count in preferences_count.items():
        if preference != 'total_users' and preference.endswith('_users'):
            preference_name = preference[:-6]
            preference_percentages[preference_name] = (count / total_users) * 100
            counts.append({'preference_name': preference_name, 'count': count})

    return Response({'preference_percentages': preference_percentages,
                     'counts': counts}, status=status.HTTP_200_OK)

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
def get_tags_percent(request):
    spots = Spot.objects.exclude(tags__name__isnull=True)
    tags_occurrences = spots.values('tags__name').annotate(tag_count=Count('tags__name')).order_by('-tag_count') 
    total_tags = sum(tag['tag_count'] for tag in tags_occurrences)
    
    data = [
        {
            'tag': tag['tags__name'],
            'count': tag['tag_count'],
            'percentage': (tag['tag_count'] / total_tags) * 100
        } for tag in tags_occurrences
    ]

    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_activity_percent(request):
    spots = Spot.objects.exclude(activity__name__isnull=True)
    activities = spots.values('activity__name').annotate(activity_count=Count('activity__name')).order_by('-activity_count')
    total_activities = sum(activity['activity_count'] for activity in activities)
    
    data = [
        {
            'activity': activity['activity__name'],
            'count': activity['activity_count'],
            'percentage': (activity['activity_count'] / total_activities) * 100
        } for activity in activities
    ]

    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_foodtags_percent(request):
    foodplace = FoodPlace.objects.exclude(tags__name__isnull=True)
    tags_occurrences = foodplace.values('tags__name').annotate(tag_count=Count('tags__name')).order_by('-tag_count') 
    total_tags = sum(tag['tag_count'] for tag in tags_occurrences)
    
    data = [
        {
            'tag': tag['tags__name'],
            'count': tag['tag_count'],
            'percentage': (tag['tag_count'] / total_tags) * 100
        } for tag in tags_occurrences
    ]

    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_visited_spot_tag(request):
    completed_days = Day.objects.filter(completed=True)
    visited_spots = Spot.objects.filter(location_ptr__itineraryitem__day__in=completed_days).exclude(tags__name__isnull=True)
    tags_occurrences = visited_spots.values('tags__name').annotate(tag_count=Count('tags__name')).order_by('-tag_count')
    total_tags = sum(tag['tag_count'] for tag in tags_occurrences)
    
    data = [
        {
            'tag': tag['tags__name'],
            'count': tag['tag_count'],
            'percentage': (tag['tag_count'] / total_tags) * 100
        } for tag in tags_occurrences
    ]
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_visited_spot_activity(request):
    completed_days = Day.objects.filter(completed=True)
    visited_spots = Spot.objects.filter(location_ptr__itineraryitem__day__in=completed_days).exclude(activity__name__isnull=True)
    activities_occurrences = visited_spots.values('activity__name').annotate(activity_count=Count('activity__name')).order_by('-activity_count')
    total_activities = sum(activity['activity_count'] for activity in activities_occurrences)
    
    data = [
        {
            'activity': activity['activity__name'],
            'count': activity['activity_count'],
            'percentage': (activity['activity_count'] / total_activities) * 100
        } for activity in activities_occurrences
    ]

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_visited_foodplace_tag(request):
    completed_days = Day.objects.filter(completed=True)
    visited_foodplaces = FoodPlace.objects.filter(location_ptr__itineraryitem__day__in=completed_days).exclude(tags__name__isnull=True)
    foodtags_occurrences = visited_foodplaces.values('tags__name').annotate(tag_count=Count('tags__name')).order_by('-tag_count')
    total_foodtags = sum(tag['tag_count'] for tag in foodtags_occurrences)
    
    data = [
        {
            'foodtag': tag['tags__name'],
            'count': tag['tag_count'],
            'percentage': (tag['tag_count'] / total_foodtags) * 100
        } for tag in foodtags_occurrences
    ]
    
    return Response(data, status=status.HTTP_200_OK)


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
    user = request.user
    try:
        if user.is_staff:
            location = Accommodation.objects.get(id=location_id)
        else:
            location = Accommodation.objects.get(id=location_id, owner=user)
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
    user = request.user
    try:
        if user.is_staff:
            location = Accommodation.objects.get(id=location_id)
        else:
            location = Accommodation.objects.get(id=location_id, owner=user)
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

@api_view(["GET"])
def get_upcoming_events(request):
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(start_date__gte=today)

    serializer = EventSerializerAdmin(upcoming_events, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_event(request):
    name = request.data.get('name')
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    description = request.data.get('description')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()
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

    start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
    end_date = datetime.strptime(end_date, '%m/%d/%Y').date()

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
    ).order_by('-total_occurrences')

    paginator = PageNumberPagination()
    paginator.page_size = 10 

    result_page = paginator.paginate_queryset(top_locations, request)

    serializer = TopLocationItinerarySerializer(result_page, many=True)

    return paginator.get_paginated_response({'top_locations_itinerary': serializer.data})

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
    fees = FeeType.objects.filter(spot=spot)
    serializer = FeeTypeSerializer(fees, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fee_type(request, fee_id):
    fee = FeeType.objects.get(id=fee_id)
    serializer = FeeTypeSerializer(fee)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_fee_type(request, fee_id):
    name = request.data.get('name')
    is_required = request.data.get('is_required')
    
    fee = FeeType.objects.get(id=fee_id)
    fee.name = name 
    fee.is_required = is_required
    fee.save()

    return Response(status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_fee_type(request, fee_id):
    fee = FeeType.objects.get(id=fee_id)

    if not fee:
        return Response(status=status.HTTP_404_NOT_FOUND)

    fee.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_audience_type(request, fee_id):
    fee = FeeType.objects.get(id=fee_id)
    name = request.data.get('name')
    price = request.data.get('price')
    
    audience = AudienceType.objects.create(
        fee_type=fee,
        price=price,
        name=name
    )
    serializer = AudienceTypeSerializer(audience)

    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_audience_type(request, audience_id):
    audience = AudienceType.objects.get(id=audience_id)
    name = request.data.get('name')
    price = request.data.get('price')

    audience.name = name
    audience.price = price 
    audience.save()

    return Response(status=status.HTTP_200_OK)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_audience_type(request, audience_id):
    audience = AudienceType.objects.get(id=audience_id)

    if not audience:
        return Response(status=status.HTTP_404_NOT_FOUND)

    audience.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_foodtags(request, location_id):
    tag_name = request.data.get('tag')
    foodplace = FoodPlace.objects.get(id=location_id)
    
    tag, created = FoodTag.objects.get_or_create(name=tag_name)
    foodplace.tags.add(tag)

    serializer = FoodTagSerializer(tag)
    return Response({
        "data": serializer.data,
        "message": "Tags added to foodplace"
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_foodtags(request, location_id):
    tag_name = request.data.get('tag')
    foodplace = FoodPlace.objects.get(id=location_id)
    tag = FoodTag.objects.get(name=tag_name)

    foodplace.tags.remove(tag)
    return Response({"message": "Tags removed from foodplace"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_foodtag(request):
    query = request.query_params.get('query', '')
    if not query:
        tags = FoodTag.objects.all()
    else:
        tags = FoodTag.objects.filter(name__icontains=query)
    serializer = FoodTagSerializer(tags, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_create_foodtag(request):
    tag_name = request.query_params.get('query')
    
    food_tag, created = FoodTag.objects.get_or_create(name=tag_name)

    serializer = FoodTagSerializer(food_tag)

    if created:
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_spot_tags(request):
    tags = Tag.objects.all()
    serializer = TagSerializer(tags, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_tags(request, location_id):
    tag_name = request.data.get('tag')
    spot = Spot.objects.get(id=location_id)
    tag = Tag.objects.get(name=tag_name)

    spot.tags.add(tag)

    return Response({"message": "Tags added to spot"}, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_tags(request, location_id):
    tag_name = request.data.get('tag')
    spot = Spot.objects.get(id=location_id)
    tag = Tag.objects.get(name=tag_name)

    spot.tags.remove(tag)

    return Response({"message": "Tags removed from spot"}, status=status.HTTP_200_OK)


@api_view(["POST"])
def add_activity(request, location_id):
    activity_name = request.data.get('activity')
    spot = Spot.objects.get(id=location_id)
    activity, created = Activity.objects.get_or_create(name=activity_name)
    spot.activity.add(activity)

    return Response({"message": "Activity added to spot"}, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def remove_activity(request, location_id):
    activity_name = request.data.get('activity')
    spot = Spot.objects.get(id=location_id)
    activity = Activity.objects.get(name=activity_name)

    spot.activity.remove(activity)

    return Response({"message": "Activity removed from spot"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_activity(request):
    query = request.query_params.get('query', '')
    if not query:
        activity = Activity.objects.all()
    else:
        activity = Activity.objects.filter(name__icontains=query)

    serializer = ActivitySerializer(activity, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_create_activity(request):
    activity_name = request.query_params.get('query', '')
    activity, created = Activity.objects.get_or_create(name=activity_name)

    serializer = ActivitySerializer(activity)
    if created:
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_spot_chain_recommendations(request, day_id):
    user = request.user 

    day = Day.objects.get(id=day_id)
    origin_location = ItineraryItem.objects.filter(day=day).last().location
    visited_list = set()
    activity_counts = defaultdict(int)

    itineraries = Itinerary.objects.filter(user=user)
    
    for itinerary in itineraries:
        for day in Day.objects.filter(itinerary=itinerary):
            for item in ItineraryItem.objects.filter(day=day):
                visited_list.add(item.location.id)

                if day.completed and item.location.location_type == '1':
                    spot = Spot.objects.get(id=item.location.id)
                    for spot in spot.activity.all():
                        activity_counts[spot.name] += 1

    visited_list = set(visited_list)

    preferences = [
        int(user.preferences.activity),
        int(user.preferences.art), 
        int(user.preferences.culture),
        int(user.preferences.entertainment),
        int(user.preferences.history),
        int(user.preferences.nature),
        int(user.preferences.religion),
    ]

    manager = RecommendationsManager()
    recommendation_ids = manager.get_spot_chain_recommendation(user, origin_location.id, preferences, visited_list, activity_counts)

    recommendations = []

    for id in recommendation_ids:
        recommendation = Location.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = RecommendedLocationSerializer(recommendations, many=True, context={'location_id': origin_location.id})

    return Response(recommendation_serializers.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_food_chain_recommendations(request, day_id):
    user = request.user
    day = Day.objects.get(id=day_id)
    visit_list = []

    for item in ItineraryItem.objects.filter(day=day):
        visit_list.append(item.location.id)

    manager = RecommendationsManager()
    recommendation_ids = manager.get_foodplace_recommendation(user, visit_list[-1], visit_list)

    recommendations = []
    for id in recommendation_ids:
        recommendation = Location.objects.get(pk=id)
        recommendations.append(recommendation)

    recommendation_serializers = RecommendedLocationSerializer(recommendations, many=True, context={'location_id': visit_list[-1]})

    return Response(recommendation_serializers.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_driver(request):
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    contact = request.data.get('contact')
    facebook = request.data.get('facebook')
    additional_information = request.data.get('info')

    car = request.data.get('car')
    car_type = request.data.get('type')
    max_capacity = request.data.get('capacity')
    image = request.data.get('image')
    plate_number = request.data.get('plate')

    Driver.objects.create(
        first_name = first_name,
        last_name = last_name,
        email = email,
        contact = contact,
        facebook = facebook,
        additional_information = additional_information,
        car = car,
        car_type = car_type,
        max_capacity = max_capacity,
        image = image,
        plate_number = plate_number
    )

    return Response({'message':'Driver created'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_driver(request, driver_id):
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    contact = request.data.get('contact')
    facebook = request.data.get('facebook')
    
    additional_information = request.data.get('additional_information')

    car = request.data.get('car')
    car_type = request.data.get('car_type')
    max_capacity = request.data.get('max_capacity')
    plate_number = request.data.get('plate_number')

    driver = Driver.objects.get(id=driver_id)

    driver.first_name = first_name
    driver.last_name = last_name
    driver.email = email
    driver.contact = contact
    driver.facebook = facebook
    driver.additional_information = additional_information
    
    driver.car = car
    driver.car_type = car_type
    driver.max_capacity = max_capacity
    driver.plate_number = plate_number

    driver.save()

    return Response({'message':'Driver edited'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_drivers(request):
    drivers = Driver.objects.all()
    serializer = DriverSerializer(drivers, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_specific_driver(request, driver_id):
    driver = Driver.objects.get(id=driver_id)
    serializer = DriverSerializer(driver)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_contact_form(request):
    user = request.user
    query = request.data.get('query')

    ContactForm.objects.create(
        user=user,
        query=query
    )
    return Response(status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_contact_forms(request):
    contact_forms = ContactForm.objects.all()
    serializer = ContactFormSerializer(contact_forms, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_admin_response(request, form_id):
    try:
        contact_form = ContactForm.objects.get(id=form_id)
    except ContactForm.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    contact_form.admin_responded = not contact_form.admin_responded
    contact_form.save()

    serializer = ContactFormSerializer(contact_form)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_foodplace_recommendations(request):
    from api.models import Review
    user = request.user

    visited_food_places_reviews = Review.objects.filter(user=user, location__location_type="2")
    visited_location_ids_reviews = visited_food_places_reviews.values_list('location', flat=True).distinct()

    visited_location_ids_itineraries = ItineraryItem.objects.filter(day__completed=True, day__itinerary__user=user, location__location_type='2').values_list('location', flat=True).distinct()
    visited_location_ids = set(visited_location_ids_reviews) | set(visited_location_ids_itineraries)

    visited_food_places = FoodPlace.objects.filter(id__in=visited_location_ids)

    food_tag_collections = defaultdict(int)

    for food_place in visited_food_places:
        food_tags = food_place.get_foodtags

        for food_tag in food_tags:
            food_tag_collections[food_tag] += 1


    manager = RecommendationsManager()
    recommendation_ids = manager.get_foodplace_recommendations(visited_food_places, food_tag_collections)
    
    recommendation_locations = []
    for id in recommendation_ids:
        location = Location.objects.get(id=id)
        recommendation_locations.append(location)

    serializer = RecommendedLocationSerializer(recommendation_locations, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def monthly_report(request, month):
    current_year = datetime.now().year

    # Calculate the first day and the last day of the selected month
    first_day = datetime(year=current_year, month=month, day=1)
    last_day = datetime(year=current_year, month=month, day=calendar.monthrange(current_year, month)[1], hour=23, minute=59, second=59)

    # Query to get all completed days in the selected month
    completed_days = Day.objects.filter(date__range=(first_day, last_day), completed=True)

    unique_visitors_count = (
        Itinerary.objects
        .filter(day__in=completed_days)
        .values('user')
        .annotate(max_people=Max('number_of_people'))
        .aggregate(unique_visitors_count=Sum('max_people'))
    )['unique_visitors_count']

    # Calculate the frequency of each location visited during the month
    location_frequency = (
        ItineraryItem.objects
        .filter(day__date__range=(first_day, last_day), day__completed=True)
        .values('location__name')
        .annotate(frequency=Count('location'))
    )

    # Additional information about completed trips
    completed_trips_info = []

    # Group itinerary items by date
    itinerary_items_by_date = {}
    total_locations_visited_in_month = 0

    for item in ItineraryItem.objects.filter(day__in=completed_days):
        date_key = item.day.date
        total_locations_visited_in_month += 1

        if date_key not in itinerary_items_by_date:
            itinerary_items_by_date[date_key] = {
                'total_locations_visited': 0,
                'percentage_completed': 0,
                'itinerary_items': [],
            }

        itinerary_items_by_date[date_key]['total_locations_visited'] += 1
        itinerary_items_by_date[date_key]['itinerary_items'].append({
            'location__name': item.location.name,
            'order': item.order,
        })

    # Process the grouped information
    for date_key, data in itinerary_items_by_date.items():
        percentage_completed = (data['total_locations_visited'] / total_locations_visited_in_month) * 100

        completed_trips_info.append({
            'date': date_key,
            'total_locations_visited': data['total_locations_visited'],
            'percentage_completed_trips': percentage_completed,
        })

    context = {
        'completed_trips': len(completed_days),
        'unique_visitor_counts': unique_visitors_count,
        'location_frequency': list(location_frequency),
        'completed_trips_info': completed_trips_info,
    }

    return Response(context, status=status.HTTP_200_OK)


@api_view(['POST'])
def notify_and_change_password(request):    
    # ids = [100] #target one user

    # for all users:
    target_users = User.objects.all() 

    #uncomment target_users code below if all
    # target_users = User.objects.filter(id__in=ids) 

    for target_user in target_users:
        new_password = generate_strong_password()
        target_user.set_password(new_password)
        target_user.save()

        send_password_change_notification_email(target_user, new_password)

    return Response({'message': 'Password changed successfully and notification sent.'})

def generate_strong_password(length=12):
    characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_-+=[]{}|;:,.<>?'
    password = get_random_string(length, characters)
    return password

def send_password_change_notification_email(user, new_password):
    subject = 'Password Change Notification'
    message = f'Thank you for trying out and testing our system CebuRoute, which is a part of our research into implementing a travel planner with a recommendation system for people who are interested in visiting Cebu.\n\n' \
              f'Recently, Google flagged our website as a potential Phishing website and for a website we did for a research project we realize we might have been lax in terms of our security procedures.\n' \
              f'We would like to assure you that we are not doing anything that might compromise the data you put in, and that we are trying to resolve the issue with Google. \n' \
              f'But to do so, we decided to reimplement the system so that it requires using strong passwords. \n' \
              f'If you decide to test our website again, you may log in using the new password we have set for you: \n\n\nPassword: {new_password} \n\n' \
              f'you can also use the forgot password mechanism to customize your password. \n' \
              f'Once again, we are truly thankful for your cooperation and time taken to try out our system!'
            
    from_email = settings.EMAIL_FROM
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_click(request, location_id):
    user = request.user
    location = Location.objects.get(id=location_id)

    click, created = UserClick.objects.get_or_create(user=user, location=location)
    print(click, created)
    if not created:
        click.amount += 1
        click.save()

    return Response("Clicked", status=status.HTTP_200_OK)