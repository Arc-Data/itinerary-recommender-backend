import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from collections import OrderedDict
from .config import db


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)
    
class RecommendationsManager():
    def get_content_recommendations(self, preferences, budget):
        from api.models import ModelItinerary
        models_data = []

        for model in ModelItinerary.objects.all():
            if model.total_min_cost <= budget:
                model_data = {
                    'id': model.id,
                    'min_cost': model.total_min_cost,
                    'max_cost': model.total_max_cost,
                    'tags': model.get_tags,
                    'names': model.get_location_names
                }
                models_data.append(model_data)


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

        recommended_itineraries_data = recommended_itineraries_data[recommended_itineraries_data['jaccard_similarity'] > 0]
        recommended_itineraries_data = recommended_itineraries_data.sort_values(by='jaccard_similarity', ascending=False)
        recommended_itineraries_data.head(12).to_clipboard()

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


    def get_spot_chain_recommendation(self, user, location_id, preferences, visited_list):
        from .models import Spot
        max_distance = 10000


        clicks_weight = 0.05
        rating_weight = 0.15
        distance_weight = 0.7
        jaccard_weight = 0.1

        jaccard_weight_visited = 0.3

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"an unexpected error has occured: {e}")
        
        origin_spot = Spot.objects.get(id=location_id)

        spots = Spot.objects.exclude(id=location_id).exclude(id__in=visited_list)
        
        locations_data = []
        for spot in spots:
            distance_from_origin = spot.get_distance_from_origin(origin_spot)
            spot_data = {
                'id': spot.id,
                'name': spot.name,
                'tags': [tag.name for tag in spot.tags.all()],
                'rating': spot.get_avg_rating,
                'distance_from_origin': distance_from_origin
            }
            locations_data.append(spot_data)

        # binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)

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

        merged_data['jaccard_similarity'] = merged_data.apply(
            lambda row: (
                jaccard_weight_visited * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
                if row['id'] in visited_list
                else jaccard_weight * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
            ),
            axis=1
        )

        merged_data['weighted_score'] = (
            clicks_weight * merged_data['amount'] + 
            jaccard_weight * merged_data['jaccard_similarity'] + 
            rating_weight * merged_data['rating'] + 
            distance_weight * (max_distance - merged_data['distance_from_origin'])
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data_sorted  = merged_data.sort_values(by='scaled_score', ascending=False)

        keep_columns = ['id', 'name', 'binned_tags', 'rating', 'amount', 'jaccard_similarity', 'distance_from_origin', 'weighted_score', 'scaled_score']
        merged_data_sorted= merged_data_sorted[keep_columns]

        return merged_data_sorted.head(4)['id'].tolist()
    
    
    def get_foodplace_recommendation(self, user, location_id, visited_list):
        from .models import FoodPlace
        max_distance = 5000

        clicks_weight = 0.05
        rating_weight = 0.45
        distance_weight = 0.6

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"an unexpected error has occured: {e}")

        origin_foodplace = FoodPlace.objects.get(id=location_id)

        foodplaces = FoodPlace.objects.exclude(id=location_id).exclude(id__in=visited_list)

        locations_data = []
        for foodplace in foodplaces:
            distance_from_origin = foodplace.get_distance_from_origin(origin_foodplace)
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

        tags_binary = pd.get_dummies(locations_data['foodtags'].explode()).groupby(level=0).max().astype(int)
        binned_tags = tags_binary.apply(lambda row: row.to_numpy().tolist(), axis=1)
        
        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)
            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['binned_tags'] = binned_tags

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

        click_weight = 0.15
        jaccard_weight = 0.6
        rating_weight = 0.25

        jaccard_weight_visited = 0.3 

        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
        except Exception as e:
            print(f"An exception has occured while querying firebase data: {e}")
            return 

        locations_data = []
        spots = Spot.objects.exclude(tags=None).exclude(id__in=visited_list)

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

        
        if clicks_data:
            clicks_df = pd.DataFrame(clicks_data)

            merged_data = pd.merge(locations_data, clicks_df, left_on='id', right_on='location', how="left")
            merged_data['amount'] = merged_data['amount'].fillna(0)
        else:
            merged_data = locations_data
            merged_data['amount'] = 0

        merged_data['binned_tags'] = binned_tags

        merged_data['jaccard_similarity'] = merged_data.apply(
            lambda row: (
                jaccard_weight_visited * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
                if row['id'] in visited_list
                else jaccard_weight * self.calculate_jaccard_similarity(preferences, row['binned_tags'])
            ),
            axis=1
        )

        merged_data['weighted_score'] = (
            click_weight * merged_data['amount'] + jaccard_weight * merged_data['jaccard_similarity'] + rating_weight * merged_data['rating']
        )

        weighted_score_array = merged_data['weighted_score'].values.reshape(-1, 1)

        scaler = MinMaxScaler()
        merged_data['scaled_score'] = scaler.fit_transform(weighted_score_array)
        merged_data_sorted = merged_data.sort_values(by='scaled_score', ascending=False)
        keep_columns = ['id', 'name', 'tags', 'amount', 'binned_tags', 'rating', 'jaccard_similarity', 'weighted_score', 'scaled_score'] 
        merged_data_sorted = merged_data_sorted[keep_columns]
        merged_data_sorted.to_clipboard()

        return merged_data_sorted.head(4)['id'].tolist()

    def get_location_recommendation(self, user, location_id):
        
        
        try:
            user_clicks = db.child("users").child(user.id).child("clicks").get()
            clicks_data = user_clicks.val() or {}
            # print(f"User {user.id} clicks data: {clicks_data}")

        except Exception as e:
            print(f"An unexpected error has occurred: {e}")

        data = pd.read_csv('TravelPackage - Spot.csv')
        # prepare labels of necessary values
        tags_columns = ['Historical', 'Nature', 'Religious', 'Art', 'Activities', 'Entertainment', 'Culture']
        selected_columns = ['Place'] + tags_columns
        locations_data = data[selected_columns]

        locations_data.index = range(1, len(locations_data) + 1)
        locations_data = locations_data.assign(ID=locations_data.index)

        # drop unnecessary columns
        locations_data.drop(columns=set(locations_data.columns) - set(['Place'] + tags_columns + ['ID']), inplace=True)
        
        for click in clicks_data:
            click_location_id = click['location']
            click_count = click['amount']

            if click_location_id in locations_data['ID'].values:
                print(locations_data)
                locations_data.loc[locations_data['ID'] == click_location_id, tags_columns] *= click_count
        
        # select location id 
        selected_location_id = location_id
        selected_location = locations_data[locations_data['ID'] == selected_location_id]

        # recommendation portion
        if selected_location.empty:
            print(f"Location not found.")
            return None
        else:
            selected_vector = selected_location[tags_columns].values.reshape(1, -1)
            all_vectors = locations_data[locations_data['ID'] != selected_location_id][tags_columns].values

            cosine_similarity_scores = cosine_similarity(selected_vector, all_vectors)
            sorted_indices = cosine_similarity_scores[0].argsort()[::-1]

            top_n = 5

            # Filter out the selected location
            is_not_selected_location = locations_data['ID'] != selected_location_id
            top_recommendations = locations_data[is_not_selected_location].iloc[sorted_indices[:top_n]]

            # Print the result including similarity scores
            # print(f"Selected Location: {selected_location['Place'].values[0]} (ID: {selected_location_id}) with tags:")
            # print(selected_location[tags_columns])
            # print("\nTop Recommendations:")
            result_with_scores = top_recommendations[['ID', 'Place'] + tags_columns].copy()
            result_with_scores['Similarity'] = cosine_similarity_scores[0, sorted_indices[:top_n]]
            # print(result_with_scores)

            # result_with_scores.head()
            top_4_ids = result_with_scores.head(4)['ID'].tolist()

            return top_4_ids