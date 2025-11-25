"""
Serializers for authentication endpoints.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile information."""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_verified', 'timezone', 'storage_used', 'api_calls_count',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'is_verified', 'storage_used', 'api_calls_count', 'date_joined', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match'
            })
        return attrs
    
    def create(self, validated_data):
        """Create user with hashed password."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_verified'] = user.is_verified
        
        return token
    
    def validate(self, attrs):
        """Add user data to token response."""
        data = super().validate(attrs)
        
        # Add user information
        data['user'] = UserSerializer(self.user).data
        
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate password change request."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match'
            })
        return attrs
    
    def validate_old_password(self, value):
        """Verify old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value
    
    def save(self, **kwargs):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
