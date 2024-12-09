from typing import Optional

from django.db import models

from kinesinlms.course.models import Course
from kinesinlms.learning_library.models import Block


class Speaker(models.Model):
    class Meta:
        ordering = ["last_name"]

    courses = models.ManyToManyField(Course, related_name="speakers", blank=True, through="CourseSpeaker")
    blocks = models.ManyToManyField(Block, related_name="speakers", blank=True)

    first_name = models.CharField(null=True, blank=True, max_length=200)
    last_name = models.CharField(null=True, blank=True, max_length=200)
    full_name = models.CharField(null=True, blank=True, max_length=200)
    video_url = models.CharField(max_length=200, null=True, blank=True)
    slug = models.SlugField(max_length=200, unique=True)
    suffix = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=400, null=True, blank=True)
    institution = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pronouns = models.CharField(null=True, blank=True, max_length=200)
    identities = models.CharField(null=True, blank=True, max_length=400)
    bio = models.TextField(null=True, blank=True)

    headshot_image = models.ImageField(
        upload_to="speakers",
        null=True,
        blank=True,
    )

    @property
    def headshot_url(self) -> Optional[str]:
        if self.headshot_image:
            return self.headshot_image.url
        else:
            return None

    def __str__(self):
        return f"Speaker [{self.id}]: {self.full_name}"


class CourseSpeaker(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    speaker = models.ForeignKey(Speaker, on_delete=models.CASCADE)

    has_course_headshot = models.BooleanField(
        default=False, help_text="Use a course-specific headshot (rather than the default headshot)"
    )

    has_course_video = models.BooleanField(
        default=False, help_text="Use a course-specific bio video (rather than the default bio video)"
    )

    @property
    def show_bio_video(self):
        if self.has_course_video or (not self.has_course_headshot and self.speaker.video_url):
            return True
        else:
            return False

    @property
    def video_url(self) -> Optional[str]:
        if self.has_course_video and self.course:
            return f"https://kinesinlms.s3.us-west-1.amazonaws.com/media/speakers/{self.course.slug}/{self.speaker.slug}.jpg"
        elif self.speaker.video_url:
            return self.speaker.video_url
        else:
            return None

    @property
    def headshot_url(self) -> Optional[str]:
        if self.has_course_headshot and self.course:
            return f"https://kinesinlms.s3.us-west-1.amazonaws.com/media/speakers/{self.course.slug}/{self.speaker.slug}.jpg"
        elif self.speaker.headshot_url:
            return self.speaker.headshot_url
        else:
            return None
