from django.utils import timezone
from rest_framework import serializers

from .models import Task, User
from .utils import BCrruptUtil


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
            "username",
            "password",
        ]
        read_only_fields = ["userid"]
        extra_kwargs = {
            "password": {"write_only": True, "required": True},
            "username": {"required": True}
        }

    def validate_dob(self, value):
        if value >= timezone.localdate():
            raise serializers.ValidationError("Date of birth must be in the past")
        return value

    def create(self, validated_data):
        password = validated_data.get("password")
        if password:
            validated_data["password"] = BCrruptUtil.encrypt_password(password)
        return User.objects.create(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.get("password")
        if password:
            validated_data["password"] = BCrruptUtil.encrypt_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only serializer that exposes all user fields except password."""

    class Meta:
        model = User
        fields = [
            "userid",
            "firstname",
            "lastname",
            "dob",
            "username",
        ]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if not username or not password:
            raise serializers.ValidationError("Both username and password are required.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        if not BCrruptUtil.verify_method(password, user.password):
            raise serializers.ValidationError("Invalid credentials.")

        attrs["user"] = user
        return attrs

        