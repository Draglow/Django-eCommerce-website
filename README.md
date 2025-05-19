# 🛒 Django E-Commerce Website

A full-featured and modern **E-Commerce platform** built with **Django**. The site supports user registration, dynamic cart management, order processing, product categorization, and real-time updates—all designed with a clean, responsive UI.


![Made with Python](https://img.shields.io/badge/Made%20with-Python%203.x-yellow?logo=python)

---

## 📸 Demo

![Demo Screenshot](https://i.imgur.com/cG1i2JO.png)

Live Demo: **[Coming Soon]**


## Features
- User authentication (email-based login & registration)
- Product listing and categorization
- Dynamic cart functionality with real-time updates
- Secure checkout process with Telebirr payment integration
- Order management and tracking
- Responsive and modern UI design

## Tech Stack
- **Backend**: Django
- **Frontend**: HTML, CSS, Bootstrap, Jquery
- **Database**: PostgreSQL
- **Payment Gateway**: Telebirr Integration,Paypal,Strip

## Installation

### Prerequisites
- Python 3.x
- PostgreSQL
- Virtual environment tool (venv or virtualenv)

### Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/Draglow/Django-eCommerce-website
   
   ```
2. Create and activate a virtual environment:
   ```sh
   python -m venv env
   source env/bin/activate  # On Windows use `env\Scripts\activate`
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Set up the database:
   ```sh
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Create a superuser for admin access:
   ```sh
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```sh
   python manage.py runserver
   ```

## Telebirr Payment Integration
To enable Telebirr payments, ensure you have the required credentials:
- Merchant AppId
- Fabric App ID
- ShortCode
- App Secret

Add these credentials in your Django settings file:
```python
TELEBIRR_CONFIG = {
    "APP_ID": "your_app_id",
    "FABRIC_APP_ID": "your_fabric_app_id",
    "SHORT_CODE": "your_short_code",
    "APP_SECRET": "your_app_secret",
}
```





## Contact
For any inquiries, reach out via email or open an issue on GitHub.

