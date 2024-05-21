from django.shortcuts import render
from .models import Country, Product, Business, Service, OpeningHour, Cart, Message, State, Event
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
import logging
import json
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.db.models import Q


logger = logging.getLogger(__name__)

def home(request):
    countries = Country.objects.all()
    products = Product.objects.all()
    context = {
        'countries': countries,
        'products': products,
    }
    return render(request, 'business/index.html', context)


def shop(request):
    return render(request, 'business/shop.html')

def community(request):
    businesses = Business.objects.all()
    countries = Country.objects.all()
    states = State.objects.all()

    country_filter = request.GET.getlist('country')
    state_filter = request.GET.getlist('state')

    if country_filter and state_filter:
        businesses = businesses.filter(
            countries__in=country_filter,
            states__in=state_filter
        ).distinct()
    elif country_filter:
        businesses = businesses.filter(countries__in=country_filter).distinct()
    elif state_filter:
        businesses = businesses.filter(states__in=state_filter).distinct()

    # Check if the request is coming from the index page
    if 'country_id' in request.GET:
        country_id = request.GET.get('country_id')
        country = get_object_or_404(Country, id=country_id)
        return redirect('community' + '?country=' + str(country.id))

    context = {
        'businesses': businesses,
        'countries': countries,
        'states': states,
        'selected_countries': country_filter,
        'selected_states': state_filter,
    }
    return render(request, 'business/community.html', context)


class BusinessRegistrationView(LoginRequiredMixin, View):
    def get(self, request):
        countries = Country.objects.all()
        day_choices = OpeningHour.DAY_CHOICES
        return render(request, 'users/business_registration.html', {'countries': countries, 'day_choices': day_choices})

    def post(self, request):
        business_name = request.POST.get('business_name')
        description = request.POST.get('description')
        business_type = request.POST.get('business_type')
        country_id = request.POST.get('country')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        website = request.POST.get('website')
        email = request.POST.get('email')
        profile_picture = request.FILES.get('profile_picture')
        banner_image = request.FILES.get('banner_image')

        country = Country.objects.get(id=country_id)
        user = request.user
        user.is_seller = True
        user.save()

        business = Business.objects.create(
            seller=request.user,
            business_name=business_name,
            description=description,
            business_type=business_type,
            country=country,
            address=address,
            phone=phone,
            website=website,
            email=email,
            profile_picture=profile_picture,
            banner_image=banner_image,   
        )

        for day, day_display in OpeningHour.DAY_CHOICES:
            is_closed = request.POST.get(f'opening_hours-{day}-is_closed', False)
            opening_time = request.POST.get(f'opening_hours-{day}-opening_time')
            closing_time = request.POST.get(f'opening_hours-{day}-closing_time')

            if is_closed:
                OpeningHour.objects.create(
                    business=business,
                    day=day,
                    is_closed=True
                )
            elif opening_time and closing_time:
                OpeningHour.objects.create(
                    business=business,
                    day=day,
                    opening_time=opening_time,
                    closing_time=closing_time
                )

        return redirect('business_detail', business_slug=business.business_slug)

class BusinessDetailView(View):
    def get(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        products = business.products.all()
        for product in products:
            print(f"Product: {product}")
            print(f"Product JSON data: {product.get_json_data()}")
        opening_hours = business.opening_hours.all()
        return render(request, 'business/business_detail.html', {'business': business, 'products': products, 'opening_hours': opening_hours})

class ProductCreateView(LoginRequiredMixin, View):
    def get(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        return render(request, 'business/product_create.html', {'business': business})

    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        if business.seller == request.user:
            name = request.POST.get('name')
            min_delivery_time = request.POST.get('min_delivery_time')
            max_delivery_time = request.POST.get('max_delivery_time')
            description = request.POST.get('description')
            price = request.POST.get('price')
            image = request.FILES.get('image')
            image2 = request.FILES.get('image2')

            product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                image=image,
                image2=image2,
                min_delivery_time=min_delivery_time,
                max_delivery_time=max_delivery_time,
                business=business
            )

            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)
        else:
            # Handle the case where the user is not the owner of the business
            return render(request, 'business/product_create.html', {'business': business, 'error': 'You are not authorized to add products to this business.'})

