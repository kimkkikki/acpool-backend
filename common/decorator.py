from functools import wraps
from flask import session, request
from common.acpool_response import response
from common.cache import cache
from acpool.models import Users
from flask.globals import g


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return response(error_code=1003)

        username = session['username']
        cache_key = 'user:{}'.format(username)
        user = cache.get(cache_key)
        if cache.get('user:{}'.format(username)) is None:
            user = Users.query.filter(Users.username == username).first()
            cache.set(cache_key, user, timeout=60)
        if user is None:
            session.pop('username', None)
            return response(error_code=1003)

        g.user = user

        return f(*args, **kwargs)

    return decorated_function


def cached(timeout=60, key='view/%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % request.path
            rv = cache.get(cache_key)
            if rv is not None:
                return rv
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            return rv

        return decorated_function

    return decorator
