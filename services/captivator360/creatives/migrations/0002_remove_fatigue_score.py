from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("creatives", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="creativeperformancedaily",
            name="fatigue_score",
        ),
    ]
