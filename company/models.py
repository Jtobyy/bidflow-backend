from django.db import models

class Company(models.Model):
    COMPANY_TYPE_CHOICES = (
        ('procurer', 'Procurer'),
        ('vendor', 'Vendor'),
    )

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=COMPANY_TYPE_CHOICES, default='vendor')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    rc_number = models.CharField("CAC/RC Number", max_length=100, blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def is_vendor(self):
        return self.type == 'vendor'

    def is_procurer(self):
        return self.type == 'procurer'
