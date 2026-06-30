from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cvs", "0003_alter_accessgrant_plan_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cv",
            name="photo_file",
            field=models.FileField(blank=True, null=True, upload_to="cvs/photos/source/"),
        ),
    ]
