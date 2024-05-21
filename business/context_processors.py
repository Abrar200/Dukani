from collections import defaultdict
from .models import Cart

def cart_data(request):
    if request.user.is_authenticated:
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        # Create a dictionary to store individual item prices
        item_prices = defaultdict(float)

        for item in cart_items:
            item_price = item.product.price * item.quantity
            item_prices[item.id] = item_price

    else:
        cart_items = []
        total_price = 0
        item_prices = {}

    return {
        'cart_items': cart_items,
        'total_price': total_price,
        'item_prices': item_prices,
    }
