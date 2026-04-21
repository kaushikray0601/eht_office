from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("idfviewer", "0002_plotplanoverlay"),
    ]

    operations = [
        migrations.AddField(
            model_name="idffile",
            name="source_format",
            field=models.CharField(
                choices=[("IDF", "IDF"), ("PCF", "PCF")],
                default="IDF",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="idfcomponent",
            name="source_format",
            field=models.CharField(
                choices=[("IDF", "IDF"), ("PCF", "PCF")],
                default="IDF",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="idfcomponent",
            index=models.Index(
                fields=["project", "source_format"],
                name="idfviewer_i_project_9f4374_idx",
            ),
        ),
    ]
