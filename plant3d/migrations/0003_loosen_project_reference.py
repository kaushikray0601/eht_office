from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plant3d", "0002_sourcemodel_is_saved_case_sourcemodel_saved_at_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="sourcemodel",
            name="plant3d_sou_project_9e7f77_idx",
        ),
        migrations.RemoveIndex(
            model_name="sourcemodel",
            name="plant3d_sou_project_c95ad7_idx",
        ),
        migrations.RemoveIndex(
            model_name="sourcemodel",
            name="plant3d_sou_project_a2eefc_idx",
        ),
        migrations.RenameField(
            model_name="sourcemodel",
            old_name="project",
            new_name="project_id",
        ),
        migrations.AlterField(
            model_name="sourcemodel",
            name="project_id",
            field=models.CharField(db_index=True, max_length=80),
        ),
        migrations.AddIndex(
            model_name="sourcemodel",
            index=models.Index(fields=["project_id", "source_format"], name="plant3d_sou_project_9e7f77_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcemodel",
            index=models.Index(fields=["project_id", "content_signature"], name="plant3d_sou_project_c95ad7_idx"),
        ),
        migrations.AddIndex(
            model_name="sourcemodel",
            index=models.Index(fields=["project_id", "uploaded_by", "is_saved_case"], name="plant3d_sou_project_a2eefc_idx"),
        ),
    ]
