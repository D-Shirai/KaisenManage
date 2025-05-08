from django.db import migrations
from django.conf import settings

def create_superuser(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    if not User.objects.filter(username='<your-username>').exists():
        User.objects.create_superuser(
            username='1620996',
            email='danasuku@gmail.com',
            password='0sakagas'
        )

class Migration(migrations.Migration):

    dependencies = [
        # 0007までのマイグレーションがすべて終わったあとに実行
        ('core', '0007_project_deleted_at_project_is_deleted'),
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]
