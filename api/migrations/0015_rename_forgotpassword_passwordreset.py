# Generated by Django 4.2.4 on 2023-12-31 07:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_forgotpassword'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ForgotPassword',
            new_name='PasswordReset',
        ),
    ]
