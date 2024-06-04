from django.shortcuts import render
from .models import Country, Product, Business, Service, OpeningHour, Cart, Message, State, Event, Variation, ProductVariation, VAR_CATEGORIES, CartItemVariation
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
import logging
import json
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import itertools
from users.models import CustomUser
from django.contrib import messages
from django.urls import reverse


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
    businesses = Business.objects.all().select_related('seller')

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

    if request.is_ajax():
        business_data = [
            {
                'business_name': business.business_name,
                'description': business.description,
                'business_slug': business.business_slug,
                'banner_image': business.banner_image.url if business.banner_image else None,
                'seller_name': business.seller.get_full_name(),
                # Add more fields as needed
            }
            for business in businesses
        ]
        return JsonResponse({'businesses': business_data})

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
    

@login_required
def edit_business(request, business_slug):
    business = get_object_or_404(Business, business_slug=business_slug)

    # Check if the user is the seller of the business
    if request.user != business.seller:
        return redirect('business_detail', business_slug=business.business_slug)

    countries = Country.objects.all()
    states = State.objects.all()

    if request.method == 'POST':
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
        state_ids = request.POST.getlist('states')

        if business_name and description and business_type and address and phone:
            business.business_name = business_name
            business.description = description
            business.business_type = business_type
            business.address = address
            business.phone = phone
            business.website = website
            business.email = email
            if profile_picture:
                business.profile_picture = profile_picture
            if banner_image:
                business.banner_image = banner_image

            if country_id != 'default':
                country = Country.objects.get(id=country_id)
                business.countries.set([country])

            states = State.objects.filter(id__in=state_ids)
            business.states.set(states)

            business.save()

            # Update or create OpeningHour instances
            for day, day_display in OpeningHour.DAY_CHOICES:
                is_closed_str = request.POST.get(f'opening_hours-{day}-is_closed', 'off')
                is_closed = is_closed_str == 'on'
                opening_time = request.POST.get(f'opening_hours-{day}-opening_time')
                closing_time = request.POST.get(f'opening_hours-{day}-closing_time')

                opening_hour, created = OpeningHour.objects.get_or_create(
                    business=business,
                    day=day,
                    defaults={
                        'is_closed': is_closed,
                        'opening_time': opening_time if not is_closed else None,
                        'closing_time': closing_time if not is_closed else None,
                    }
                )

                if not created:
                    opening_hour.is_closed = is_closed
                    opening_hour.opening_time = opening_time if not is_closed else None
                    opening_hour.closing_time = closing_time if not is_closed else None
                    opening_hour.save()

            return redirect('business_detail', business_slug=business.business_slug)

    context = {
        'business': business,
        'countries': countries,
        'states': states,
        'day_choices': OpeningHour.DAY_CHOICES,
    }
    return render(request, 'business/edit_business.html', context)


class BusinessDetailView(View):
    def get(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        products = business.products.all()
        services = business.services.all()
        opening_hours = business.opening_hours.all()
        return render(request, 'business/business_detail.html', {'business': business, 'products': products, 'opening_hours': opening_hours, 'services': services})

class ProductDetailView(View):
    def get(self, request, business_slug=None, product_slug=None):
        if request.is_ajax():
            return self.ajax_get(request, business_slug, product_slug)
        
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        
        color_variations = Variation.objects.filter(product=product, name='color')
        size_variations = Variation.objects.filter(product=product, name='size')

        context = {
            'product': product,
            'business': business,
            'color_variations': color_variations,
            'size_variations': size_variations,
        }

        return render(request, 'business/product_detail.html', context)


class AjaxProductDetailView(View):
    def get(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)

        color_variations = Variation.objects.filter(product=product, name='color')
        size_variations = Variation.objects.filter(product=product, name='size')
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'description': product.description,
            'images': [product.image.url, product.image2.url] if product.image and product.image2 else [],
            'color_variations': list(color_variations.values('id', 'values__id', 'values__value', 'values__image')),
            'size_variations': list(size_variations.values('id', 'values__id', 'values__value')),
            'sku': product.product_slug,
            'categories': [product.business.business_name],
            'tags': [tag.name for tag in product.tags.all()] if hasattr(product, 'tags') else []
        }
        return JsonResponse(product_data)
    


