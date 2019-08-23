from flask import jsonify


def get_error_message(code: int):
    return {
        1000: 'Invalid request.',
        1001: 'Your information is already exist.',
        1002: 'Incorrect id or password',
        1003: 'Login session is expired',
        1004: 'Password is incorrect.',
        1005: 'Same as previous password.',
        1006: 'Invalid otp code',
        1007: 'Unknown coin',
        1008: 'Unknown block',
        1009: 'Duplicate Address',
        1010: 'reCaptcha Validation Failure',
        1011: 'Invalid Address',
        1012: 'Invalid Verification code',
        1013: 'Can not send email for 10 minutes after sending email once.',
        1014: 'We can not send email. Please verify your email address.',
        1015: 'Add New Wallet Failure',
        1016: 'Edit Wallet Failure',
        1017: 'Can not send Coin.',
        1018: 'User does not exist.',
    }.get(code, 'default error message')


def response(result=None, error_code: int = None) -> jsonify:
    if result is None and error_code is None:
        return jsonify({'result': True, 'error': None})

    if error_code is not None:
        return jsonify({'result': result, 'error': {'code': error_code, 'message': get_error_message(code=error_code)}})
    else:
        return jsonify({'result': result, 'error': None})