class ProductDetailView(View):
    def get(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        return render(request, 'business/product_detail.html', {'product': product, 'business': business})
    

class ProductEditView(LoginRequiredMixin, View):
    def get(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        opening_hours = business.opening_hours.all()
        return render(request, 'business/product_edit.html', {'product': product, 'business': business, 'opening_hours': opening_hours})

    def post(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)

        name = request.POST.get('name', product.name)
        min_delivery_time = request.POST.get('min_delivery_time', product.min_delivery_time)
        max_delivery_time = request.POST.get('max_delivery_time', product.max_delivery_time)
        description = request.POST.get('description', product.description)
        price = request.POST.get('price', product.price)
        image = request.FILES.get('image')
        image2 = request.FILES.get('image2')
        in_stock = 'in_stock' in request.POST

        product.name = name
        product.min_delivery_time = min_delivery_time
        product.max_delivery_time = max_delivery_time
        product.description = description
        product.price = price
        if image:
            product.image = image
        if image2:
            product.image2 = image2
        product.in_stock = in_stock
        product.save()

        return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)




class ServiceCreateView(LoginRequiredMixin, View):
    def get(self, request, service_slug):
        business = get_object_or_404(Business, service_slug=service_slug, seller=request.user)
        return render(request, 'business/service_create.html', {'business': business})

    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        name = request.POST.get('name')
        description = request.POST.get('description')

        service = Service.objects.create(
            name=name,
            description=description,
            business=business
        )

        return redirect('service_detail', business_slug=business.slug, service_slug=service.service_slug)

class ServiceDetailView(View):
    def get(self, request, business_slug, service_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        service = get_object_or_404(Service, service_slug=service_slug, business=business)
        return render(request, 'business/service_detail.html', {'service': service, 'business': business})
    

class CartView(LoginRequiredMixin, View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, 'business/cart.html', {'cart_items': cart_items, 'total_price': total_price})

    def post(self, request):
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in the request body")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

        logger.debug(f'Received product_id: {product_id}')

        if not product_id:
            logger.error("No product_id provided in the request")
            return JsonResponse({'error': 'No product_id provided'}, status=400)

        product = get_object_or_404(Product, id=product_id)
        cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
        if not created:
            cart_item.quantity += 1
        cart_item.save()

        cart_items = Cart.objects.filter(user=request.user)
        cart_data = []
        for item in cart_items:
            cart_data.append({
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'image': item.product.image.url if item.product.image else None,
                },
                'quantity': item.quantity,
            })
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        logger.debug("Returning updated cart data as JSON response")
        return JsonResponse({'success': True, 'items': cart_data, 'subtotal': total_price})

    def get_cart_data(self, request):
        logger.debug("Received request to fetch cart data")
        cart_items = Cart.objects.filter(user=request.user)
        cart_data = []
        for item in cart_items:
            cart_data.append({
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'image': str(item.product.image.url) if item.product.image else None,
                },
                'quantity': item.quantity,
            })
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        logger.debug(f"Returning cart data: {cart_data}")
        return JsonResponse({'items': cart_data, 'subtotal': total_price})
    
    def update_quantity(self, request):
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            action = data.get('action')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

        # Retrieve the cart item
        cart_item = get_object_or_404(Cart, id=item_id)

        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1

        cart_item.save()

        # Calculate total price and prepare cart data
        cart_items = Cart.objects.filter(user=request.user)
        cart_data = [
            {
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'image': item.product.image.url if item.product.image else None,
                },
                'quantity': item.quantity,
            }
            for item in cart_items
        ]
        total_price = sum(item.product.price * item.quantity for item in cart_items)

        return JsonResponse({'success': True, 'items': cart_data, 'subtotal': total_price})
    
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            if request.path == '/cart/update_quantity/':
                return self.update_quantity(request, *args, **kwargs)
            else:
                # Handle other POST requests here
                pass
        elif request.method == 'GET':
            if request.path == '/cart/data/':
                logger.debug(f"Request Path: {request.path}")
                return self.get_cart_data(request)
            else:
                # Handle other GET requests here
                pass

        # Fall back to the default behavior if the request doesn't match any of the above conditions
        return super().dispatch(request, *args, **kwargs)
    

