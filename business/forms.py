from django import forms
from .models import ServiceReview

class ServiceReviewForm(forms.ModelForm):
    class Meta:
        model = ServiceReview
        fields = ['review_text', 'rating']
        widgets = {
            'review_text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your review...'}),
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
        }
