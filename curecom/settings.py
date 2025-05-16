# Allauth Settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_FIELDS = ['email', 'password1', 'password2']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_PASSWORD_MIN_LENGTH = 8
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_USERNAME_BLACKLIST = ['admin', 'administrator', 'root', 'superuser']
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_USERNAME_VALIDATORS = 'mainapp.validators.custom_username_validators'
ACCOUNT_FORMS = {
    'signup': 'mainapp.forms.CustomSignupForm',
    'login': 'mainapp.forms.CustomLoginForm',
    'reset_password': 'mainapp.forms.CustomResetPasswordForm',
    'reset_password_from_key': 'mainapp.forms.CustomResetPasswordKeyForm',
    'change_password': 'mainapp.forms.CustomChangePasswordForm',
    'add_email': 'mainapp.forms.CustomAddEmailForm',
    'set_password': 'mainapp.forms.CustomSetPasswordForm',
}

# Import Telebirr settings
from .telebirr_settings import *

# Telebirr Payment Settings
TELEBIRR_API_KEY = 'your_api_key_here'  # Replace with your actual API key
TELEBIRR_API_SECRET = 'your_api_secret_here'  # Replace with your actual API secret
TELEBIRR_API_URL = 'https://api.telebirr.com/api/payment'  # Replace with actual API URL
TELEBIRR_NOTIFY_URL = 'http://your-domain.com/payment/notify/'  # Replace with your actual notify URL
TELEBIRR_RETURN_URL = 'http://your-domain.com/payment/return/'  # Replace with your actual return URL

# Internationalization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('am', 'አማርኛ'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... rest of your middleware ...
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'widget_tweaks',
    'mainapp',
    # ... existing code ...
] 