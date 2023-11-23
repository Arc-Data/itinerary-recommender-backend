# Generated by Django 4.2.4 on 2023-11-23 07:34

import api.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_location_website_alter_location_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='locationimage',
            name='image',
            field=models.ImageField(default='location_images/DefaultLocationImage.jpg', max_length=512, upload_to=api.models.location_image_path),
        ),
    ]