def checkout(request):
    return render(request, 'business/checkout.html')


@login_required
def message_seller(request, business_slug):
    business = get_object_or_404(Business, business_slug=business_slug)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                recipient=business.seller,
                business=business,
                content=content
            )
            return redirect('message_seller', business_slug=business.business_slug)

    # Mark messages as read for the current user and business
    Message.objects.filter(recipient=request.user, business=business).update(is_read=True)

    messages = Message.objects.filter(
        Q(sender=request.user, recipient=business.seller) |
        Q(sender=business.seller, recipient=request.user)
    ).filter(business=business).order_by('timestamp')

    individual_business_message_counter = Message.objects.filter(recipient=request.user, business=business, is_read=False).count()
    context = {
        'business': business,
        'messages': messages,
        'individual_business_message_counter': individual_business_message_counter,
    }
    return render(request, 'business/message.html', context)


@login_required
def user_messages_view(request):
    businesses = Business.objects.filter(
        Q(messages__sender=request.user) | Q(messages__recipient=request.user)
    ).distinct()
    user_messages = []

    for business in businesses:
        last_message = Message.objects.filter(
            Q(sender=request.user, recipient=business.seller) |
            Q(sender=business.seller, recipient=request.user)
        ).filter(business=business).order_by('-timestamp').first()
        unread_businesses = set()
        if Message.objects.filter(recipient=request.user, business=business, is_read=False).exists():
            unread_businesses.add(business)
        user_messages.append({
            'business': business,
            'last_message': last_message,
            'unread_count': len(unread_businesses),
        })

    unread_message_counter = len(unread_businesses)

    if request.method == 'POST':
        business_slug = request.POST.get('business_slug')
        business = get_object_or_404(Business, business_slug=business_slug)
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                recipient=business.seller,
                business=business,
                content=content
            )

    selected_business = None
    messages = []
    if 'business_slug' in request.GET:
        business_slug = request.GET.get('business_slug')
        selected_business = get_object_or_404(Business, business_slug=business_slug)
        messages = Message.objects.filter(
            Q(sender=request.user, recipient=selected_business.seller) |
            Q(sender=selected_business.seller, recipient=request.user)
        ).filter(business=selected_business).order_by('timestamp')

    context = {
        'user_messages': user_messages,
        'selected_business': selected_business,
        'messages': messages,
        'unread_message_counter': unread_message_counter,
    }
    return render(request, 'business/user_messages.html', context)



def events(request):
    events = Event.objects.all()
    countries = Country.objects.all()
    states = State.objects.all()

    country_filter = request.GET.getlist('country')
    state_filter = request.GET.getlist('state')

    if country_filter and state_filter:
        events = events.filter(
            Q(country__in=country_filter) &
            Q(state__in=state_filter)
        )
    elif country_filter:
        events = events.filter(country__in=country_filter)
    elif state_filter:
        events = events.filter(state__in=state_filter)

    context = {
        'events': events,
        'countries': countries,
        'states': states,
        'selected_countries': country_filter,
        'selected_states': state_filter,
    }
    return render(request, 'business/events.html', context)


@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect('event_detail', event.id)
    else:
        form = EventForm()
    return render(request, 'business/create_event.html', {'form': form})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'business/event_detail.html', {'event': event})