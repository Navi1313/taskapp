from django.utils import timezone
from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "status",
            "created_at",
            "due_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_due_at(self, value):
        reference_date = timezone.localdate()
        if self.instance is not None:
            reference_date = self.instance.created_at
        if value < reference_date:
            raise serializers.ValidationError("Please use valid due Date")
        return value

    def create(self, validated_data):
        task = Task(**validated_data)
        task.save()
        return task

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
