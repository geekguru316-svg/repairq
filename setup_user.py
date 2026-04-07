import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairq.settings')
django.setup()

from django.contrib.auth.models import User

def setup_demo_user():
    username = 'user1'
    password = 'user1'
    
    # Check if user exists
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True # Make it superuser so they can see everything in the demo
    user.save()
    
    if created:
        print(f"User '{username}' created successfully.")
    else:
        print(f"User '{username}' password updated.")

if __name__ == "__main__":
    setup_demo_user()
