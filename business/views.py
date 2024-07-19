from django.shortcuts import render
from .models import Country, Product, Business, Service, OpeningHour, Cart, Message, State, Event, Variation, ProductVariation, VAR_CATEGORIES, CartItemVariation, ProductReview, Order, OrderItem, Refund
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
from django.http import HttpResponseRedirect
from itertools import chain
from django.template import RequestContext
from django.template.context_processors import csrf
import stripe
from django.conf import settings
from collections import defaultdict
import string
import random
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from decimal import Decimal
from django.core.paginator import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Subquery, OuterRef
from django.views.decorators.http import require_POST


stripe.api_key = settings.STRIPE_SECRET_KEY

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

def privacy_policy(request):
    return render(request, 'business/privacy_policy.html')


def return_and_refund_policy(request):
    return render(request, 'business/return_and_refund_policy.html')


def terms_and_conditions(request):
    return render(request, 'business/terms_and_conditions.html')


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

    paginator = Paginator(businesses, 5)  # Show 10 businesses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.is_ajax():
        business_data = [
            {
                'business_name': business.business_name,
                'description': business.description,
                'business_slug': business.business_slug,
                'profile_picture': business.profile_picture.url,
                'seller_name': business.seller.get_full_name(),
                # Add more fields as needed
            }
            for business in page_obj
        ]
        return JsonResponse({'businesses': business_data})

    context = {
        'businesses': page_obj,
        'countries': countries,
        'states': states,
        'selected_countries': country_filter,
        'selected_states': state_filter,
    }
    return render(request, 'business/community.html', context)



class BusinessRegistrationView(LoginRequiredMixin, View):
    def get(self, request):
        countries = Country.objects.all()
        states = State.objects.all()
        day_choices = OpeningHour.DAY_CHOICES
        return render(request, 'users/business_registration.html', {
            'countries': countries,
            'states': states,
            'day_choices': day_choices
        })

    def post(self, request):
        try:
            business_name = request.POST.get('business_name')
            description = request.POST.get('description')
            business_type = request.POST.get('business_type')
            country_ids = request.POST.getlist('countries[]')
            state_ids = request.POST.getlist('states[]')
            address = request.POST.get('address')
            phone = request.POST.get('phone')
            website = request.POST.get('website')
            email = request.POST.get('email')
            profile_picture = request.FILES.get('profile_picture')
            banner_image = request.FILES.get('banner_image')

            user = request.user
            user.is_seller = True
            user.save()

            business = Business.objects.create(
                seller=user,
                business_name=business_name,
                description=description,
                business_type=business_type,
                address=address,
                phone=phone,
                website=website,
                email=email,
                profile_picture=profile_picture,
                banner_image=banner_image,
            )

            business.countries.set(country_ids)
            business.states.set(state_ids)
            business.save()

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

            # Create Stripe account
            try:
                account = stripe.Account.create(
                    type='express',
                    country='AU',  # You can set this dynamically based on the business's country
                    email=email,
                    business_type='individual',
                )
                business.stripe_account_id = account.id
                business.save()

                account_link = stripe.AccountLink.create(
                    account=account.id,
                    refresh_url=request.build_absolute_uri(reverse('business_registration')),
                    return_url=request.build_absolute_uri(reverse('business_detail', args=[business.business_slug])),
                    type='account_onboarding',
                )

                return redirect(account_link.url)
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {e.user_message}")
                messages.error(request, f"Stripe error: {e.user_message}")
                business.delete()  # Clean up the partially created business
                return redirect('business_registration')

        except Exception as e:
            logger.error(f"Error during business registration: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
            if 'business' in locals():
                business.delete()  # Clean up the partially created business
            return redirect('business_registration')

    

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
        country_ids = request.POST.getlist('countries')
        state_ids = request.POST.getlist('states')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        website = request.POST.get('website')
        email = request.POST.get('email')
        profile_picture = request.FILES.get('profile_picture')
        banner_image = request.FILES.get('banner_image')

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

            countries = Country.objects.filter(id__in=country_ids)
            business.countries.set(countries)

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
    

@method_decorator(login_required, name='dispatch')
class BusinessDeleteView(View):
    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug)

        if request.user != business.seller:
            messages.error(request, "You do not have permission to delete this business.")
            return redirect('business_detail', business_slug=business_slug)
        
        # Delete the business
        business.delete()
        
        # Set the user as not a seller
        request.user.is_seller = False
        request.user.save()
        
        messages.success(request, "Business has been successfully deleted.")
        return redirect('home')  # Redirect to the home page or any other page after deletion
    


