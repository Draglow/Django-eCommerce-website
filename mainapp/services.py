import requests
import json
import base64
import hashlib
import time
import uuid
import logging
from django.conf import settings
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from .models import Payment, TelebirrPayment

logger = logging.getLogger(__name__)

class TelebirrPaymentService:
    def __init__(self):
        self.api_key = settings.TELEBIRR_API_KEY
        self.api_secret = settings.TELEBIRR_API_SECRET
        self.api_url = settings.TELEBIRR_API_URL
        self.notify_url = settings.TELEBIRR_NOTIFY_URL
        self.return_url = settings.TELEBIRR_RETURN_URL

    def _encrypt(self, data):
        """Encrypt data using RSA public key"""
        try:
            key = RSA.importKey(self.public_key)
            cipher = PKCS1_v1_5.new(key)
            encrypted = cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def _generate_sign(self, data):
        """Generate signature for the request"""
        try:
            sign_str = f"{self.app_id}{data}{self.app_key}"
            return hashlib.sha256(sign_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Signature generation failed: {str(e)}")
            raise

    def create_payment(self, order, amount, subject, body):
        try:
            # Prepare payment data
            payment_data = {
                "outTradeNo": str(order.id),
                "subject": subject,
                "totalAmount": str(amount),
                "shortCode": self.api_key,
                "notifyUrl": self.notify_url,
                "returnUrl": self.return_url,
                "body": body
            }

            # Convert to JSON string
            json_data = json.dumps(payment_data)
            
            # Encode to base64
            encoded_data = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
            
            # Ensure the encoded string length is a multiple of 4
            padding = len(encoded_data) % 4
            if padding:
                encoded_data += '=' * (4 - padding)

            # Create payment record
            payment = TelebirrPayment.objects.create(
                order=order,
                amount=amount,
                transaction_id=str(order.id),
                status='pending'
            )

            # Prepare request data
            request_data = {
                "appId": self.api_key,
                "data": encoded_data
            }

            # Make API request
            response = requests.post(
                self.api_url,
                json=request_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    payment_url = result.get('paymentUrl')
                    return {
                        'success': True,
                        'payment_url': payment_url
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', 'Payment initiation failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'API request failed with status code: {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def verify_payment(self, transaction_id):
        try:
            payment = TelebirrPayment.objects.get(transaction_id=transaction_id)
            
            # Prepare verification data
            verify_data = {
                "outTradeNo": transaction_id,
                "appId": self.api_key
            }

            # Make API request to verify payment
            response = requests.post(
                f"{self.api_url}/verify",
                json=verify_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    payment.status = 'completed'
                    payment.save()
                    return {
                        'success': True,
                        'status': 'completed'
                    }
                else:
                    payment.status = 'failed'
                    payment.save()
                    return {
                        'success': False,
                        'error': result.get('message', 'Payment verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'API request failed with status code: {response.status_code}'
                }

        except TelebirrPayment.DoesNotExist:
            return {
                'success': False,
                'error': 'Payment not found'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 