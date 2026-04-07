import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairq.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin():
    username = 'admin'
    password = 'admin'
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, 'admin@example.com', password)
        print("Admin user created.")
    else:
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print("Admin user password updated.")

if __name__ == "__main__":
    create_admin()
