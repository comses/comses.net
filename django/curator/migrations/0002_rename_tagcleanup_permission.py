# Generated by Django 2.0.4 on 2018-04-24 17:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('curator', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tagcleanup',
            options={'permissions': (('process_tagcleanup', 'Able to process tag cleanups'),)},
        ),
    ]
