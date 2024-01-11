from django.utils import timezone
from .models import OTP
import random
import string

def generate_otp(user):
    otp_code = ''.join(random.choices(string.digits, k=6))
    expiration_time = timezone.now() + timezone.timedelta(minutes=15)
    
    otp_instance, created = OTP.objects.get_or_create(user=user)
    otp_instance.otp = otp_code
    otp_instance.expiration_time = expiration_time
    otp_instance.save()

    return otp_code