class BusinessOrdersView(LoginRequiredMixin, View):
    def get(self, request, business_slug):
        business = Business.objects.get(business_slug=business_slug)
        if request.user != business.seller:
            return JsonResponse({'error': 'Unauthorized access'}, status=403)

        # Fetch orders related to this business
        orders = Order.objects.filter(items__product__business=business).distinct().order_by('-created_at')
        order_data = []
        for order in orders:
            items = order.items.filter(product__business=business)
            order_data.append({
                'order': order,
                'items': items
            })

        return render(request, 'business/business_orders.html', {'business': business, 'orders': order_data})

    def post(self, request, business_slug):
        business = Business.objects.get(business_slug=business_slug)
        if request.user != business.seller:
            return JsonResponse({'error': 'Unauthorized access'}, status=403)

        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        order = Order.objects.get(id=order_id)

        # Update the order status
        order.order_status = new_status
        order.save()

        # Send email to the user based on the new status
        self.send_status_update_email(order, business, new_status)

        # Add a success message
        messages.success(request, f'Order status updated to {new_status} and email sent to the customer.')

        return redirect('business_orders', business_slug=business_slug)

    def send_status_update_email(self, order, business, status):
        user = order.user
        item_details = [
            f"{item.quantity} x {item.product.name} ({', '.join([f'{k}: {v}' for k, v in item.variations.items()]) if item.variations else ''})"
            for item in order.items.filter(product__business=business)
        ]

        if status == 'shipped':
            email_subject = f"Your order {order.ref_code} has been shipped"
            email_template = 'business/order_shipped_email.html'
        elif status == 'delivered':
            email_subject = f"Your order {order.ref_code} has been delivered"
            email_template = 'business/order_delivered_email.html'
        else:
            return

        email_body = render_to_string(email_template, {
            'user': user,
            'business': business,
            'order': order,
            'item_details': item_details
        })

        email = EmailMultiAlternatives(
            subject=email_subject,
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(email_body, "text/html")
        email.send(fail_silently=False)


class ProductDetailView(View):
    def get(self, request, business_slug=None, product_slug=None):
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        
        color_variations = Variation.objects.filter(product=product, name='color')
        size_variations = Variation.objects.filter(product=product, name='size')
        reviews = product.reviews.all()

        star_percentages = {
            5: product.star_rating_percentage(5),
            4: product.star_rating_percentage(4),
            3: product.star_rating_percentage(3),
            2: product.star_rating_percentage(2),
            1: product.star_rating_percentage(1),
        }

        context = {
            'product': product,
            'business': business,
            'color_variations': color_variations,
            'size_variations': size_variations,
            'reviews': reviews,
            'star_percentages': star_percentages,
            'overall_review': product.overall_review
        }

        return render(request, 'business/product_detail.html', context)

    @method_decorator(login_required)
    def post(self, request, business_slug=None, product_slug=None):
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)

        review_text = request.POST.get('message')
        rating = request.POST.get('rating')

        if review_text and rating:
            rating = int(rating)
            ProductReview.objects.create(
                product=product,
                user=request.user,
                review_text=review_text,
                rating=rating
            )
            return redirect('product_detail', business_slug=business_slug, product_slug=product_slug)
        
        color_variations = Variation.objects.filter(product=product, name='color')
        size_variations = Variation.objects.filter(product=product, name='size')
        reviews = product.reviews.all()

        star_percentages = {
            5: product.star_rating_percentage(5),
            4: product.star_rating_percentage(4),
            3: product.star_rating_percentage(3),
            2: product.star_rating_percentage(2),
            1: product.star_rating_percentage(1),
        }

        context = {
            'product': product,
            'business': business,
            'color_variations': color_variations,
            'size_variations': size_variations,
            'reviews': reviews,
            'star_percentages': star_percentages,
        }

        return render(request, 'business/product_detail.html', context)

    

