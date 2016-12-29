# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-12-20 17:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='exportrun',
            name='expiration',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
