from django.utils import timezone
from rest_framework import serializers

from .models import Task, User


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
            "completed_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at"]

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


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "userid",
            "firstname",
            "lastname",
            "dob",
        ]
        read_only_fields = ["userid"]

    def validate_dob(self, value):
        if value >= timezone.localdate():
            raise serializers.ValidationError("Date of birth must be in the past")
        return value

    def create(self, validated_data):
        return User.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance