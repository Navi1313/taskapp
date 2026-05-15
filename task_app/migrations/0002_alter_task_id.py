import uuid

from django.db import migrations, models


def clear_tasks(apps, schema_editor):
    Task = apps.get_model("task_app", "Task")
    Task.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("task_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(clear_tasks, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="task",
            name="id",
        ),
        migrations.AddField(
            model_name="task",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
