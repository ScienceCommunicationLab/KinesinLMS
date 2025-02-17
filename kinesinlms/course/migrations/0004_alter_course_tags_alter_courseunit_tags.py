# Generated by Django 5.0.9 on 2024-11-28 01:44

import taggit.managers
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("course", "0003_course_tags"),
        ("taggit", "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="tags",
            field=taggit.managers.TaggableManager(
                blank=True,
                help_text="Tags for this course",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AlterField(
            model_name="courseunit",
            name="tags",
            field=taggit.managers.TaggableManager(
                blank=True,
                help_text="Tags for this course unit",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
    ]
