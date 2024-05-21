from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.core.serializers import serialize
import json

class Country(models.Model):
    name = models.CharField(max_length=300)
    image = models.ImageField(upload_to="country_images/")

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
    min_delivery_time = models.PositiveIntegerField(null=True, help_text="Minimum estimated delivery time in business days")
    max_delivery_time = models.PositiveIntegerField(null=True, help_text="Maximum estimated delivery time in business days")

    def __str__(self):
        return f'{self.business.business_name, self.name}'

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



class Service(models.Model):
    name = models.CharField(max_length=100)
    service_slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')

    def __str__(self):
        return f'{self.business.business_name}, {self.name}'

    def save(self, *args, **kwargs):
        if not self.service_slug:
            self.service_slug = slugify(self.name)
        super().save(*args, **kwargs)
    

class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"
    

class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
    


class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='messages', null=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"
    


class Event(models.Model):
    organizer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organized_events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    country = models.ForeignKey('Country', on_delete=models.CASCADE, related_name='events')
    state = models.ForeignKey('State', on_delete=models.CASCADE, related_name='events')
    start_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    banner_image = models.ImageField(upload_to='event_banners/', blank=True, null=True)

    def __str__(self):
        return self.title
