from datetime import datetime
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import TextField

User = get_user_model()

STATUS = (
    (0, "Draft"),
    (1, "Publish")
)


class NewsPost(models.Model):
    title = models.CharField(max_length=250, unique=True)
    slug = models.SlugField(max_length=250, unique=True)
    featured_image = models.FileField(null=True, blank=True)
    author = models.ForeignKey(User,
                               null=True,
                               blank=True,
                               on_delete=models.CASCADE,
                               related_name='blog_posts')
    content = TextField()
    updated_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)
    published_on = models.DateTimeField(default=datetime.now, blank=True)
    status = models.IntegerField(choices=STATUS, default=0)
    featured_image_credit = models.CharField(max_length=200, blank=True, null=True)
    featured_image_alt = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['-published_on']

    def __str__(self):
        return self.title