@method_decorator(login_required, name='dispatch')
class ProductDeleteView(View):
    def post(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)

        if request.user != business.seller:
            messages.error(request, "You do not have permission to delete this product.")
            return redirect('product_detail', business_slug=business_slug, product_slug=product_slug)
        
        product.delete()
        messages.success(request, "Product has been successfully deleted.")
        return redirect('business_detail', business_slug=business_slug)


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
        return render(request, 'business/product_create.html', {
            'business': business, 
            'VAR_CATEGORIES': VAR_CATEGORIES,
            'Product': Product  # Add this line to pass the Product model to the template
        })

    def post(self, request, business_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        if business.seller == request.user:
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = request.POST.get('price')
            category = request.POST.get('category')  # Get the category from the form
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
                category=category,  # Add the category to the product
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
            return render(request, 'business/product_create.html', {
                'business': business, 
                'error': 'You are not authorized to add products to this business.', 
                'VAR_CATEGORIES': VAR_CATEGORIES,
                'Product': Product  # Add this line here as well
            })




class ProductEditView(LoginRequiredMixin, View):
    def get(self, request, business_slug, product_slug):
        business = get_object_or_404(Business, business_slug=business_slug, seller=request.user)
        product = get_object_or_404(Product, product_slug=product_slug, business=business)
        variations = product.variations.all()
        variation_names = variations.values_list('name', flat=True)

        variations_with_values = {}
        for variation in variations:
            variation_values = ProductVariation.objects.filter(variation=variation, variation__product=product)
            variations_with_values[variation.name] = list(variation_values.values('id', 'value', 'image'))

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
                    variation_value_ids = request.POST.getlist(f'variation_value_ids_{variation_name}')

                    existing_values = {str(pv.id): pv for pv in variation.values.all()}

                    for i, value in enumerate(variation_values):
                        if value.strip() == "":
                            continue  # Skip empty values

                        variation_image = variation_images[i] if i < len(variation_images) else None
                        variation_value_id = variation_value_ids[i] if i < len(variation_value_ids) else None

                        if variation_value_id and variation_value_id in existing_values:
                            # Update existing ProductVariation
                            product_variation = existing_values[variation_value_id]
                            product_variation.value = value
                            if variation_image:
                                product_variation.image = variation_image
                            product_variation.save()
                        else:
                            # Create new ProductVariation, but first check if one with this value already exists
                            existing_pv = ProductVariation.objects.filter(variation=variation, value=value).first()
                            if existing_pv:
                                if variation_image:
                                    existing_pv.image = variation_image
                                existing_pv.save()
                            else:
                                ProductVariation.objects.create(
                                    variation=variation,
                                    value=value,
                                    image=variation_image
                                )

                    # Delete ProductVariations that are no longer in the form
                    for existing_value_id in existing_values.keys():
                        if existing_value_id not in variation_value_ids:
                            existing_values[existing_value_id].delete()

                # Delete Variations that are no longer in the form
                for existing_variation_name in existing_variations.keys():
                    if existing_variation_name not in variation_names:
                        existing_variations[existing_variation_name].delete()
            else:
                product.variations.all().delete()

            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)
        else:
            return redirect('product_detail', business_slug=business.business_slug, product_slug=product.product_slug)

    @login_required
    @require_POST
    def delete_variation(request, variation_id):
        try:
            variation = ProductVariation.objects.get(id=variation_id)
            if variation.variation.product.business.seller == request.user:
                variation.delete()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
        except ProductVariation.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Variation not found'}, status=404)


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
    business = service.business  # Get the business from the service
    opening_hours = business.opening_hours.all()  # Get the opening hours for the specific business
    context = {
        'service': service,
        'business': business,  # Pass the business to the template if needed
        'opening_hours': opening_hours,
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

    @method_decorator(login_required)
    def post(self, request):
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            selected_variations = data.get('selected_variations', [])
            quantity = data.get('quantity', 1)  # Get the quantity from the request
            logger.debug(f'Received product_id: {product_id} with variations: {selected_variations} with quantity {quantity}')
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in the request body")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

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
            cart_item.quantity += quantity
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                product=product,
                quantity=quantity,  # Set the quantity
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




from collections import defaultdict

class CreateCheckoutSessionView(LoginRequiredMixin, View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, 'business/checkout.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        })

    def post(self, request, *args, **kwargs):
        cart_items = Cart.objects.filter(user=request.user)
        YOUR_DOMAIN = "http://127.0.0.1:8000"

        line_items = []
        for item in cart_items:
            line_items.append({
                'price_data': {
                    'currency': 'aud',
                    'product_data': {
                        'name': item.product.name,
                    },
                    'unit_amount': int(float(item.product.price) * 100),
                },
                'quantity': item.quantity,
            })

        # Collect user address details from the request body
        request_data = json.loads(request.body)
        address = request_data.get('address', '')
        city = request_data.get('city', '')
        state = request_data.get('state', '')
        postal_code = request_data.get('postal_code', '')
        note = request_data.get('note', '')

        try:
            # Create a Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=YOUR_DOMAIN + '/success/',
                cancel_url=YOUR_DOMAIN + '/cancel/',
            )

            # Save the session ID and other relevant details to handle post-payment logic
            request.session['checkout_session_id'] = checkout_session.id
            request.session['business_items'] = {
                str(business.id): [
                    {
                        'amount': int(float(item.product.price) * 100 * item.quantity),
                        'business': business.stripe_account_id,
                        'product_id': item.product.id,
                        'quantity': item.quantity,
                        'variations': [
                            {
                                'variation_name': cv.product_variation.variation.name,
                                'variation_value': cv.product_variation.value
                            }
                            for cv in item.variations.all()
                        ]
                    }
                    for item in items
                ]
                for business, items in self.group_items_by_business(cart_items).items()
            }
            request.session['address'] = address
            request.session['city'] = city
            request.session['state'] = state
            request.session['postal_code'] = postal_code
            request.session['note'] = note
            request.session['cart_items'] = [
                {
                    'product_id': item.product.id,
                    'quantity': item.quantity,
                    'variations': [
                        {
                            'variation_name': cv.product_variation.variation.name,
                            'variation_value': cv.product_variation.value
                        }
                        for cv in item.variations.all()
                    ]
                }
                for item in cart_items
            ]

            return JsonResponse({'id': checkout_session.id})
        except Exception as e:
            return JsonResponse({'error': str(e)})

    def group_items_by_business(self, cart_items):
        business_items = defaultdict(list)
        for item in cart_items:
            business_items[item.product.business].append(item)
        return business_items

class PaymentSuccessView(LoginRequiredMixin, View):
    def get(self, request):
        checkout_session_id = request.session.get('checkout_session_id')
        business_items = request.session.get('business_items')
        cart_items = request.session.get('cart_items')
        address = request.session.get('address')
        city = request.session.get('city')
        state = request.session.get('state')
        postal_code = request.session.get('postal_code')
        note = request.session.get('note')

        if not checkout_session_id or not business_items or not cart_items:
            return JsonResponse({'error': 'Session data not found'}, status=400)

        try:
            # Retrieve the checkout session
            session = stripe.checkout.Session.retrieve(checkout_session_id)
            payment_intent_id = session.payment_intent

            # Create transfers for each business
            for business_id, items in business_items.items():
                total_amount = sum(item['amount'] for item in items)
                stripe.Transfer.create(
                    amount=int(total_amount * 0.85),  # 85% of the total amount
                    currency='aud',
                    destination=items[0]['business'],
                    transfer_group=payment_intent_id,
                )

            # Generate a unique reference code with strings and digits
            characters = string.ascii_letters + string.digits
            ref_code = ''.join(random.choice(characters) for _ in range(10))

            total_price = sum(item['quantity'] * Product.objects.get(id=item['product_id']).price for item in cart_items)
            order = Order.objects.create(
                user=request.user,
                ref_code=ref_code,
                total_amount=total_price,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                note=note
            )

            for item in cart_items:
                product = Product.objects.get(id=item['product_id'])
                variations = {
                    v['variation_name']: v['variation_value']
                    for v in item['variations']
                }
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=product.price,
                    variations=variations
                )

            # Clear the cart
            Cart.objects.filter(user=request.user).delete()

            # Send email to businesses
            self.send_order_emails(order, business_items)

            # Clear the session data
            del request.session['checkout_session_id']
            del request.session['business_items']
            del request.session['cart_items']
            del request.session['address']
            del request.session['city']
            del request.session['state']
            del request.session['postal_code']
            del request.session['note']

            return render(request, 'business/success.html')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def send_order_emails(self, order, business_items):
        for business_id, items in business_items.items():
            business = Business.objects.get(id=business_id)
            business_total = sum(item['amount'] for item in items) / 100  # Convert cents to dollars

            item_details = []
            for item in items:
                # Build the variations string for each item
                variations_str = ', '.join([f'{v["variation_name"]}: {v["variation_value"]}' for v in item["variations"]])
                item_detail = (
                    f"{item['quantity']} x {Product.objects.get(id=item['product_id']).name} "
                    f"({variations_str}) - "
                    f"${item['amount'] / 100}"  # Convert cents to dollars
                )
                item_details.append(item_detail)

            email_subject = f"New Order Received - {order.ref_code}"
            email_body = render_to_string('business/new_order.html', {
                'business': business,
                'order': order,
                'business_total': business_total,
                'item_details': item_details
            })

            # Send email using EmailMultiAlternatives to include the HTML message
            email = EmailMultiAlternatives(
                subject=email_subject,
                body=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[business.email],
            )
            email.attach_alternative(email_body, "text/html")
            email.send(fail_silently=False)


