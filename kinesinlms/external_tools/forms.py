from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Fieldset
from kinesinlms.external_tools.models import ExternalToolProvider


class ExternalToolProviderForm(ModelForm):
    class Meta:
        model = ExternalToolProvider
        fields = [
            "name",
            "active",
            "type",
            "description",
            "connection_method",
            "username_field",
            "slug",
            "login_url",
            "launch_uri",
            "public_keyset_url",
            "client_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

        if self.instance:
            deployment_id = self.instance.deployment_id
            deployment_id_div = f'<div class="mb-3"><label class="form-label" for="deployment_id">Deployment ID</label><input class="form-control disabled" value="{deployment_id}" disabled /><div id="id_client_id_helptext" class="form-text">The deployment_id is a fixed value and never changes.</div></div>'
        else:
            deployment_id_div = "<div></div>"

        self.helper.layout = Layout(
            Fieldset(
                None,
                "active",
                "name",
                "type",
                "description",
                "connection_method",
                "username_field",
                "slug",
                "login_url",
                "launch_uri",
                "public_keyset_url",
                "client_id"
            ),
            HTML(deployment_id_div),
        )
        self.helper.form_method = "post"
