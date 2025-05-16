from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg, Count, Sum, F
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Coupon, ProductRating, Newsletter, ProductReview, ReviewImage, UserProduct, Conversation, Message, TelebirrPayment, User
from .forms import CheckoutForm, ProductReviewForm, ReviewImageForm, UserProductForm
import paypalrestsdk
import json
import requests
from decimal import Decimal
from django.utils import timezone
import logging
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .services import TelebirrPaymentService
from datetime import timedelta

logger = logging.getLogger(__name__)

def home(request):
    featured_products = Product.objects.filter(available=True)[:8]
    categories = Category.objects.all()
    return render(request, 'mainapp/home.html', {
        'featured_products': featured_products,
        'categories': categories
    })

def product_list(request, category_slug=None):
    # Get category_slug from URL parameter or GET parameter
    category_slug = category_slug or request.GET.get('category')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'name')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    products = Product.objects.filter(available=True)
    
    # Handle multiple category filters
    category_ids = request.GET.getlist('category')
    if category_ids:
        products = products.filter(category_id__in=category_ids)
    elif category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply price range filters if provided
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            pass
    
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            pass
    
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:
        products = products.order_by('name')
    
    # Annotate products with average rating and review count
    products = products.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )
    
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    return render(request, 'mainapp/product_list.html', {
        'products': products,
        'categories': Category.objects.all(),
        'current_category': category_slug,
        'current_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'selected_categories': category_ids
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    
    # Get related products with ratings
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating', '-created_at')[:12]  # Show 12 related products
    
    # Get average rating and review count for the current product
    avg_rating = product.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    review_count = product.reviews.count()
    
    # Get user's existing rating if any
    user_rating = None
    if request.user.is_authenticated:
        try:
            user_rating = ProductReview.objects.get(product=product, user=request.user)
        except ProductReview.DoesNotExist:
            pass
    
    return render(request, 'mainapp/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'avg_rating': round(avg_rating, 1),
        'review_count': review_count,
        'user_rating': user_rating
    })

@csrf_exempt
def cart_add(request):
    if request.method == 'POST':
        try:
            # Get product_id and quantity from request
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                product_id = data.get('product_id')
                quantity = data.get('quantity', 1)
            else:
                product_id = request.POST.get('product_id')
                quantity = request.POST.get('quantity', 1)

            product = get_object_or_404(Product, id=product_id)
            
            if request.user.is_authenticated:
                # Check if product already exists in cart
                cart_item = CartItem.objects.filter(
                    cart__user=request.user,
                    product=product
                ).first()
                
                if cart_item:
                    # Product already in cart
                    return JsonResponse({
                        'status': 'exists',
                        'message': 'Product is already in your cart',
                        'cart_count': CartItem.objects.filter(cart__user=request.user).count()
                    })
                
                # Create or get cart
                cart, created = Cart.objects.get_or_create(user=request.user)
                
                # Create cart item
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity
                )
                
                cart_count = CartItem.objects.filter(cart__user=request.user).count()
            else:
                # Handle anonymous user
                cart = request.session.get('cart', {})
                
                if str(product_id) in cart:
                    # Product already in cart
                    return JsonResponse({
                        'status': 'exists',
                        'message': 'Product is already in your cart',
                        'cart_count': len(cart)
                    })
                
                cart[str(product_id)] = {
                    'quantity': quantity,
                    'price': str(product.price)
                }
                request.session['cart'] = cart
                cart_count = len(cart)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product added to cart successfully',
                'cart_count': cart_count
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@csrf_exempt
def cart_update(request):
    if request.method == 'POST':
        try:
            # Try to parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                item_id = data.get('item_id')
                product_id = data.get('product_id')
                quantity = int(data.get('quantity', 1))
            else:
                # Handle form data
                item_id = request.POST.get('item_id')
                product_id = request.POST.get('product_id')
                quantity = int(request.POST.get('quantity', 1))
            
            if request.user.is_authenticated:
                cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
                cart_item.quantity = quantity
                cart_item.save()
                
                return JsonResponse({
                    'success': True,
                    'cart_count': cart_item.cart.items.count(),
                    'total': str(cart_item.cart.get_total()),
                    'subtotal': str(cart_item.get_cost())
                })
            else:
                # Handle anonymous users
                cart = request.session.get('cart', {})
                if not isinstance(cart, dict):
                    cart = {}
                
                # Use product_id for non-logged-in users
                if product_id:
                    cart[str(product_id)] = {
                        'quantity': quantity,
                        'price': str(Product.objects.get(id=product_id).price)
                    }
                else:
                    return JsonResponse({'success': False, 'message': 'Product ID is required'}, status=400)
                
                request.session['cart'] = cart
                request.session.modified = True
                
                # Calculate totals
                total = Decimal('0')
                for product_id, item_data in cart.items():
                    try:
                        product = Product.objects.get(id=product_id)
                        total += product.price * Decimal(item_data['quantity'])
                    except Product.DoesNotExist:
                        continue
                
                return JsonResponse({
                    'success': True,
                    'cart_count': sum(int(item['quantity']) for item in cart.values()),
                    'total': str(total),
                    'subtotal': str(total)
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid quantity value'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def cart_remove(request):
    if request.method == 'POST':
        try:
            # Try to parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                item_id = data.get('item_id')
                product_id = data.get('product_id')
            else:
                # Handle form data
                item_id = request.POST.get('item_id')
                product_id = request.POST.get('product_id')
            
            if request.user.is_authenticated:
                cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
                cart = cart_item.cart
                cart_item.delete()
                
                return JsonResponse({
                    'success': True,
                    'cart_count': cart.items.count(),
                    'total': str(cart.get_total())
                })
            else:
                # Handle anonymous users
                cart = request.session.get('cart', {})
                if not isinstance(cart, dict):
                    cart = {}
                
                # Use product_id for non-logged-in users
                if product_id and str(product_id) in cart:
                    del cart[str(product_id)]
                    request.session['cart'] = cart
                    request.session.modified = True
                    
                    # Calculate total
                    total = Decimal('0')
                    for pid, item_data in cart.items():
                        try:
                            product = Product.objects.get(id=pid)
                            total += product.price * Decimal(item_data['quantity'])
                        except Product.DoesNotExist:
                            continue
                    
                    return JsonResponse({
                        'success': True,
                        'cart_count': sum(int(item['quantity']) for item in cart.values()),
                        'total': str(total)
                    })
                else:
                    return JsonResponse({'success': False, 'message': 'Item not found in cart'}, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def cart(request):
    logger.debug("Accessing cart view")
    if request.user.is_authenticated:
        # Handle authenticated users
        cart, created = Cart.objects.get_or_create(user=request.user)
        logger.debug(f"Authenticated user cart - Items: {cart.items.count()}")
    else:
        # Handle anonymous users
        cart = None
        cart_items = []
        total = 0
        session_cart = request.session.get('cart', {})
        logger.debug(f"Session cart contents: {session_cart}")
        
        if isinstance(session_cart, dict):
            for product_id, quantity in session_cart.items():
                try:
                    product = Product.objects.get(id=product_id)
                    # Ensure quantity is an integer
                    quantity = int(quantity) if isinstance(quantity, (int, str)) else 1
                    subtotal = product.price * quantity
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
                    total += subtotal
                except Product.DoesNotExist:
                    logger.error(f"Product not found: {product_id}")
                    continue
        
        logger.debug(f"Anonymous user cart - Items: {len(cart_items)}, Total: {total}")
    
    context = {
        'cart': cart,
        'cart_items': cart_items if not request.user.is_authenticated else None,
        'total': total if not request.user.is_authenticated else None
    }
    return render(request, 'mainapp/cart.html', context)

@login_required
def checkout(request):
    cart = Cart.objects.get(user=request.user)
    if cart.items.count() == 0:
        return redirect('cart')
        
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # Calculate totals
                subtotal = cart.get_subtotal()
                discount = cart.get_discount()
                shipping_cost = Decimal('10.00')  # Example shipping cost
                total = subtotal - discount + shipping_cost
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                    postal_code=form.cleaned_data['postal_code'],
                    city=form.cleaned_data['city'],
                    country=form.cleaned_data['country'],
                    payment_method=form.cleaned_data['payment_method'],
                    total=total,
                    subtotal=subtotal,
                    discount=discount,
                    shipping_cost=shipping_cost
                )
                
                # Add items to order
                for item in cart.items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                
                # Clear the cart
                cart.items.all().delete()
                cart.coupon = None
                cart.save()
                
                # Handle payment based on selected method
                payment_method = form.cleaned_data['payment_method']
                if payment_method == 'telebirr':
                    redirect_url = reverse('mainapp:telebirr_payment', args=[order.id])
                elif payment_method == 'paypal':
                    redirect_url = reverse('mainapp:paypal_payment', args=[order.id])
                else:
                    order.paid = True
                    order.status = 'processing'
                    order.save()
                    redirect_url = reverse('mainapp:order_detail', args=[order.id])

                # Handle AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'redirect_url': redirect_url
                    })
                
                # Handle regular form submission
                messages.success(request, 'Order placed successfully!')
                return redirect(redirect_url)

            except Exception as e:
                error_message = f'An error occurred while processing your order: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_message
                    }, status=400)
                
                messages.error(request, error_message)
                return render(request, 'mainapp/checkout.html', {
                    'form': form,
                    'cart': cart,
                    'subtotal': cart.get_subtotal(),
                    'discount': cart.get_discount(),
                    'total': cart.get_total()
                })
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please correct the errors in the form.',
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CheckoutForm()
        
    return render(request, 'mainapp/checkout.html', {
        'form': form,
        'cart': cart,
        'subtotal': cart.get_subtotal(),
        'discount': cart.get_discount(),
        'total': cart.get_total()
    })

