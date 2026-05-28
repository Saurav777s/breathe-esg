# core/management/commands/seed_demo.py
from django.core.management.base import BaseCommand
from core.models import Tenant, User

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tenant, _ = Tenant.objects.get_or_create(name='Demo Corp', slug='demo')
        if not User.objects.filter(username='analyst').exists():
            u = User.objects.create_superuser('analyst', 'analyst@demo.com', 'breathe2024')
            u.tenant = tenant
            u.role = 'analyst'
            u.save()
            self.stdout.write('Demo user created: analyst / breathe2024')