class UserOrdersView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'business/user_orders.html', {'orders': orders})
    


class RequestRefundView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'business/request_refund.html', {'order': order})

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if order.refund_requested:
            return redirect('user_orders')
        
        email = request.POST.get('email')
        reason = request.POST.get('reason')
        
        refund = Refund.objects.create(
            order=order,
            reason=reason,
            email=email
        )
        
        order.refund_requested = True
        order.save()

        # Get unique business emails associated with this order
        business_emails = OrderItem.objects.filter(order=order).select_related('product__business').values_list('product__business__email', flat=True).distinct()

        # Send email to each business
        for business_email in business_emails:
            # Get items for this specific business in this order
            business_items = OrderItem.objects.filter(
                order=order,
                product__business__email=business_email
            ).select_related('product')

            items_details = "\n".join([
                f"- {item.quantity} x {item.product.name} - ${item.price}"
                for item in business_items
            ])

            message = f"""
A refund has been requested for Order #{order.ref_code}.

Items from your business in this order:
{items_details}

Reason: {reason}

Customer Email: {email}
            """

            send_mail(
                f'Refund Request for Order #{order.ref_code}',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [business_email],
                fail_silently=False,
            )

        return redirect('user_orders')


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
def message_buyer(request, username):
    user = get_object_or_404(CustomUser, username=username)
    business = Business.objects.filter(seller=request.user).first()

    if not business:
        return redirect('user_messages')

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                recipient=user,
                business=business,
                content=content
            )
            return redirect('message_buyer', username=user.username)

    # Mark messages as read for the current user and buyer
    Message.objects.filter(recipient=request.user, sender=user).update(is_read=True)

    messages = Message.objects.filter(
        Q(sender=request.user, recipient=user) |
        Q(sender=user, recipient=request.user)
    ).filter(business=business).order_by('timestamp')

    context = {
        'user': user,
        'messages': messages,
    }
    return render(request, 'business/message_buyer.html', context)