@login_required
def apply_coupon(request):
    if request.method == 'POST':
        # Try to get code from JSON data first
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                code = data.get('code')
            except json.JSONDecodeError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON data'
                })
        else:
            # Get code from form data
            code = request.POST.get('code')
            
        if not code:
            return JsonResponse({
                'status': 'error',
                'message': 'Coupon code is required'
            })
            
        try:
            coupon = Coupon.objects.get(code=code)
            
            # Check if coupon is active
            if not coupon.active:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This coupon is no longer active'
                })
            
            # Check validity period
            now = timezone.now()
            if now < coupon.valid_from:
                return JsonResponse({
                    'status': 'error',
                    'message': f'This coupon is not valid until {coupon.valid_from.strftime("%Y-%m-%d")}'
                })
            
            if now > coupon.valid_to:
                return JsonResponse({
                    'status': 'error',
                    'message': f'This coupon expired on {coupon.valid_to.strftime("%Y-%m-%d")}'
                })
            
            # Get user's cart
            try:
                cart = Cart.objects.get(user=request.user)
            except Cart.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No cart found'
                })
            
            # Apply coupon to cart
            cart.coupon = coupon
            cart.save()
            
            # Calculate totals
            subtotal = cart.get_subtotal()
            discount = cart.get_discount()
            total = cart.get_total()
            
            return JsonResponse({
                'status': 'success',
                'valid': True,
                'message': 'Coupon applied successfully',
                'discount_amount': str(discount),
                'subtotal': str(subtotal),
                'cart_total': str(total),
                'cart_count': cart.items.count()
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid coupon code'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
            
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'mainapp/order_list.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'mainapp/order_detail.html', {'order': order})

@login_required
def paypal_payment(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Check if PayPal credentials are configured
        if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_SECRET_KEY:
            logger.error("PayPal credentials not configured")
            messages.error(request, 'Payment system is not properly configured. Please contact support.')
            return redirect('mainapp:order_detail', order_id=order.id)
        
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_SECRET_KEY
        })
        
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(f'/payment/paypal/execute/{order.id}/'),
                "cancel_url": request.build_absolute_uri(f'/payment/paypal/cancel/{order.id}/')
            },
            "transactions": [{
                "amount": {
                    "total": str(order.get_total_cost()),
                    "currency": "USD"
                },
                "description": f"Order #{order.id}"
            }]
        })
        
        if payment.create():
            for link in payment.links:
                if link.method == "REDIRECT":
                    return redirect(link.href)
        
        logger.error(f"Failed to create PayPal payment: {payment.error}")
        messages.error(request, 'Failed to create PayPal payment. Please try again or choose a different payment method.')
        return redirect('mainapp:order_detail', order_id=order.id)
        
    except Exception as e:
        logger.error(f"PayPal payment error: {str(e)}")
        messages.error(request, 'An error occurred while processing your payment. Please try again later.')
        return redirect('mainapp:order_detail', order_id=order.id)

