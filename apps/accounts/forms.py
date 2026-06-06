from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import PatientMemory

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password  = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'date_of_birth']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # AbstractUser declares these blank=True, so the ModelForm makes them
        # optional. Force them required to match the API RegisterSerializer.
        for name in ('first_name', 'last_name', 'email'):
            self.fields[name].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        password  = cleaned.get('password')
        password2 = cleaned.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', 'Passwords do not match.')
        if password:
            try:
                validate_password(password)
            except forms.ValidationError as e:
                self.add_error('password', e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.username = email
        user.role = User.Role.PATIENT
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            PatientMemory.objects.get_or_create(patient=user)
        return user
