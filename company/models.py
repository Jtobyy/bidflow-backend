# companies/models.py (or add to users/models.py)
from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    rc_number = models.CharField("CAC/RC Number", max_length=100, blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
