from django import forms
from django.contrib.auth.forms import get_user_model

user = get_user_model()

class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = user
        fields = ('email', 'first_name', 'last_name')

        def clean(self):
            cleaned_data = super().clean()
            if cleaned.get('password1') != cleaned.get('password2'):
                raise forms.ValidationError("Passwords do not match")
            return cleaned

        def save(self, commit=True):
         user = super().save(commit=False)
         user.set_password(self.cleaned_data['password1'])
         if commit:
          user.save()
         return user
            