# Generated by Django 4.2.4 on 2024-01-11 01:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_alter_user_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='reqiures_otp',
            field=models.BooleanField(default=False),
        ),
    ]