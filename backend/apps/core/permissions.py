"""
Custom permissions for MagicToolbox.

Provides role-based and object-level permission classes.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    
    Assumes the model instance has an `owner` or `user` attribute.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to owner
        owner = getattr(obj, 'owner', None) or getattr(obj, 'user', None)
        return owner == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to only allow admin users to edit objects.
    
    Non-admin users can only perform read operations.
    """
    
    def has_permission(self, request, view):
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for admin users
        return request.user and request.user.is_staff
