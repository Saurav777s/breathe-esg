
# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser


class Tenant(models.Model):
    """Multi-tenancy: one row per client company."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Extended user — belongs to a tenant, has a role."""
    ROLES = [
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('auditor', 'Auditor'),
    ]
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        null=True, blank=True, related_name='users'
    )
    role = models.CharField(max_length=20, choices=ROLES, default='analyst')


class AuditLog(models.Model):
    """Immutable log of every state change — required for audit trail."""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    diff = models.JSONField(default=dict)  # what changed
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']