# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-22 22:36
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0012_merge_20170622_2110'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ExportTaskResult',
            new_name='FileProducingTaskResult',
        ),
    ]