from djoser import email


class ActivationEmail(email.ActivationEmail):
    template_name = "accounts/email/activation.html"


class ConfirmationEmail(email.ConfirmationEmail):
    template_name = "accounts/email/confirmation.html"


class PasswordResetEmail(email.PasswordResetEmail):
    template_name = "accounts/email/password_reset.html"


class PasswordChangedConfirmationEmail(email.PasswordChangedConfirmationEmail):
    template_name = "accounts/email/password_changed_confirmation.html"
