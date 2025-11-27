"""
Tests for authentication endpoints.
"""

from django.contrib.auth import get_user_model

from rest_framework import status

import pytest

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
            "first_name": "New",
            "last_name": "User",
        }

        response = api_client.post("/api/v1/auth/register/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["user"]["email"] == "newuser@example.com"
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securepass123",
            "password_confirm": "differentpass",
        }

        response = api_client.post("/api/v1/auth/register/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        data = {"email": "test@example.com", "password": "testpass123"}

        response = api_client.post("/api/v1/auth/login/", data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data

    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials."""
        data = {"email": "test@example.com", "password": "wrongpassword"}

        response = api_client.post("/api/v1/auth/login/", data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    """Test user profile endpoint."""

    def test_get_profile(self, authenticated_client, user):
        """Test retrieving user profile."""
        response = authenticated_client.get("/api/v1/auth/profile/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["username"] == user.username

    def test_update_profile(self, authenticated_client, user):
        """Test updating user profile."""
        data = {"first_name": "Updated", "last_name": "Name"}

        response = authenticated_client.patch("/api/v1/auth/profile/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_profile_requires_auth(self, api_client):
        """Test that profile requires authentication."""
        response = api_client.get("/api/v1/auth/profile/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
