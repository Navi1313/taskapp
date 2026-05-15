from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("task_app", "0002_alter_task_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="completed_at",
            field=models.DateField(blank=True, null=True),
        ),
    ]
