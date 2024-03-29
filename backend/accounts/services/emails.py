from django.conf import settings
from django.core.mail import EmailMessage


class SendEmail:
    def __init__(self, name: str):
        self.name=name
        self.source='backend.email'

    def apply(self, to: str, data, due_date=None):
        if data is None:
            data = {}

        if self.name == "ACCOUNT_ACTIVATION":
            subject = render_to_string(
                "accounts/emails/account_activation_subject.txt", 
                data
            ).rstrip('\n')
            body = render_to_string(
                "accounts/emails/account_activation_body.html", 
                data 
            )
            email = EmailMessage(subject, body, settings.EMAIL_HOST_USER, [to])
            email.send(fail_silently=True)
        elif self.name == "PASSWORD_RESET":
            subject = render_to_string(
                "accounts/emails/password_reset_subject.txt", 
                data
            ).rstrip('\n')
            body = render_to_string(
                "accounts/emails/password_reset_body.html", 
                data 
            )
            email = EmailMessage(subject, body, settings.EMAIL_HOST_USER, [to])
            email.send(fail_silently=True)


class BaseEmail:
    serializer_class = None

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return None
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {}


class Email(BaseEmail):
    name = None

    def __init__(self, to, data=None):
        self.to = to
        self.data = data
        if data is None:
            self.data = {}

    def send(self, due_date=None):
        send_data = None

        serializer = self.get_serializer(data=self.data)
        if serializer:
            serializer.is_valid(raise_exception=True)
            send_data = serializer.data

        email_task = SendEmail(self.name)
        email_task.apply(to=self.to, data=send_data, due_date=due_date)
