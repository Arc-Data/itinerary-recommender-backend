from django.urls import path
from .views import *
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('token/', MyTokenObtainPairView.as_view(), name='token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserRegistrationView.as_view(), name="register"),
    path('change-password/', change_password, name="change-password"),
    path('activate/<str:uidb64>/<str:token>/', activate_account, name="activate-account"),

    path('location/create/', create_location, name="create-location"),
    path('location/<int:id>/delete/', delete_location, name="delete-location"),
    path('location/<int:id>/edit/', edit_location, name="edit-location"),
    path('location/request/', create_ownership_request, name="create_ownership_requests"),
    path('location/requests/', get_ownership_requests, name="get_ownership_requests"),

    path('location/paginated/', PaginatedLocationViewSet.as_view({'get': 'list'}, name="paginated_locations")),

    path('location/', LocationViewSet.as_view({'get': 'list'}), name="locations"),
    path('location/plan/', LocationPlanViewSet.as_view({'get': 'list'}), name="locations-plan"),
    path('location/<int:id>/', get_location, name='location-detail'),
    path('location/<int:location_id>/bookmark/', bookmark, name='bookmark'),
    
    path('itinerary/',  create_itinerary, name='create_itinerary'),
    path('itinerary/list/', get_itinerary_list, name="itinerary-list"),
    path('itinerary/<int:itinerary_id>/', get_itinerary, name="get_itinerary"),
    path('itinerary/<int:itinerary_id>/calendar/', update_itinerary_calendar,name="update-itinerary-calendar"),
    path('itinerary/<int:itinerary_id>/days/', get_related_days, name="get_related_days"),
    path('itinerary/<int:itinerary_id>/delete/', delete_itinerary, name="delete_itinerary"),
    path('itinerary/<int:itinerary_id>/edit/name/', edit_itinerary_name, name="edit_itinerary"),
    path('itinerary/<int:itinerary_id>/edit/', edit_itinerary, name='edit_itinerary_detail'),

    path('day/<int:day_id>/color/', edit_day_color, name="edit-day-color"),
    path('day/<int:day_id>/delete/', delete_day, name="delete-day"),
    path('days/completed/', get_completed_days, name="get_completed_days"),
    path('day/<int:day_id>/complete/', mark_day_complete, name="mark_day_complete"),
    path('day/<int:day_id>/detail/', get_completed_day, name="get-completed-day"),
    path('day/<int:day_id>/rate/', rate_day, name="rate-day"),
    path('days/complete/', mark_days_complete, name="mark_days_complete"),
    path('days/completed/all/', get_all_completed_days, name='get_all_completed_days'),

    path('day-item/', create_itinerary_item, name="create-itinerary-item"),
    path('day-item/<int:day_id>/delete/', delete_day_item, name="delete-day-item"),
    path('update-ordering/', update_ordering, name="update-item-ordering"),

    path('spot/<int:pk>/', spot),

    path('preferences/', update_preferences, name="update-preferences"),
    
    path('recommendations/content/', get_content_recommendations, name='content-recommendations'),
    path('recommendations/<int:model_id>/apply/', apply_recommendation, name='apply-recommendation'),
    path('recommendations/location/<int:location_id>/', get_location_recommendations, name='get_location_recommendation'),
    path('recommendations/homepage/', get_homepage_recommendations, name='get_homepage_recommendations'), 
    path('recommendations/<int:day_id>/nearby/spot/', get_spot_chain_recommendations, name="get_spot_chain_recommendations"),
    path('recommendations/<int:day_id>/nearby/foodplace/', get_food_chain_recommendations, name="get_food_chain_recommendations"),

    path('bookmarks/', get_bookmarks, name='get_bookmarks'),

    path('location/<int:location_id>/reviews/', get_location_reviews, name='get_location_reviews'),
    path('location/<int:location_id>/reviews/user/', get_user_review, name='get_user_review'),
    path('location/<int:location_id>/reviews/create/', create_review, name='create_review'),
    path('location/<int:location_id>/reviews/edit/', edit_review, name='edit_review'),
    path('location/<int:location_id>/reviews/delete/', delete_review, name='delete_review'),

    path('user/<int:user_id>/delete/', delete_user, name='delete_user'),
    path('user/', get_all_users, name='get_all_users'),
    path('user/<int:user_id>/', get_user, name='get_user'),
    path('user/business/', get_user_business, name='get_user_business'),
    path('user/business/<int:location_id>/delete/', delete_user_business, name='delete_user_business'),
    path('user/business/<int:location_id>/', get_specific_business, name='get_specific_business'),
    path('user/business/<int:location_id>/edit/', edit_business, name='edit_business'),
    path('user/active/', get_active_trips, name="get-active-trips"),
    path('user/business/<int:location_id>/stats/', get_business_stats, name='get_business_stats'),

    path('user/business/<int:location_id>/edit/add_foodtags/', add_foodtags, name='add_foodtags'), #edit foodplace tags
    path('user/business/<int:location_id>/edit/remove_foodtags/', remove_foodtags, name='remove_foodtags'), #edit foodplace tags
    path('user/business/<int:location_id>/edit/add_tags/', add_tags, name='add_tags'), #edit spot tags
    path('user/business/<int:location_id>/edit/remove_tags/', remove_tags, name='remove_tags'), #edit spot tags
    
    path('foodtag/get/', get_create_foodtag, name='get_create_foodtag'),
    path('foodtag/search/', search_foodtag, name='search_foodtag'),

    path('tags/get/', get_spot_tags, name="get_spot_tags"),
    
    path('requests/', get_all_ownership_requests, name="get_all_ownership_requests"),
    path('request/<int:request_id>/approve/', approve_request, name="approve-request"),

    path('confirm/set/preferences/', get_set_preferences, name="get_set_preferences"),

    path('food/<int:location_id>/create/', create_food, name='create_food'),
    path('food/<int:location_id>/', get_food_details, name='get_food_details'),
    path('food/<int:location_id>/delete/<int:food_id>/', delete_food, name='delete_food'),

    path('service/<int:location_id>/create/', create_service, name='create_service'),
    path('service/<int:location_id>/', get_service_details, name='get_service_details'),
    path('service/<int:location_id>/delete/<int:service_id>/', delete_service, name='delete_service'),

    path('dashboard/preference/', get_preference_percentages, name='get_preference_percentages'),
    path('dashboard/counts/', get_counts, name='get_counts'),
    path('dashboard/top-spots/', get_top_spots, name='get_top_spots'),
    path('dashboard/top-accommodations/', get_top_accommodations, name='get_top_accommodations'),
    path('dashboard/top-foodplaces/', get_top_foodplaces, name='get_top_foodplaces'),
    path('dashboard/top-bookmarks/', get_top_bookmarks, name='get_top_bookmarks'),
    path('dashboard/top-locations-itinerary/', get_top_locations_itinerary, name='get_top_locations_itinerary'),
    
    path('event/', get_all_events, name='get_all_events'),
    path('event/<int:event_id>/', get_event, name='get_event'),
    path('event/create/', create_event, name='create_event'),
    path('event/<int:event_id>/update/', update_event, name='update_event'),
    path('event/<int:event_id>/delete/', delete_event, name='delete_event'),

    path('location/<int:location_id>/fee/create/', create_fee, name="create_fee"),
    path('location/<int:location_id>/fees/', get_fees, name="get_fees"),
    
    path('fee/<int:fee_id>/', get_fee, name='get_fee'),
    path('fee/<int:audience_id>/edit/', edit_fee, name='edit_fee'),
    path('fee/<int:fee_id>/edit/<int:audience_id>/delete', delete_fee, name='delete_fee'),

    # path('test/<int:day_id>/', test_function, name="test_function"),
]