@login_required
def telebirr_payment(request, order_id):
    """Handle Telebirr payment initiation"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if order.paid:
            messages.warning(request, 'This order has already been paid.')
            return redirect('mainapp:order_detail', order_id=order.id)
        
        # Initialize payment service
        payment_service = TelebirrPaymentService()
        
        # Create payment request
        result = payment_service.create_payment(
            order=order,
            amount=float(order.get_total_cost()),
            subject=f"Order #{order.id}",
            body=f"Payment for order #{order.id} - {order.get_items_description()}"
        )
        
        if result['success']:
            # Redirect to payment URL
            return redirect(result['payment_url'])
        else:
            messages.error(request, f'Payment initiation failed: {result["error"]}')
            return redirect('mainapp:order_detail', order_id=order.id)
            
    except ValueError as e:
        messages.error(request, f'Payment configuration error: {str(e)}')
        return redirect('mainapp:order_detail', order_id=order.id)
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('mainapp:order_detail', order_id=order.id)

@login_required
@require_POST
def rate_product(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        rating = int(request.POST.get('rating', 0))
        review = request.POST.get('review', '').strip()
        
        if not 1 <= rating <= 5:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid rating value'
            }, status=400)
        
        # Check if user has already rated this product
        existing_rating = ProductReview.objects.filter(
            product=product,
            user=request.user
        ).first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating
            existing_rating.content = review
            existing_rating.save()
        else:
            # Create new rating
            ProductReview.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                title=f"Review by {request.user.email}",
                content=review,
                verified_purchase=OrderItem.objects.filter(
                    order__user=request.user,
                    product=product,
                    order__status='delivered'
                ).exists()
            )
        
        # Calculate new average rating
        avg_rating = product.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        review_count = product.reviews.count()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Rating submitted successfully',
            'avg_rating': round(avg_rating, 1),
            'review_count': review_count
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_POST
def newsletter_subscribe(request):
    try:
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({
                'status': 'error',
                'message': 'Email is required.'
            }, status=400)
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'status': 'error',
                'message': 'Please enter a valid email address.'
            }, status=400)
        
        # Check if email already exists
        if Newsletter.objects.filter(email=email).exists():
            return JsonResponse({
                'status': 'info',
                'message': 'You are already subscribed to our newsletter!'
            })
        
        # Create new subscription
        Newsletter.objects.create(email=email)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for subscribing to our newsletter!'
        })
        
    except Exception as e:
        logger.error(f"Newsletter subscription error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred. Please try again later.'
        }, status=500)

@login_required
def cart_clear(request):
    if request.method == 'POST':
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Cart cleared successfully',
                'cart_count': 0,
                'cart_total': '0.00'
            })
        except Cart.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Cart not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error clearing cart: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while clearing the cart'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

def search_products(request):
    """
    View function for searching products.
    Handles search queries, category filtering, price range filtering, and sorting.
    """
    # Get search parameters from request
    search_query = request.GET.get('q', '')
    category_slug = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with all available products
    products = Product.objects.filter(available=True)
    
    # Apply search query filter if provided
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply category filter if provided
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Apply price range filters if provided
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            pass
    
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # Default to name
        products = products.order_by('name')
    
    # Paginate results
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page', 1)
    products = paginator.get_page(page_number)
    
    # Get all categories for filter sidebar
    categories = Category.objects.all()
    
    # Prepare context
    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'current_category': category_slug,
        'current_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
    }
    
    return render(request, 'mainapp/product_list.html', context)

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user has already reviewed this product
    existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('mainapp:product_detail', slug=product.slug)
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST)
        image_form = ReviewImageForm(request.POST, request.FILES)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            
            # Handle review images
            if image_form.is_valid() and request.FILES.getlist('images'):
                for image in request.FILES.getlist('images'):
                    ReviewImage.objects.create(review=review, image=image)
            
            messages.success(request, 'Your review has been added successfully.')
            return redirect('mainapp:product_detail', slug=product.slug)
    else:
        form = ProductReviewForm()
        image_form = ReviewImageForm()
    
    context = {
        'form': form,
        'image_form': image_form,
        'product': product,
    }
    return render(request, 'mainapp/add_review.html', context)

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ProductReviewForm(request.POST, instance=review)
        image_form = ReviewImageForm(request.POST, request.FILES)
        
        if form.is_valid():
            form.save()
            
            # Handle review images
            if image_form.is_valid() and request.FILES.getlist('images'):
                for image in request.FILES.getlist('images'):
                    ReviewImage.objects.create(review=review, image=image)
            
            messages.success(request, 'Your review has been updated successfully.')
            return redirect('mainapp:product_detail', slug=review.product.slug)
    else:
        form = ProductReviewForm(instance=review)
        image_form = ReviewImageForm()
    
    context = {
        'form': form,
        'image_form': image_form,
        'review': review,
        'product': review.product,
    }
    return render(request, 'mainapp/edit_review.html', context)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    product_slug = review.product.slug
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Your review has been deleted successfully.')
        return redirect('mainapp:product_detail', slug=product_slug)
    
    context = {
        'review': review,
        'product': review.product,
    }
    return render(request, 'mainapp/delete_review.html', context)

@login_required
def mark_review_helpful(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id)
    
    if request.method == 'POST':
        # Toggle helpful status
        if request.user in review.helpful_votes.all():
            review.helpful_votes.remove(request.user)
            message = 'Review marked as not helpful.'
        else:
            review.helpful_votes.add(request.user)
            message = 'Review marked as helpful.'
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': message,
                'helpful_count': review.helpful_votes.count(),
                'is_helpful': request.user in review.helpful_votes.all()
            })
        
        messages.success(request, message)
        return redirect('mainapp:product_detail', slug=review.product.slug)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def about(request):
    """View function for the about page."""
    return render(request, 'mainapp/about.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save the message to the database
        # For now, we'll just show a success message
        messages.success(request, 'Thank you for your message. We will get back to you soon!')
        return redirect('contact')
    
    return render(request, 'mainapp/contact.html')

@login_required
def profile(request):
    """View function for the user profile page."""
    if request.method == 'POST':
        # Update user information
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.save()
        
        # Update profile information if it exists
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.phone = request.POST.get('phone', '')
            profile.address = request.POST.get('address', '')
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
            
            profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('mainapp:profile')
    
    # Get user's recent orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    return render(request, 'mainapp/profile.html', {
        'orders': orders
    })

@login_required
def user_dashboard(request):
    # Get recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get order statistics
    total_orders = Order.objects.filter(user=request.user).count()
    pending_orders = Order.objects.filter(user=request.user, status='pending').count()
    completed_orders = Order.objects.filter(user=request.user, status='delivered').count()
    
    # Get recent reviews
    recent_reviews = ProductReview.objects.filter(user=request.user).order_by('-created_at')[:3]
    
    return render(request, 'mainapp/user_dashboard.html', {
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'recent_reviews': recent_reviews
    })

@login_required
def user_products(request):
    """View function for managing user's products."""
    products = UserProduct.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'mainapp/user_products.html', {'products': products})

