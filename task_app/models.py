import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Task(models.Model):

    class TaskStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    created_at = models.DateField(auto_now_add=True)
    due_at = models.DateField()
    completed_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def clean(self):
        super().clean()
        reference_date = self.created_at or timezone.localdate()
        if self.due_at < reference_date:
            raise ValidationError({"due_at": "Please use valid due Date"})

    def save(self, *args, **kwargs):
        if self.status == self.TaskStatus.COMPLETED:
            if self.completed_at is None:
                self.completed_at = timezone.localdate()
        else:
            self.completed_at = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.owner})"


class User(models.Model):
    userid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)
    dob = models.DateField()

    class Meta:
        ordering = ["lastname", "firstname"]

    def __str__(self):
        return f"{self.firstname} {self.lastname}"