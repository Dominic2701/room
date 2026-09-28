from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("booking", "0002_alter_payment_payment_method")]

    operations = [
        migrations.AddField(
            model_name="room",
            name="total_rooms",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="room",
            name="available_rooms",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="booking",
            name="number_of_rooms",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="AdminVerificationCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("used", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="room",
            constraint=models.CheckConstraint(
                condition=models.Q(available_rooms__lte=models.F("total_rooms")),
                name="room_available_not_above_total",
            ),
        ),
    ]