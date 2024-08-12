from django import forms
from django.contrib import admin
from tinymce.widgets import TinyMCE

from kinesinlms.news.models import NewsPost


class NewsPostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    class Meta:
        model = NewsPost
        fields = '__all__'


class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_status', 'published_on', 'slug',)
    form = NewsPostAdminForm

    def post_status(self, obj):
        if obj.status == 0:
            return "Draft"
        else:
            return "Published"

    post_status.short_description = "Post Status"


admin.site.register(NewsPost, NewsPostAdmin)
