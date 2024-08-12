from typing import Any, Dict

from django.views import generic

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.news.models import NewsPost


class NewsPostList(generic.ListView):
    template_name = 'news/news_post_list.html'

    def get_queryset(self):
        if self.request.user and self.request.user.is_superuser:
            queryset = NewsPost.objects.order_by('-published_on')
        else:
            queryset = NewsPost.objects.filter(status=1).order_by('-published_on')
        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super(NewsPostList, self).get_context_data(**kwargs)
        extra_context = {
            "section": "news",
            "breadcrumbs": [
            ],
            "title": "News",
            "description": f"News posts by the KinesinLMS team",
        }
        context = {**context, **extra_context}
        return context


class NewsPostDetail(generic.DetailView):
    model = NewsPost
    template_name = 'news/news_post_detail.html'

    def get_context_data(self, **kwargs):
        context = super(NewsPostDetail, self).get_context_data(**kwargs)
        news_post: NewsPost = self.get_object()

        catalog_descriptions = CourseCatalogDescription.objects.filter(course__slug__in=["LE", "PYSJ", "SYR"])

        extra_context = {
            "section": "news",
            "catalog_descriptions": catalog_descriptions,
            "breadcrumbs": [
                {
                    "url": "/news",
                    "label": "News"
                }
            ],
            "title": "Post",
            "description": f"\"{news_post.title}\"",
        }
        context = {**context, **extra_context}
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_staff and not user.is_superuser:
            # Only show published stories...
            queryset = queryset.filter(status=1)
        return queryset

