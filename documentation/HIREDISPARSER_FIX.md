# HiredisParser Compatibility Fix

## Issue
After deploying the Redis session storage fix, users were still experiencing HTTP 500 errors when attempting to login. The error logs revealed:

```
ImportError: Module "redis.connection" does not define a "HiredisParser" attribute/class
```

## Root Cause
The application was configured to use `HiredisParser` in the Django cache backend settings:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",  # ❌ Incompatible
            ...
        },
        ...
    }
}
```

**Problem**: `HiredisParser` was removed in redis-py 5.0+. The application is using redis-py 5.1.1, which only includes the default `PythonParser`.

## Solution
Removed the explicit `PARSER_CLASS` configuration from `magictoolbox/settings/base.py`:

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Removed PARSER_CLASS - django-redis will use default PythonParser
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "magictoolbox",
        "TIMEOUT": 300,
    }
}
```

## Changes Made

### File: `magictoolbox/settings/base.py`
- **Commit**: `b134239`
- **Change**: Removed `"PARSER_CLASS": "redis.connection.HiredisParser"` line from `CACHES["default"]["OPTIONS"]`
- **Reason**: redis-py 5.0+ removed HiredisParser in favor of the default PythonParser

## Deployment
- **Deployed**: November 27, 2025
- **Revision**: `app-we-magictoolbox-dev-01--6oh1we0`
- **Status**: ✅ Successful

## Verification
1. **User Creation**: Successfully created test user `testuser` via Django shell
2. **Login Test**: POST to `/auth/login/` returned HTTP 200 (success)
3. **Error Logs**: No HiredisParser errors found in application logs
4. **Request Completion**: All login requests completed successfully without exceptions

## Technical Details

### redis-py Version History
- **redis-py < 5.0**: Supported both HiredisParser (C-based, faster) and PythonParser (pure Python)
- **redis-py >= 5.0**: Only PythonParser available (HiredisParser removed)
- **Current Version**: redis-py 5.1.1 (installed via django-redis dependency)

### django-redis Compatibility
- django-redis 5.4.0 is compatible with redis-py 5.x
- When `PARSER_CLASS` is not specified, django-redis automatically uses the default parser (PythonParser)
- No performance degradation expected for typical Django session operations

## Related Documentation
- [LOGIN_ERROR_FIX.md](./LOGIN_ERROR_FIX.md) - Previous Redis session storage fix
- [redis-py 5.0 Release Notes](https://github.com/redis/redis-py/releases/tag/v5.0.0) - HiredisParser removal announcement

## Prevention
To avoid similar issues in the future:
1. Review library upgrade guides before major version updates
2. Remove deprecated configuration options when upgrading dependencies
3. Test authentication flows after infrastructure changes
4. Monitor application logs for import errors during deployments

## Status: ✅ RESOLVED
- Login functionality working correctly
- No HiredisParser errors in logs
- Redis session storage functioning as expected
