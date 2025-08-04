from django.contrib.auth.models import AbstractUser
from django.db import models
from company.models import Company


class User(AbstractUser):
    ROLE_CHOICES = (
        ('procurer', 'Procurer'),
        ('client', 'Client'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='procurer')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_procurer(self):
        return self.role == 'procurer'

    def is_client(self):
        return self.role == 'client'
