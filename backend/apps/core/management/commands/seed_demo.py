# core/management/commands/seed_demo.py
from django.core.management.base import BaseCommand
from apps.core.models import Tenant, User

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tenant, _ = Tenant.objects.get_or_create(name='Demo Corp', slug='demo')

        # Delete and recreate to ensure password is correct
        User.objects.filter(username='analyst').delete()

        u = User.objects.create_superuser(
            username='analyst',
            email='analyst@demo.com',
            password='breathe2024'
        )
        u.tenant = tenant
        u.role = 'analyst'
        u.save()
        self.stdout.write(self.style.SUCCESS('Demo user created: analyst / breathe2024'))