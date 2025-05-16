from .models import Cart
from decimal import Decimal

def cart(request):
    """
    Context processor to make cart information available in all templates.
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()
        cart_total = cart.get_total()
    else:
        # Handle anonymous users
        session_cart = request.session.get('cart', {})
        cart_count = sum(int(item['quantity']) for item in session_cart.values())
        cart_total = Decimal('0')
        for product_id, item_data in session_cart.items():
            try:
                from .models import Product
                product = Product.objects.get(id=product_id)
                cart_total += product.price * Decimal(item_data['quantity'])
            except Product.DoesNotExist:
                continue
    
    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
    } 