class ProductCreateView(LoginRequiredMixin, View):
    def get(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        return render(request, 'business/product_create.html', {'business': business, 'VAR_CATEGORIES': VAR_CATEGORIES})

    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        if business.seller == request.user:
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = request.POST.get('price')
            min_delivery_time = request.POST.get('min_delivery_time')
            max_delivery_time = request.POST.get('max_delivery_time')
            image = request.FILES.get('image')
            image2 = request.FILES.get('image2')
            in_stock = request.POST.get('in_stock') == 'on'
            has_variations = request.POST.get('has_variations') == 'on'

            product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                image=image,
                image2=image2,
                min_delivery_time=min_delivery_time,
                max_delivery_time=max_delivery_time,
                business=business,
                in_stock=in_stock,
                has_variations=has_variations
            )

            if has_variations:
                variation_names = request.POST.getlist('variation_names')
                for variation_name in variation_names:
                    variation = Variation.objects.create(
                        product=product,
                        name=variation_name
                    )
                    variation_values = request.POST.getlist(f'variation_values_{variation_name}')
                    variation_images = request.FILES.getlist(f'variation_images_{variation_name}')
                    for i, value in enumerate(variation_values):
                        variation_image = variation_images[i] if i < len(variation_images) else None
                        ProductVariation.objects.create(
                            variation=variation,
                            value=value,
                            image=variation_image
                        )

            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)
        else:
            return render(request, 'business/product_create.html', {'business': business, 'error': 'You are not authorized to add products to this business.', 'VAR_CATEGORIES': VAR_CATEGORIES})


class ProductEditView(LoginRequiredMixin, View):
    def get(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        variations = product.variations.all()
        variation_names = variations.values_list('name', flat=True)
        
        variations_with_values = {}
        for variation in variations:
            # Fetch ProductVariation objects related to the current product and variation
            variation_values = ProductVariation.objects.filter(variation=variation, variation__product=product)
            variations_with_values[variation.name] = variation_values

        return render(request, 'business/product_edit.html', {
            'product': product,
            'business': business,
            'variations': variations,
            'variation_names': variation_names,
            'variations_with_values': variations_with_values,
            'VAR_CATEGORIES': VAR_CATEGORIES
        })

    def post(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)

        if request.user == business.seller:
            name = request.POST.get('name', product.name)
            description = request.POST.get('description', product.description)
            price = request.POST.get('price', product.price)
            min_delivery_time = request.POST.get('min_delivery_time', product.min_delivery_time)
            max_delivery_time = request.POST.get('max_delivery_time', product.max_delivery_time)
            image = request.FILES.get('image')
            image2 = request.FILES.get('image2')
            in_stock = request.POST.get('in_stock') == 'on'
            has_variations = request.POST.get('has_variations') == 'on'

            product.name = name
            product.description = description
            product.price = price
            product.min_delivery_time = min_delivery_time
            product.max_delivery_time = max_delivery_time
            if image:
                product.image = image
            if image2:
                product.image2 = image2
            product.in_stock = in_stock
            product.has_variations = has_variations
            product.save()

            if has_variations:
                existing_variations = {v.name: v for v in product.variations.all()}

                variation_names = request.POST.getlist('variation_names')
                for variation_name in variation_names:
                    if variation_name in existing_variations:
                        variation = existing_variations[variation_name]
                    else:
                        variation = Variation.objects.create(
                            product=product,
                            name=variation_name
                        )
                    
                    variation_values = request.POST.getlist(f'variation_values_{variation_name}')
                    variation_images = request.FILES.getlist(f'variation_images_{variation_name}')

                    existing_values = {pv.value: pv for pv in variation.values.all()}
                    
                    for i, value in enumerate(variation_values):
                        variation_image = variation_images[i] if i < len(variation_images) else None
                        if value in existing_values:
                            product_variation = existing_values[value]
                            if variation_image:
                                product_variation.image = variation_image
                            product_variation.save()
                        else:
                            ProductVariation.objects.create(
                                variation=variation,
                                value=value,
                                image=variation_image
                            )

                    for existing_value in existing_values.keys():
                        if existing_value not in variation_values:
                            existing_values[existing_value].delete()

                for existing_variation_name in existing_variations.keys():
                    if existing_variation_name not in variation_names:
                        existing_variations[existing_variation_name].delete()
            else:
                product.variations.all().delete()

            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)
        else:
            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)



