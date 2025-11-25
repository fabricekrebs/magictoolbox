"""
Views for authentication (both web UI and API endpoints).
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    PasswordChangeSerializer
)

User = get_user_model()


# Template Views
class LoginForm(forms.Form):
    """Login form for web interface."""
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class RegistrationForm(forms.ModelForm):
    """Registration form for web interface."""
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data


def login_view(request):
    """Login page view."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                return redirect('core:home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'authentication/login.html', {'form': form})


def register_view(request):
    """Registration page view."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('authentication:login')
    else:
        form = RegistrationForm()
    
    return render(request, 'authentication/register.html', {'form': form})


@login_required
def profile_view(request):
    """User profile page view."""
    return render(request, 'authentication/profile.html')


def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('core:home')


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    POST /api/v1/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Create new user and return user data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'message': 'User registered successfully',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    JWT token obtain endpoint with custom claims.
    
    POST /api/v1/auth/login/
    """
    serializer_class = CustomTokenObtainPairSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile endpoint.
    
    GET/PUT/PATCH /api/v1/auth/profile/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Return current authenticated user."""
        return self.request.user


class PasswordChangeView(APIView):
    """
    Password change endpoint.
    
    POST /api/v1/auth/password/change/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
