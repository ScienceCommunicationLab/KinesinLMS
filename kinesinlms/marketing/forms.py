from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from django import forms

trainer_info_description = """
Please briefly describe how you are implementing the “Planning Your Scientific Journey” course 
with your trainees, or what you are considering doing. (For example, are you planning to have 
the students meet on a regular basis to discuss topics? How will trainees report back to you on their progress? 
Are you planning to do any kind of evaluation to determine outcomes after the course is over? etc.). Please include any 
requests or questions you have for us.
"""


class TrainerInfoForm(forms.Form):
    COURSE_OPTIONS = (('PYSJ', 'Planning Your Scientific Journey'),
                      ('BCLS', 'Business Concepts for Life Scientists'),
                      ('LE', 'Let\'s Experiment'))

    full_name = forms.CharField(label='Full name', required=True, max_length=200)
    email = forms.EmailField(label='Email', required=True, max_length=200)
    courses = forms.MultipleChoiceField(label="Course(s) you are considering requiring",
                                        widget=forms.CheckboxSelectMultiple,
                                        choices=COURSE_OPTIONS)
    institution = forms.CharField(label="Institution", max_length=200, required=False)
    job_title = forms.CharField(label="Job Title", max_length=200, required=False)
    description = forms.CharField(label=trainer_info_description, widget=forms.Textarea, max_length=2000,
                                  required=False)
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',  # default=light
                'data-size': 'normal',  # default=normal
            },
        ),
    )


class ContactForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea,
                              label="Message",
                              max_length=2000)
    consent = forms.BooleanField(required=True,
                                 label="I consent to my submitted data being "
                                       "collected and stored by KinesinLMS.")

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox(
            attrs={
                'data-theme': 'light',  # default=light
                'data-size': 'normal',  # default=normal
            },
        ),
    )
