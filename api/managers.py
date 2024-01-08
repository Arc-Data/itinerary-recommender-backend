import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
# from memory_profiler import profile

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from collections import OrderedDict, defaultdict
from .config import db


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email field must be set')
        print("I am here")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)
    
class RecommendationsManager():
    def calculate_activity_score(self, user_activities, model_spot_activities):
        activity_score = 0

        for activity, frequency in model_spot_activities.items():
            user_frequency = user_activities.get(activity, 0)
            try:
                activity_score += user_frequency / (frequency + 1)
            except RuntimeWarning as e:
                activity_score += 0
                print("Error", {e})

        return activity_score

    # @profile
    def get_content_recommendations(self, preferences, budget, visited_list, activity_list):
        from api.models import ModelItinerary, ModelItineraryLocationOrder
        models_data = []

        for model in ModelItinerary.objects.all():
            if model.total_min_cost <= budget:
                model_locations = set()
                order_penalty_factor = 1.0

                for order_entry in ModelItineraryLocationOrder.objects.filter(itinerary=model):
                    spot_id = order_entry.spot.id
                    model_locations.add(spot_id)

                common_visited = model_locations.intersection(visited_list)

                if len(model_locations) > 0:
                    visited_ratio = len(common_visited) / len(model_locations)
                    order_penalty_factor = max(0, 1 - visited_ratio)
                else:
                    order_penalty_factor = 1

                model_data = {
                    'id': model.id,
                    'min_cost': model.total_min_cost,
                    'max_cost': model.total_max_cost,
                    'names': model.get_location_names,
                    'tags': model.get_tags,
                    'activities': model.get_activities,
                    'order_penalty_factor': order_penalty_factor
                }
                models_data.append(model_data)

        print("Did i get past here though?")

        recommended_itineraries_data = pd.DataFrame.from_records(models_data)
        tags_binary = pd.get_dummies(recommended_itineraries_data['tags'].explode()).groupby(level=0).max().astype(int)
        binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)

        recommended_itineraries_data['binned_tags'] = binned_tags 
        recommended_itineraries_data['jaccard_similarity'] = recommended_itineraries_data.apply(
            lambda row: (
                self.calculate_jaccard_similarity(preferences, row['binned_tags'])
            ),
            axis=1
        )

        activity_scores = recommended_itineraries_data['activities'].apply(
            lambda row: self.calculate_activity_score(activity_list, row)
        )

        activity_scores = activity_scores.values.reshape(1, -1)
        activity_scores = activity_scores / activity_scores.max() if activity_scores.max() != 0 else activity_scores / 1.0
        recommended_itineraries_data['activity_score'] = activity_scores.flatten()

        jaccard_weight = 0.6
        activity_weight = 0.1
        penalty_weight = 0.3

        recommended_itineraries_data['final_score'] = (
            jaccard_weight * recommended_itineraries_data['jaccard_similarity'] + 
            penalty_weight * recommended_itineraries_data['order_penalty_factor'] + 
            activity_weight * recommended_itineraries_data['activity_score']
        )

        recommended_itineraries_data['final_score'] = recommended_itineraries_data['final_score'].values.reshape(-1, 1)
        recommended_itineraries_data['final_score'] = recommended_itineraries_data['final_score'] / recommended_itineraries_data['final_score'].max()
        
        keep_columns = ['id', 'names' ,'min_cost', 'max_cost', 'activity_score', 'order_penalty_factor', 'jaccard_similarity','activity_score','final_score']
        recommended_itineraries_data = recommended_itineraries_data[keep_columns]
        recommended_itineraries_data = recommended_itineraries_data.sort_values(by='final_score', ascending=False)

        return recommended_itineraries_data.head(12)['id'].tolist()
        

    def get_hybrid_recommendations(self):
        return None
    
    def calculate_jaccard_similarity(self, user_preferences, spot_tags):
        # Convert user preferences and spot tags to sets
        user_array = np.array(user_preferences)
        spot_array = np.array(spot_tags)

        # Calculate Jaccard similarity
        intersection = np.sum(np.logical_and(user_array, spot_array))
        union = np.sum(np.logical_or(user_array, spot_array))
        similarity = intersection / union if union != 0 else 0.0

        return similarity

    # @profile
    def get_spot_chain_recommendation(self, user, location_id, preferences, visited_list, activity_count):
        from .models import Spot, Location
        max_distance = 10000

        clicks_weight = 0.05
        rating_weight = 0.15
        distance_weight = 0.5
        activity_weight = 0.1
        jaccard_weight = 0.1
        visited_weight = 0.1

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"an unexpected error has occured: {e}")
        
        tag_visit_counts = defaultdict(int)
        origin_spot = Location.objects.get(id=location_id)
        spots = Spot.objects.exclude(id=location_id).exclude(tags=None)

        locations_data = []
        for spot in spots:
            if spot.id not in visited_list:
                distance_from_origin = spot.get_distance_from_origin(origin_spot)
                spot_data = {
                    'id': spot.id,
                    'name': spot.name,
                    'tags': [tag.name for tag in spot.tags.all()],
                    'rating': spot.get_avg_rating,
                    'distance_from_origin': distance_from_origin,
                    'activities': spot.get_activities,
                }
                locations_data.append(spot_data)
            else:
                for tag in spot.tags.all():
                    tag_name = tag.name
                    tag_visit_counts[tag_name] += 1

        
        locations_data = pd.DataFrame.from_records(locations_data)
        tags_binary = pd.get_dummies(locations_data['tags'].explode()).groupby(level=0).max().astype(int)
        binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)

        locations_data = locations_data.sort_values(by='distance_from_origin')
        locations_data = locations_data.head(15)

        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)
            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['binned_tags'] = binned_tags
        print(merged_data['activities'])

        merged_data['jaccard_similarity'] = merged_data.apply(
            lambda row: (
                jaccard_weight * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
            ),
            axis=1
        )

        merged_data['activities_count'] = merged_data['activities'].apply(
            lambda activities: sum(activity_count[activity] for activity in activities) 
        )
        merged_data['activity_count_score'] = activity_weight * merged_data['activities_count']

        merged_data['visit_count'] = merged_data['tags'].apply(lambda tags: sum(tag_visit_counts[tag] for tag in tags))
        merged_data['visit_count_score'] = visited_weight * merged_data['visit_count']

        merged_data['weighted_score'] = (
            clicks_weight * merged_data['amount'] + 
            jaccard_weight * merged_data['jaccard_similarity'] + 
            rating_weight * merged_data['rating'] + 
            distance_weight * (max_distance - merged_data['distance_from_origin']) + 
            visited_weight * merged_data['visit_count_score'] + 
            activity_weight * merged_data['activity_count_score']
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data = merged_data[merged_data['scaled_score'] != 0]
        merged_data_sorted  = merged_data.sort_values(by='scaled_score', ascending=False)

        keep_columns = ['id', 'name', 'binned_tags', 'rating', 'amount', 'activities','activities_count', 'activity_count_score', 'jaccard_similarity', 'visit_count_score', 'distance_from_origin', 'weighted_score', 'scaled_score']
        merged_data_sorted= merged_data_sorted[keep_columns]

        return merged_data_sorted.head(4)['id'].tolist()
    
    
    def get_foodplace_recommendation(self, user, location_id, visit_list):
        from .models import FoodPlace, Location
        max_distance = 5000

        clicks_weight = 0.05
        rating_weight = 0.35
        distance_weight = 0.6

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"an unexpected error has occured: {e}")

        origin_location = Location.objects.get(id=location_id)
        foodplaces = FoodPlace.objects.exclude(id=location_id).exclude(id__in=visit_list)

        locations_data = []
        for foodplace in foodplaces:
            distance_from_origin = foodplace.get_distance_from_origin(origin_location)
            foodplace_data = {
                'id': foodplace.id,
                'name': foodplace.name,
                'foodtags': [tag.name for tag in foodplace.tags.all()],
                'rating': foodplace.get_avg_rating,
                'distance_from_origin': distance_from_origin
            }
            locations_data.append(foodplace_data)

        locations_data = pd.DataFrame.from_records(locations_data)
        locations_data = locations_data.sort_values(by='distance_from_origin')
        locations_data = locations_data.head(15)
        locations_data = locations_data.reset_index()

        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)
            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['binned_tags'] = 0

        merged_data['weighted_score'] = (
            clicks_weight * merged_data['amount'] + 
            rating_weight * merged_data['rating'] + 
            distance_weight * (max_distance - merged_data['distance_from_origin'])
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data_sorted = merged_data.sort_values(by='scaled_score', ascending=False)

        keep_columns = ['id', 'name', 'binned_tags', 'rating', 'amount', 'distance_from_origin', 'weighted_score', 'scaled_score']
        merged_data_sorted = merged_data_sorted[keep_columns]

        return merged_data_sorted.head(4)['id'].tolist()
    

    def get_homepage_recommendation(self, user, preferences, visited_list):
        from .models import Spot

        click_weight = 0.1
        jaccard_weight = 0.5
        rating_weight = 0.2
        visited_weight = 0.2

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"An exception has occured while querying firebase data: {e}")
            return 

        locations_data = []
        tag_visit_counts = defaultdict(int)
        spots = Spot.objects.exclude(tags=None)

        for spot in spots:
            if spot.id not in visited_list:
                spot_data = {
                    'id': spot.id,
                    'name': spot.name,
                    'tags': [tag.name for tag in spot.tags.all()],
                    'rating': spot.get_avg_rating
                }
                locations_data.append(spot_data)
            else:
                for tag in spot.tags.all():
                    tag_name = tag.name
                    tag_visit_counts[tag_name] += 1

        locations_data = pd.DataFrame.from_records(locations_data)

        tags_binary = pd.get_dummies(locations_data['tags'].explode()).groupby(level=0).max().astype(int)
        binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)

        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)

            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['binned_tags'] = binned_tags

        merged_data['visit_count'] = merged_data['tags'].apply(lambda tags: sum(tag_visit_counts[tag] for tag in tags))
        merged_data['visit_count_score'] = visited_weight * merged_data['visit_count']

        merged_data['jaccard_similarity'] = merged_data.apply(
            lambda row: (
                jaccard_weight * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
            ),
            axis=1
        )

        merged_data['weighted_score'] = (
            click_weight * merged_data['amount'] + 
            jaccard_weight * merged_data['jaccard_similarity'] + 
            rating_weight * merged_data['rating'] + 
            visited_weight * merged_data['visit_count_score']
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data_sorted = merged_data.sort_values(by='scaled_score', ascending=False)
        keep_columns = ['id', 'name', 'tags', 'amount', 'binned_tags', 'rating', 'jaccard_similarity', 'weighted_score', 'visit_count', 'visit_count_score', 'scaled_score' ] 
        merged_data_sorted = merged_data_sorted[keep_columns]

        return merged_data_sorted.head(4)['id'].tolist()

    def get_location_recommendation(self, user, origin_binned_tags, location_id, visited_list):
        from api.models import Spot
        # this is from the details page, put higher prioritization on preference similarity
        # but should I add a weight for the tags the user has already visited?

        jaccard_weight = 0.7
        rating_weight = 0.2
        clicks_weight = 0.1

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"An unexpected error has occurred: {e}")

        locations_data = []
        tag_visit_counts = defaultdict(int)
        spots = Spot.objects.exclude(tags=None, id=location_id)

        for spot in spots:
            spot_data = {
                'id': spot.id,
                'name': spot.name,
                'tags': [tag.name for tag in spot.tags.all()],
                'rating': spot.get_avg_rating
            }
            locations_data.append(spot_data)

        locations_data = pd.DataFrame.from_records(locations_data)
        tags_binary = pd.get_dummies(locations_data['tags'].explode()).groupby(level=0).max().astype(int)
        binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)
        locations_data['binned_tags'] = binned_tags 

        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)

            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['jaccard_similarity'] = merged_data.apply(
            lambda row: (
                self.calculate_jaccard_similarity(origin_binned_tags, row['binned_tags'])
            ),
            axis=1
        )

        merged_data['weighted_score'] = (
            clicks_weight * merged_data['amount'] + jaccard_weight * merged_data['jaccard_similarity'] + rating_weight * merged_data['rating']
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data = merged_data.sort_values(by='scaled_score', ascending=False)

        return merged_data.head(4)['id'].to_list()