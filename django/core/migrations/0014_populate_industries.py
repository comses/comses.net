# Generated by Django 3.2.12 on 2022-06-10 22:17

from django.db import migrations


initial_industries = [
    "college/university", "K-12 educator", "government", "private", "non-profit", "student",
]


def initialize_industries(apps, schema_editor):
    Industry = apps.get_model('core', 'Industry')

    for industry_name in initial_industries:
        Industry.objects.create(name=industry_name)

def clear_industries(apps, schema_editor):
    Industry = apps.get_model('core', 'Industry')
    Industry.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_add_industry'),
    ]

    operations = [
        migrations.RunPython(initialize_industries, clear_industries),
    ]