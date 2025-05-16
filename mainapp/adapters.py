from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        This is called when saving user via allauth registration.
        We override this to set the email as the username.
        """
        user = super().save_user(request, user, form, commit=False)
        user.username = None
        if commit:
            user.save()
        return user 