@login_required
def user_messages_view(request):
    businesses = Business.objects.filter(
        Q(messages__sender=request.user) | Q(messages__recipient=request.user)
    ).distinct()

    user_messages = []
    latest_messages = []

    for business in businesses:
        if request.user == business.seller:
            # Query messages for business with other users
            messages = Message.objects.filter(
                Q(sender=business.seller) | Q(recipient=business.seller)
            ).filter(business=business).order_by('-timestamp')
            for user, chat in itertools.groupby(messages, lambda m: m.recipient if m.sender == request.user else m.sender):
                last_message = next(chat)
                unread_count = Message.objects.filter(recipient=business.seller, sender=user, business=business, is_read=False).count()
                user_messages.append({
                    'business': business,
                    'last_message': last_message,
                    'user': user,
                    'unread_count': unread_count,
                })
                latest_messages.append(last_message)
        else:
            last_message = Message.objects.filter(
                Q(sender=request.user, recipient=business.seller) |
                Q(sender=business.seller, recipient=request.user)
            ).filter(business=business).order_by('-timestamp').first()
            unread_count = Message.objects.filter(recipient=request.user, sender=business.seller, is_read=False).count()
            user_messages.append({
                'business': business,
                'last_message': last_message,
                'unread_count': unread_count,
            })
            latest_messages.append(last_message)

    # Sort user_messages by the latest message timestamp
    user_messages = sorted(user_messages, key=lambda um: um['last_message'].timestamp, reverse=True)
    
    unread_message_counter = sum(msg['unread_count'] for msg in user_messages)

    if request.method == 'POST':
        business_slug = request.POST.get('business_slug')
        business = get_object_or_404(Business, business_slug=business_slug)
        content = request.POST.get('content')
        if content:
            if request.user == business.seller:
                # Business sending message to user
                username = request.POST.get('username')
                if username:
                    recipient = get_object_or_404(CustomUser, username=username)
                    Message.objects.create(
                        sender=request.user,
                        recipient=recipient,
                        business=business,
                        content=content
                    )
                    return redirect(f'{request.path}?business_slug={business.business_slug}&username={recipient.username}')
            else:
                # User sending message to business
                Message.objects.create(
                    sender=request.user,
                    recipient=business.seller,
                    business=business,
                    content=content
                )
                return redirect(f'{request.path}?business_slug={business.business_slug}')

    selected_business = None
    selected_user = None
    messages = []
    if 'business_slug' in request.GET:
        business_slug = request.GET.get('business_slug')
        selected_business = get_object_or_404(Business, business_slug=business_slug)
        if request.user == selected_business.seller and 'username' in request.GET:
            # Query messages for selected_business with selected_user
            username = request.GET.get('username')
            if username:
                selected_user = get_object_or_404(CustomUser, username=username)
                messages = Message.objects.filter(
                    Q(sender=selected_user, recipient=selected_business.seller) |
                    Q(sender=selected_business.seller, recipient=selected_user)
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
        'selected_user': selected_user,
        'messages': messages,
        'unread_message_counter': unread_message_counter,
    }
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

    # Category filter
    category = request.GET.get('category')
    if category:
        products = products.filter(category=category)
    
    # Country and State filters
    selected_countries = request.GET.getlist('country')
    selected_states = request.GET.getlist('state')
    
    if selected_countries:
        products = products.filter(business__countries__id__in=selected_countries).distinct()
    if selected_states:
        products = products.filter(business__states__id__in=selected_states).distinct()
    
    # Sorting
    sort = request.GET.get('sort')
    if sort == 'price_high_low':
        products = products.order_by('-price')
    elif sort == 'price_low_high':
        products = products.order_by('price')
    elif sort == 'best_selling':
        products = products.filter(is_best_seller=True)
    elif sort == 'popular':
        products = products.filter(is_popular=True)
    elif sort == 'trending':
        products = products.filter(trending=True)
    elif sort == 'new_releases':
        products = products.filter(new_releases=True)
    
    # Pagination
    paginator = Paginator(products, 9)  # Show 9 products per page
    page = request.GET.get('page', 1)
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get all categories for the filter
    categories = Product.Category.choices
    
    # Get countries and states with their product counts
    countries = Country.objects.annotate(
        product_count=Count('business__products', distinct=True)
    )
    states = State.objects.annotate(
        product_count=Count('business__products', distinct=True)
    )
    
    context = {
        "products": products,
        "categories": categories,
        "countries": countries,
        "states": states,
        "selected_countries": selected_countries,
        "selected_states": selected_states,
    }
    
    return render(request, "business/products.html", context)



def services(request):
    services = Service.objects.all()
    
    # Get countries and states with their service counts
    countries = Country.objects.annotate(
        service_count=Count('business__services', distinct=True)
    )
    states = State.objects.annotate(
        service_count=Count('business__services', distinct=True)
    )

    # Filtering
    selected_countries = request.GET.getlist('country')
    selected_states = request.GET.getlist('state')

    if selected_countries:
        services = services.filter(business__countries__id__in=selected_countries)
    if selected_states:
        services = services.filter(business__states__id__in=selected_states)

    # Pagination
    paginator = Paginator(services, 10)  # Show 10 services per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "services": page_obj,
        "countries": countries,
        "states": states,
        "selected_countries": selected_countries,
        "selected_states": selected_states,
    }
    return render(request, "business/services.html", context)


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
    

@login_required
def delete_cart_item(request, cart_item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
        cart_item.delete()
        messages.success(request, "Item successfully removed from the cart.")
    return redirect('cart')  # Replace 'cart' with your cart URL name
