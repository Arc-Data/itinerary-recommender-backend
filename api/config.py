from django.conf import settings
import pyrebase

FIREBASE_CONFIG = {
    'apiKey': settings.FIREBASE_API_KEY,
    'authDomain': settings.FIREBASE_AUTH_DOMAIN,
    'projectId': settings.FIREBASE_PROJECT_ID,
    'databaseURL': settings.FIREBASE_DATABASE_URL,
    'storageBucket': settings.FIREBASE_STORAGE_BUCKET,
    'messagingSenderId': settings.FIREBASE_MESSAGING_SENDER_ID,
    'appId': settings.FIREBASE_APP_ID,
    'measurementId': settings.FIREBASE_MEASUREMENT_ID,
}

firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
db = firebase.database()