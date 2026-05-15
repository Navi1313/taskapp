from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("owner", models.CharField(max_length=255)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("Pending", "Pending")],
                        default="Pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateField(auto_now_add=True)),
                ("due_at", models.DateField()),
            ],
            options={
                "ordering": ["-created_at", "id"],
            },
        ),
    ]
