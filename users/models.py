from django.contrib.auth.models import AbstractUser
from django.db import models
from company.models import Company


class User(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False, blank=False, related_name='users')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
