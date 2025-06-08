# users/management/commands/setup_admin_permissions.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from users.models import SpotterCompany, Vehicle, DriverVehicleAssignment

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup admin permissions and groups for fleet managers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing groups and permissions',
        )

    def handle(self, *args, **options):
        reset = options['reset']
        
        self.stdout.write(
            self.style.SUCCESS('Setting up admin permissions for fleet managers...')
        )
        
        try:
            with transaction.atomic():
                # Create or get Fleet Manager group
                fleet_manager_group, created = Group.objects.get_or_create(
                    name='Fleet Managers'
                )
                
                if reset and not created:
                    fleet_manager_group.permissions.clear()
                    self.stdout.write('Cleared existing Fleet Manager permissions')
                
                # Get content types for our models
                user_ct = ContentType.objects.get_for_model(User)
                vehicle_ct = ContentType.objects.get_for_model(Vehicle)
                assignment_ct = ContentType.objects.get_for_model(DriverVehicleAssignment)
                company_ct = ContentType.objects.get_for_model(SpotterCompany)
                
                # Define permissions fleet managers should have
                permissions_to_add = [
                    # User model permissions (for managing drivers)
                    ('view_user', user_ct),
                    ('add_user', user_ct),
                    ('change_user', user_ct),
                    # Note: Not giving delete_user permission for safety
                    
                    # Vehicle model permissions
                    ('view_vehicle', vehicle_ct),
                    ('add_vehicle', vehicle_ct),
                    ('change_vehicle', vehicle_ct),
                    ('delete_vehicle', vehicle_ct),
                    
                    # Driver-Vehicle Assignment permissions
                    ('view_drivervehicleassignment', assignment_ct),
                    ('add_drivervehicleassignment', assignment_ct),
                    ('change_drivervehicleassignment', assignment_ct),
                    ('delete_drivervehicleassignment', assignment_ct),
                    
                    # Company info permissions (view only)
                    ('view_spottercompany', company_ct),
                ]
                
                added_permissions = []
                for perm_codename, content_type in permissions_to_add:
                    try:
                        permission = Permission.objects.get(
                            codename=perm_codename,
                            content_type=content_type
                        )
                        fleet_manager_group.permissions.add(permission)
                        added_permissions.append(f"{content_type.model}.{perm_codename}")
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Permission {perm_codename} not found for {content_type.model}')
                        )
                
                self.stdout.write(
                    f'Added {len(added_permissions)} permissions to Fleet Managers group'
                )
                
                # Assign all fleet managers to this group
                fleet_managers = User.objects.filter(is_fleet_manager=True)
                assigned_count = 0
                
                for user in fleet_managers:
                    if not user.groups.filter(name='Fleet Managers').exists():
                        user.groups.add(fleet_manager_group)
                        assigned_count += 1
                        self.stdout.write(
                            f'✓ Added {user.full_name} ({user.username}) to Fleet Managers group'
                        )
                
                # Summary
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('ADMIN PERMISSIONS SETUP COMPLETE'))
                self.stdout.write('='*60)
                self.stdout.write(f'Fleet Managers group: {"Created" if created else "Updated"}')
                self.stdout.write(f'Permissions added: {len(added_permissions)}')
                self.stdout.write(f'Fleet managers assigned to group: {assigned_count}')
                self.stdout.write(f'Total fleet managers: {fleet_managers.count()}')
                
                self.stdout.write('\nFleet managers can now:')
                self.stdout.write('✓ View and create driver accounts')
                self.stdout.write('✓ Manage vehicle fleet')
                self.stdout.write('✓ Assign drivers to vehicles')
                self.stdout.write('✓ View company information')
                self.stdout.write('✗ Delete user accounts (for safety)')
                self.stdout.write('✗ Modify super admin settings')
                
                # List permissions for reference
                if options.get('verbosity', 1) >= 2:
                    self.stdout.write('\nDetailed permissions granted:')
                    for perm in added_permissions:
                        self.stdout.write(f'  - {perm}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up permissions: {str(e)}')
            )
            raise