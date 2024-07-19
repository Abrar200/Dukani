from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.serializers import serialize
import json
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    name = models.CharField(max_length=300)
    image = models.ImageField(upload_to="country_images/")
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class State(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=3)

    def __str__(self):
        return self.name

class Business(models.Model):
    BUSINESS_TYPE_CHOICES = [
        ('product', 'Product Business'),
        ('service', 'Service Business'),
    ]
    seller = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='business')
    business_name = models.CharField(max_length=100)
    description = models.TextField()
    business_slug = models.SlugField(unique=True, blank=True)
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES)
    countries = models.ManyToManyField(Country)
    states = models.ManyToManyField(State)
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    website = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='business_profiles/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='business_banners/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)  # Add this line

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        if not self.business_slug:
            self.business_slug = slugify(self.business_name)
        super().save(*args, **kwargs)


class OpeningHour(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('public_holiday', 'Public Holiday'),
    ]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='opening_hours')
    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    is_closed = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        if self.is_closed:
            return f"{self.business.business_name} - {self.get_day_display()} (Closed)"
        else:
            return f"{self.business.business_name} - {self.get_day_display()} ({self.opening_time} - {self.closing_time})"
    



class Product(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = 'EL', _('Electronics')
        CLOTHING = 'CL', _('Clothing, Shoes & Jewelry')
        BOOKS = 'BK', _('Books')
        HOME = 'HM', _('Home & Kitchen')
        BEAUTY = 'BE', _('Beauty & Personal Care')
        TOYS = 'TY', _('Toys & Games')
        SPORTS = 'SP', _('Sports & Outdoors')
        AUTOMOTIVE = 'AU', _('Automotive')
        HEALTH = 'HE', _('Health & Household')
        GROCERY = 'GR', _('Grocery & Gourmet Food')
        PET_SUPPLIES = 'PT', _('Pet Supplies')
        OFFICE = 'OF', _('Office Products')
        TOOLS = 'TL', _('Tools & Home Improvement')
        MOVIES = 'MV', _('Movies & TV')
        GARDEN = 'GD', _('Garden & Outdoor')
        HANDMADE = 'HN', _('Handmade')
        BABY = 'BA', _('Baby')
        INDUSTRIAL = 'IN', _('Industrial & Scientific')
        ARTS = 'AR', _('Arts, Crafts & Sewing')
        MUSIC = 'MU', _('Musical Instruments')
        OTHER = 'OT', _('Other')

    category = models.CharField(
        max_length=2,
        choices=Category.choices,
        default=Category.OTHER,
    )
    name = models.CharField(max_length=100)
    product_slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    image2 = models.ImageField(upload_to='products/', null=True, blank=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='products')
    in_stock = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    trending = models.BooleanField(default=False)
    new_releases = models.BooleanField(default=False)
    min_delivery_time = models.PositiveIntegerField(null=True, help_text="Minimum estimated delivery time in business days")
    max_delivery_time = models.PositiveIntegerField(null=True, help_text="Maximum estimated delivery time in business days")
    has_variations = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.business.business_name}, {self.name}'

    def get_json_data(self):
        data = {
            'id': self.id,
            'name': self.name,
            'price': float(self.price),
            'description': self.description,
            'images': [self.image.url, self.image2.url] if self.image and self.image2 else [],
            'min_delivery_time': self.min_delivery_time,
            'max_delivery_time': self.max_delivery_time,
        }
        return json.dumps(data)

    def save(self, *args, **kwargs):
        if not self.product_slug:
            self.product_slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def overall_review(self):
        avg_rating = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg_rating, 1) if avg_rating else 0

    def star_rating_percentage(self, star):
        total_reviews = self.reviews.count()
        if total_reviews == 0:
            return 0
        star_count = self.reviews.filter(rating=star).count()
        return round((star_count / total_reviews) * 100)


VAR_CATEGORIES = (
    ('size', 'Size'),
    ('color', 'Color'),
)

class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=50, choices=VAR_CATEGORIES, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.get_name_display()}"

class ProductVariation(models.Model):
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE, related_name='values', null=True)
    value = models.CharField(max_length=50, null=True)
    image = models.ImageField(upload_to='product_variations/', null=True, blank=True)

    class Meta:
        unique_together = (('variation', 'value'),)

    def __str__(self):
        return f"{self.variation.product.name} - {self.variation.get_name_display()} - {self.value}"
    

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    review_text = models.TextField()
    rating = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.user.username} on {self.product.name}'

    @property
    def date(self):
        return (timezone.now() - self.created_at).days


class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    variation_key = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class CartItemVariation(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='variations')
    product_variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.cart} - {self.product_variation}"


class Service(models.Model):
    name = models.CharField(max_length=100)
    service_slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='services/', null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')

    def __str__(self):
        return f'{self.business.business_name}, {self.name}'

    def save(self, *args, **kwargs):
        if not self.service_slug:
            self.service_slug = slugify(self.name)
        super().save(*args, **kwargs)



class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('ordered', 'ordered'),
        ('shipped', 'shipped'),
        ('delivered', 'delivered'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    ref_code = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=100, null=True)
    postal_code = models.CharField(max_length=20, null=True)
    note = models.TextField(null=True, blank=True)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="ordered")
    
    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    variations = JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} ({', '.join([f'{k}: {v}' for k, v in self.variations.items()]) if self.variations else ''})"
    

class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    email = models.EmailField()
    accepted = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.pk}"


class Message(models.Model):
    sender = models.ForeignKey(CustomUser, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(CustomUser, related_name='received_messages', on_delete=models.CASCADE)
    business = models.ForeignKey(Business, related_name='messages', on_delete=models.CASCADE, null=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f''

    @property
    def sender_is_business(self):
        return self.sender.business.exists()

    @property
    def recipient_is_business(self):
        return self.recipient.business.exists()

    


class Event(models.Model):
    organizer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organized_events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    country = models.ForeignKey('Country', on_delete=models.CASCADE, related_name='events')
    state = models.ForeignKey('State', on_delete=models.CASCADE, related_name='events')
    start_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    banner_image = models.ImageField(upload_to='event_banners/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title
