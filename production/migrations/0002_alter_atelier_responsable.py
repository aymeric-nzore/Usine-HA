import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_responsables(apps, schema_editor):
    Atelier = apps.get_model("production", "Atelier")
    User = apps.get_model("auth", "User")
    users = {
        f"{user.first_name} {user.last_name}".strip(): user
        for user in User.objects.all()
    }
    for atelier in Atelier.objects.all():
        responsable = users.get(str(atelier.responsable).strip())
        if responsable:
            atelier.responsable_new_id = responsable.pk
            atelier.save(update_fields=["responsable_new"])


class Migration(migrations.Migration):
    dependencies = [
        ("production", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="atelier",
            name="responsable_new",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ateliers_responsables_new",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(migrate_responsables, migrations.RunPython.noop),
        migrations.RemoveField(model_name="atelier", name="responsable"),
        migrations.RenameField(
            model_name="atelier",
            old_name="responsable_new",
            new_name="responsable",
        ),
        migrations.AlterField(
            model_name="atelier",
            name="responsable",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ateliers_responsables",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