class ServiceCreateView(LoginRequiredMixin, View):
    def get(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        return render(request, 'business/service_create.html', {'business': business})

    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        if business.seller == request.user:
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = request.POST.get('price')
            image = request.FILES.get('image')

            service = Service.objects.create(
                name=name,
                description=description,
                price=price,
                image=image,
                business=business
            )

            return redirect('service_detail', business_slug=business.business_slug, service_slug=service.service_slug)
        else:
            # Handle the case where the user is not the owner of the business
            return render(request, 'business/service_create.html', {'business': business, 'error': 'You are not authorized to add services to this business.'})


def service_detail(request, business_slug, service_slug):
    service = get_object_or_404(Service, service_slug=service_slug, business__business_slug=business_slug)
    context = {
        'service': service,
    }
    return render(request, 'business/service_detail.html', context)
    

class ServiceEditView(LoginRequiredMixin, View):
    def get(self, request, business_slug, service_slug):
        service = get_object_or_404(Service, service_slug=service_slug, business__business_slug=business_slug)
        business = service.business

        # Check if the user is the seller of the business
        if request.user != business.seller:
            return redirect('service_detail', business_slug=business.business_slug, service_slug=service.service_slug)

        return render(request, 'business/service_edit.html', {'service': service, 'business': business})

    def post(self, request, business_slug, service_slug):
        service = get_object_or_404(Service, service_slug=service_slug, business__business_slug=business_slug)
        business = service.business

        # Check if the user is the seller of the business
        if request.user == business.seller:
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = request.POST.get('price')
            image = request.FILES.get('image')

            service.name = name
            service.description = description
            service.price = price
            if image:
                service.image = image
            service.save()

            return redirect('service_detail', business_slug=business.business_slug, service_slug=service.service_slug)
        else:
            return redirect('service_detail', business_slug=business.business_slug, service_slug=service.service_slug)
    

class CartView(LoginRequiredMixin, View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, 'business/cart.html', {'cart_items': cart_items, 'total_price': total_price})

    def post(self, request):
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            selected_variations = data.get('selected_variations', [])
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in the request body")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

        logger.debug(f'Received product_id: {product_id} with variations: {selected_variations}')

        if not product_id:
            logger.error("No product_id provided in the request")
            return JsonResponse({'error': 'No product_id provided'}, status=400)

        product = get_object_or_404(Product, id=product_id)

        variation_categories = product.variations.count()

        if product.has_variations and len(selected_variations) != variation_categories:
            messages.error(request, f"Please select all {variation_categories} variations.")
            return JsonResponse({'error': f'Please select all {variation_categories} variations.'}, status=400)

        variation_key = "-".join(sorted(str(v_id) for v_id in selected_variations))

        cart_item = Cart.objects.filter(user=request.user, product=product, variation_key=variation_key).first()

        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                product=product,
                quantity=1,
                variation_key=variation_key
            )
            for variation_id in selected_variations:
                product_variation = get_object_or_404(ProductVariation, id=variation_id)
                CartItemVariation.objects.create(cart=cart_item, product_variation=product_variation)

        cart_item.save()

        cart_items = Cart.objects.filter(user=request.user)
        cart_data = []
        for item in cart_items:
            item_variations = [v.product_variation.value for v in item.variations.all()]
            cart_data.append({
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'image': item.product.image.url if item.product.image else None,
                },
                'variations': item_variations,
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
            item_variations = [v.product_variation.value for v in item.variations.all()]
            cart_data.append({
                'id': item.id,
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'image': str(item.product.image.url) if item.product.image else None,
                },
                'variations': item_variations,
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

        cart_item = get_object_or_404(Cart, id=item_id)

        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1

        cart_item.save()

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
                'variations': [v.product_variation.value for v in item.variations.all()],
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

        return super().dispatch(request, *args, **kwargs)





    

def checkout(request):
    return render(request, 'business/checkout.html')



@login_required
def message_seller(request, business_slug):
    business = get_object_or_404(Business, business_slug=business_slug)
    logger.debug(f"message_seller view: business_slug = {business_slug}, business = {business}")
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                recipient=business.seller,
                business=business,
                content=content
            )
            logger.debug(f"New message created: sender = {request.user}, recipient = {business.seller}, content = {content}")
            return redirect('message_seller', business_slug=business.business_slug)

    # Mark messages as read for the current user and business
    Message.objects.filter(recipient=request.user, business=business).update(is_read=True)
    logger.debug(f"Messages marked as read for recipient: {request.user}, business: {business}")

    messages = Message.objects.filter(
        Q(sender=request.user, recipient=business.seller) |
        Q(sender=business.seller, recipient=request.user)
    ).filter(business=business).order_by('timestamp')
    logger.debug(f"Fetched messages: {messages}")

    individual_business_message_counter = Message.objects.filter(recipient=request.user, business=business, is_read=False).count()
    context = {
        'business': business,
        'messages': messages,
        'individual_business_message_counter': individual_business_message_counter,
    }
    logger.debug(f"context: {context}")
    return render(request, 'business/message.html', context)



@login_required
def user_messages_view(request):
    businesses = Business.objects.filter(
        Q(messages__sender=request.user) | Q(messages__recipient=request.user)
    ).distinct()
    user_messages = []

    for business in businesses:
        if request.user == business.seller:
            # Query user_messages for business with other users
            messages = Message.objects.filter(
                Q(sender=business.seller) |
                Q(recipient=business.seller)
            ).filter(business=business).order_by('-timestamp')
            for user, chat in itertools.groupby(messages, lambda m: m.recipient if m.sender == request.user else m.sender):
                last_message = next(chat)
                user_messages.append({
                    'business': business,
                    'last_message': last_message,
                    'user': user,
                })
        else:
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
    logger.debug(f"Unread message counter: {unread_message_counter}")

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
            logger.debug(f"New message created: sender = {request.user}, recipient = {business.seller}, content = {content}")
        return redirect(f'{request.path}?business_slug={business.business_slug}')

    selected_business = None
    messages = []
    if 'business_slug' in request.GET:
        business_slug = request.GET.get('business_slug')
        selected_business = get_object_or_404(Business, business_slug=business_slug)
        if request.user == selected_business.seller and 'username' in request.GET:
            # Query messages for selected_business with selected_user
            username = request.GET.get('username')
            selected_user = get_object_or_404(CustomUser, username=username)
            messages = Message.objects.filter(
                Q(sender= selected_user, recipient=selected_business.seller) |
                Q(sender=selected_business.seller, recipient= selected_user)
            ).filter(business=selected_business).order_by('timestamp')
        else:
            messages = Message.objects.filter(
                Q(sender=request.user, recipient=selected_business.seller) |
                Q(sender=selected_business.seller, recipient=request.user)
            ).filter(business=selected_business).order_by('timestamp')

        Message.objects.filter(recipient=request.user, business=selected_business).update(is_read=True)

    context = {
        'user_messages': user_messages,
        'selected_business': selected_business,
        'messages': messages,
        'unread_message_counter': unread_message_counter,
    }
    logger.debug(f"context: {context}")
    return render(request, 'business/user_messages.html', context)





def events(request):
    events = Event.objects.all().select_related('organizer', 'country', 'state')
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

    if request.is_ajax():
        event_data = [
            {
                'id': event.id,  # Ensure ID is included
                'title': event.title,
                'description': event.description,
                'country': event.country.name,
                'state': event.state.name,
                'start_time': event.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'location': event.location,
                'banner_image': event.banner_image.url if event.banner_image else None,
                'organizer_name': event.organizer.get_full_name(),
            }
            for event in events
        ]
        return JsonResponse({'events': event_data})

    context = {
        'events': events,
        'countries': countries,
        'states': states,
        'selected_countries': country_filter,
        'selected_states': state_filter,
    }
    return render(request, 'business/events.html', context)


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
    countries = Country.objects.all()
    states = State.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        country_id = request.POST.get('country')
        state_id = request.POST.get('state')
        start_time = request.POST.get('start_time')
        location = request.POST.get('location')
        banner_image = request.FILES.get('banner_image')

        if title and description and country_id and state_id and start_time and location and banner_image:
            country = Country.objects.get(id=country_id)
            state = State.objects.get(id=state_id)

            event = Event.objects.create(
                organizer=request.user,
                title=title,
                description=description,
                country=country,
                state=state,
                start_time=start_time,
                location=location,
                banner_image=banner_image
            )
            return redirect('event_detail', event.id)

    return render(request, 'business/create_event.html', {'countries': countries, 'states': states})


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Check if the user is the organizer of the event
    if request.user != event.organizer:
        return redirect('event_detail', event_id=event.id)

    countries = Country.objects.all()
    states = State.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        country_id = request.POST.get('country')
        state_id = request.POST.get('state')
        start_time = request.POST.get('start_time')
        location = request.POST.get('location')
        banner_image = request.FILES.get('banner_image')

        if title and description and country_id and state_id and start_time and location:
            country = Country.objects.get(id=country_id)
            state = State.objects.get(id=state_id)

            event.title = title
            event.description = description
            event.country = country
            event.state = state
            event.start_time = start_time
            event.location = location
            if banner_image:
                event.banner_image = banner_image
            event.save()
            return redirect('event_detail', event_id=event.id)

    context = {
        'event': event,
        'countries': countries,
        'states': states,
    }
    return render(request, 'business/edit_event.html', context)


@login_required
def event_detail(request, event_id):
    events = Event.objects.all()
    event = get_object_or_404(Event, id=event_id)
    is_organizer = request.user == event.organizer
    return render(request, 'business/event_detail.html', {'event': event, 'events': events, 'is_organizer': is_organizer})


def products(request):
    products = Product.objects.all()
    return render(request, "business/products.html", {"products": products})


def services(request):
    services = Service.objects.all()
    return render(request, "business/services.html", {"services": services})


def search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(name__icontains=query)
    services = Service.objects.filter(name__icontains=query)
    businesses = Business.objects.filter(business_name__icontains=query)

    context = {
        'query': query,
        'products': products,
        'services': services,
        'businesses': businesses,
    }
    return render(request, 'business/search.html', context)

@login_required
def quick_shop_view(request, product_slug):
    # Get the product based on the slug
    product = get_object_or_404(Product, product_slug=product_slug)

    # Check if the product has variations
    if product.has_variations:
        # Redirect to the product detail page
        product_detail_url = reverse('product_detail', args=[product.business.business_slug, product.product_slug])
        messages.info(request, f"Please select your variations.")
        return redirect(product_detail_url)
    else:
        # Get the current user
        user = request.user

        # Create a new cart item
        cart_item, created = Cart.objects.get_or_create(
            user=user,
            product=product,
            defaults={'quantity': 1, 'variation_key': None}
        )

        # If the cart item already exists, increment the quantity
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        # Display a success message
        messages.success(request, f"{product.name} has been added to your cart.")

        # Redirect to the checkout page
        return redirect('checkout')