@login_required
def create_product(request):
    """View function for creating a new product."""
    if request.method == 'POST':
        form = UserProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, 'Product created successfully!')
            return redirect('mainapp:user_products')
    else:
        form = UserProductForm()
    
    return render(request, 'mainapp/create_product.html', {'form': form})

@login_required
def edit_product(request, product_id):
    """View function for editing an existing product."""
    product = get_object_or_404(UserProduct, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        form = UserProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('mainapp:user_products')
    else:
        form = UserProductForm(instance=product)
    
    return render(request, 'mainapp/edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    """View function for deleting a product."""
    product = get_object_or_404(UserProduct, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('mainapp:user_products')
    
    return render(request, 'mainapp/delete_product.html', {'product': product})

@login_required
def conversations(request):
    """View function for listing user's conversations."""
    conversations = Conversation.objects.filter(
        Q(seller=request.user) | Q(buyer=request.user)
    ).order_by('-last_message_at')
    
    # Get unread message counts for each conversation
    for conversation in conversations:
        conversation.unread_count = Message.objects.filter(
            conversation=conversation,
            recipient=request.user,
            is_read=False
        ).count()
    
    return render(request, 'mainapp/conversations.html', {'conversations': conversations})

@login_required
def conversation_detail(request, conversation_id):
    """View function for viewing a conversation."""
    conversation = get_object_or_404(
        Conversation,
        Q(seller=request.user) | Q(buyer=request.user),
        id=conversation_id
    )
    
    # Mark messages as read
    Message.objects.filter(
        conversation=conversation,
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    messages = Message.objects.filter(conversation=conversation).order_by('created_at')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                recipient=conversation.seller if request.user == conversation.buyer else conversation.buyer,
                content=content
            )
            conversation.last_message_at = timezone.now()
            conversation.save()
            return redirect('mainapp:conversation_detail', conversation_id=conversation.id)
    
    return render(request, 'mainapp/conversation_detail.html', {
        'conversation': conversation,
        'messages': messages
    })

@login_required
def start_conversation(request, product_id):
    """View function for starting a new conversation."""
    product = get_object_or_404(UserProduct, id=product_id)
    
    # Check if conversation already exists
    conversation = Conversation.objects.filter(
        product=product,
        buyer=request.user
    ).first()
    
    if conversation:
        return redirect('mainapp:conversation_detail', conversation_id=conversation.id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            conversation = Conversation.objects.create(
                product=product,
                seller=product.seller,
                buyer=request.user
            )
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                recipient=product.seller,
                content=content
            )
            return redirect('mainapp:conversation_detail', conversation_id=conversation.id)
    
    return render(request, 'mainapp/start_conversation.html', {'product': product})

@login_required
def get_unread_message_count(request):
    """View function for getting the count of unread messages."""
    count = Message.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')  # Replace 'home' with your desired redirect URL
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def initiate_payment(request, order_id):
    """Initiate payment for an order"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if order is already paid
        if order.paid:
            messages.warning(request, 'This order has already been paid.')
            return redirect('order_detail', order_id=order.id)
        
        # Initialize payment service
        payment_service = TelebirrPaymentService()
        
        # Create payment request
        result = payment_service.create_payment(
            order=order,
            amount=order.get_total_cost(),
            subject=f"Order #{order.id}",
            body=f"Payment for order #{order.id}"
        )
        
        if result['success']:
            # Redirect to payment URL
            return redirect(result['payment_url'])
        else:
            messages.error(request, f"Payment initiation failed: {result['error']}")
            return redirect('order_detail', order_id=order.id)
            
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('order_list')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('order_list')

@csrf_exempt
def payment_notify(request):
    """Handle payment notification from Telebirr"""
    try:
        # Get the notification data
        data = json.loads(request.body)
        transaction_id = data.get('outTradeNo')
        
        if not transaction_id:
            return JsonResponse({'status': 'error', 'message': 'Missing transaction ID'})
        
        # Initialize payment service
        payment_service = TelebirrPaymentService()
        
        # Verify the payment
        result = payment_service.verify_payment(transaction_id)
        
        if result['success']:
            # Update order status if payment is completed
            if result['status'] == 'completed':
                payment = TelebirrPayment.objects.get(transaction_id=transaction_id)
                order = payment.order
                order.paid = True
                order.status = 'processing'
                order.save()
            
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': result['error']})
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Payment notification error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def payment_return(request):
    """Handle payment return from Telebirr"""
    try:
        transaction_id = request.GET.get('outTradeNo')
        
        if not transaction_id:
            messages.error(request, 'Missing transaction ID')
            return redirect('mainapp:order_list')
        
        # Initialize payment service
        payment_service = TelebirrPaymentService()
        
        # Verify the payment
        result = payment_service.verify_payment(transaction_id)
        
        if result['success']:
            payment = TelebirrPayment.objects.get(transaction_id=transaction_id)
            
            if payment.status == 'completed':
                messages.success(request, 'Payment completed successfully!')
            elif payment.status == 'failed':
                messages.error(request, 'Payment failed. Please try again.')
            elif payment.status == 'cancelled':
                messages.warning(request, 'Payment was cancelled.')
            else:
                messages.info(request, 'Payment is being processed.')
            
            return redirect('mainapp:order_detail', order_id=payment.order.id)
        else:
            messages.error(request, f'Payment verification failed: {result["error"]}')
            return redirect('mainapp:order_list')
        
    except TelebirrPayment.DoesNotExist:
        messages.error(request, 'Payment not found')
        return redirect('mainapp:order_list')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('mainapp:order_list')

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    # Sales Summary
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    sales_today = Order.objects.filter(
        created_at__date=today,
        paid=True
    ).aggregate(total=Sum('items__price'))['total'] or Decimal('0.00')
    
    sales_week = Order.objects.filter(
        created_at__date__gte=week_ago,
        paid=True
    ).aggregate(total=Sum('items__price'))['total'] or Decimal('0.00')
    
    sales_month = Order.objects.filter(
        created_at__date__gte=month_ago,
        paid=True
    ).aggregate(total=Sum('items__price'))['total'] or Decimal('0.00')
    
    # Order Status Overview
    order_statuses = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    total_orders = sum(status['count'] for status in order_statuses)
    for status in order_statuses:
        status['percentage'] = round((status['count'] / total_orders) * 100) if total_orders > 0 else 0
    
    # Recent Orders
    recent_orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')[:10]
    
    # Top Selling Products
    top_products = Product.objects.annotate(
        sold_count=Count('orderitem__order', filter=Q(orderitem__order__paid=True)),
        revenue=Sum('orderitem__price', filter=Q(orderitem__order__paid=True))
    ).order_by('-sold_count')[:5]
    
    # Add revenue growth calculation
    for product in top_products:
        previous_month = Order.objects.filter(
            items__product=product,
            created_at__date__gte=month_ago - timedelta(days=30),
            created_at__date__lt=month_ago,
            paid=True
        ).aggregate(revenue=Sum('items__price'))['revenue'] or Decimal('0.00')
        
        current_month = Order.objects.filter(
            items__product=product,
            created_at__date__gte=month_ago,
            paid=True
        ).aggregate(revenue=Sum('items__price'))['revenue'] or Decimal('0.00')
        
        if previous_month > 0:
            product.revenue_growth = round(((current_month - previous_month) / previous_month) * 100)
        else:
            product.revenue_growth = 0
    
    # Low Stock Alerts
    low_stock_products = Product.objects.filter(stock__lte=10).order_by('stock')[:5]
    
    context = {
        'sales_today': sales_today,
        'sales_week': sales_week,
        'sales_month': sales_month,
        'order_statuses': order_statuses,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
    }
    
    return render(request, 'mainapp/admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def user_list(request):
    """View function for listing all users in the admin dashboard."""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'mainapp/admin/users.html', {'users': users}) 