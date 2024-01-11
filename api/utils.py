from .models import OTP
import random
import string

def generate_otp(user):
    otp_code = ''.join(random.choices(string.digits, k=6))
    otp_instance, created = OTP.objects.get_or_create(user=user)
    otp_instance.code = otp_code
    otp_instance.save()

    return otp_code