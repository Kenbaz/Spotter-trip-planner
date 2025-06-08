import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import SpotterCompany

User = get_user_model()

class Command(BaseCommand):
    help = 'Create initial Spotter super admin and setup company information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the super admin'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the super admin',
            default='kbassey016@gmail.com'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password for the super admin',
        )
        parser.add_argument(
            '--first_name',
            type=str,
            help='First name for the super admin',
            default='System'
        )
        parser.add_argument(
            '--last_name',
            type=str,
            help='Last name for the super admin',
            default='Administrator'
        )
        parser.add_argument(
            '--usdot',
            type=str,
            help='Spotter USDOT number',
        )
        parser.add_argument(
            '--mc_number',
            type=str,
            help='Spotter MC number',
        )
        parser.add_argument(
            '--company_address',
            type=str,
            help='Spotter company address',
        )
        parser.add_argument(
            '--company_city',
            type=str,
            help='Spotter company city',
        )
        parser.add_argument(
            '--company_state',
            type=str,
            help='Spotter company state',
            default='TX'
        )
        parser.add_argument(
            '--company_zip',
            type=str,
            help='Spotter company zip code',
        )
        parser.add_argument(
            '--company_phone',
            type=str,
            help='Spotter company phone number',
        )
        parser.add_argument(
            '--company_email',
            type=str,
            help='Spotter company email',
            default='contact@spotter.com'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip creating the super admin if it already exists'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # Check if the super admin already exists
        if User.objects.filter(is_super_admin=True).exists():
            if options['skip_existing']:
                self.stdout.write(self.style.SUCCESS('Super admin already exists. Skipping creation.'))
                return
            else:
                raise CommandError('Super admin already exists. Use --skip-existing to skip creation.')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')
        
         # Get password if not provided
        if not password:
            password = os.environ.get('SPOTTER_ADMIN_PASSWORD')
            if not password:
                from getpass import getpass
                password = getpass('Enter password for super admin: ')
                confirm_password = getpass('Confirm password: ')
                if password != confirm_password:
                    raise CommandError('Passwords do not match.')
        
        if len(password) < 8:
            raise CommandError('Password must be at least 8 characters long.')
        
        try:
            with transaction.atomic():
                # Creating super admin user
                super_admin = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=options['first_name'],
                    last_name=options['last_name'],
                    is_staff=True,
                    is_superuser=True,
                    is_super_admin=True,
                    is_fleet_manager=True,
                    is_driver=False,
                    is_active_driver=False
                )

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully created super admin: {username}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Employee ID: {super_admin.employee_id}")
                )

                # Create Spotter company information
                company = SpotterCompany.get_company_instance()

                # Update company info if provided
                updated = False
                if options['usdot']:
                    company.usdot_number = options['usdot']
                    updated = True
                
                if options['mc_number']:
                    company.mc_number = options['mc_number']
                    updated = True
                
                if options['company_address']:
                    company.address = options['company_address']
                    updated = True
                
                if options['company_city']:
                    company.city = options['company_city']
                    updated = True
                
                if options['company_state']:
                    company.state = options['company_state']
                    updated = True
                
                if options['company_zip']:
                    company.zip_code = options['company_zip']
                    updated = True
                
                if options['company_phone']:
                    company.phone_number = options['company_phone']
                    updated = True
                
                if options['company_email']:
                    company.email = options['company_email']
                    updated = True
                
                if updated:
                    company.save()
                    self.stdout.write(
                        self.style.SUCCESS('Successfully updated Spotter company information')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Spotter company created with default values. Update manually in admin.')
                    )
                
                # Display setup information
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('SPOTTER HOS SYSTEM SETUP COMPLETE'))
                self.stdout.write('='*50)
                self.stdout.write(f'Super Admin Username: {username}')
                self.stdout.write(f'Super Admin Email: {email}')
                self.stdout.write(f'Super Admin Employee ID: {super_admin.employee_id}')
                self.stdout.write(f'Company: {company.name}')
                self.stdout.write(f'USDOT: {company.usdot_number}')
                self.stdout.write(f'MC Number: {company.mc_number}')
                self.stdout.write('='*50)
                self.stdout.write(
                    self.style.WARNING(
                        'IMPORTANT: Please update company information in the admin panel '
                        'if default values were used.'
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        'Login at /admin/ to complete the setup and create fleet managers.'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error creating super admin: {str(e)}')