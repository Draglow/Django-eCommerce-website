from django import forms
from django_countries.fields import CountryField
from .models import Order, ProductReview, ReviewImage, UserProduct, Message

class CheckoutForm(forms.ModelForm):
    country = CountryField().formfield()
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    
    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'postal_code', 'city', 'country',
            'payment_method'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter your full address'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your postal code'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your city'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to payment method radio buttons
        self.fields['payment_method'].widget.attrs.update({'class': 'form-check-input'})
        # Make all fields required
        for field in self.fields.values():
            field.required = True

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'content']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Give your review a title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Share your experience with this product'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].label = 'Your Rating'
        self.fields['title'].label = 'Review Title'
        self.fields['content'].label = 'Review Content'

class ReviewImageForm(forms.ModelForm):
    images = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        required=False,
        label='Add Photos (Optional)'
    )

    class Meta:
        model = ReviewImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False

class UserProductForm(forms.ModelForm):
    class Meta:
        model = UserProduct
        fields = ['name', 'description', 'price', 'image', 'category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Type your message here...',
                'class': 'form-control'
            })
        }
