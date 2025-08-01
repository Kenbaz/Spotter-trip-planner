# Generated by Django 5.2.1 on 2025-06-26 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trip_api', '0006_remove_stops_trip_api_st_amenity_265717_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='total_on_duty_time',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total on-duty time (driving + pickup/delivery time) in hours', max_digits=6, null=True),
        ),
    ]
