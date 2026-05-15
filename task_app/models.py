import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone




class Task(models.Model):

    class TaskStatus(models.TextChoices):
        PENDING = "Pending", "Pending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20,choices=TaskStatus.choices,default=TaskStatus.PENDING)
    created_at = models.DateField(auto_now_add=True)
    due_at = models.DateField()

    class Meta:
        ordering = ["-created_at", "id"]

    def clean(self):
        super().clean()
        reference_date = self.created_at or timezone.localdate()
        if self.due_at < reference_date:
            raise ValidationError({"due_at": "Please use valid due Date"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.owner})"
