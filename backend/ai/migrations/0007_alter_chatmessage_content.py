# Generated for ChatMessage.content: CharField(max_length=2048) -> TextField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0006_rename_image_drawing_alter_drawing_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatmessage",
            name="content",
            field=models.TextField(db_comment="消息内容", verbose_name="消息内容"),
        ),
    ]
