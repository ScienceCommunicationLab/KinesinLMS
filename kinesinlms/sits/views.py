from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import generic
from django.views.generic import DeleteView
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from kinesinlms.sits.forms import SimpleInteractiveToolTemplateForm
from kinesinlms.sits.models import SimpleInteractiveToolSubmission, SimpleInteractiveTool, SimpleInteractiveToolTemplate
from kinesinlms.sits.serializers import SimpleInteractiveToolSerializer, SimpleInteractiveToolSubmissionSerializer, \
    SimpleInteractiveToolTemplateSerializer


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# DRF ViewSets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ViewSets for admin and staff...

class SimpleInteractiveToolViewSet(ModelViewSet):
    serializer_class = SimpleInteractiveToolSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAdminUser,)
    queryset = SimpleInteractiveTool.objects.all()


class SimpleInteractiveToolTemplateViewSet(ModelViewSet):
    serializer_class = SimpleInteractiveToolTemplateSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAdminUser,)
    queryset = SimpleInteractiveToolTemplate.objects.all()

    def destroy(self, request, *args, pk=None, **kwargs):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ViewSets for student use...

class SimpleInteractiveToolSubmissionViewSet(ModelViewSet):
    serializer_class = SimpleInteractiveToolSubmissionSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_superuser:
            return SimpleInteractiveToolSubmission.objects.all()
        else:
            return SimpleInteractiveToolSubmission.objects.all().filter(student=self.request.user)

    @action(detail=True,
            methods=['get'],
            name='Template json')
    def template(self, request, pk):
        """
        Return the json for the SimpleInteractiveToolTemplate for this
        SimpleInteractiveTool, if one is defined.
        """
        submission: SimpleInteractiveToolSubmission = get_object_or_404(SimpleInteractiveToolSubmission,
                                                                        id=pk,
                                                                        student=request.user)
        if submission.simple_interactive_tool.template:
            template_json = submission.simple_interactive_tool.template.template_json
            return Response(template_json, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    # We allow retrieve, create, update, patch.

    # But don't allow partial, list and destroy...

    def partial_update(self, request, *args, pk=None, **kwargs):
        response = {'message': 'Partial function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def list(self, request, *args, pk=None, **kwargs):
        response = {'message': 'List function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, pk=None, **kwargs):
        response = {'message': 'Delete function is not offered in this path.'}
        return Response(response, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Django ViewSets
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SimpleInteractiveToolTemplateListView(UserPassesTestMixin, generic.ListView):
    model = SimpleInteractiveToolTemplate
    template_name = "composer/simple_interactive_tool/template_list.html"
    context_object_name = "simple_interactive_tool_templates"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super(SimpleInteractiveToolTemplateListView, self).get_context_data(**kwargs)
        extra_context = {
            "section": "simple_interactive_tool_template",
            "breadcrumbs": [
            ],
            "title": "Simple Interactive Tool Templates",
            "description": f"Templates by staff to pre-populate 'simple interactive tool' assessments.",
        }
        context = {**context, **extra_context}
        return context


class SimpleInteractiveToolTemplateCreateView(UserPassesTestMixin, generic.CreateView):
    model = SimpleInteractiveToolTemplate
    template_name = "composer/simple_interactive_tool/template_create.html"
    fields = ['name', 'tool_type', 'description', 'instructions']
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        simple_interactive_tool_template_id = self.object.id
        url = reverse('composer:simple_interactive_tool_template_design',
                      kwargs={'template_id': simple_interactive_tool_template_id})
        messages.add_message(self.request,
                             messages.INFO,
                             f"New {self.object.tool_type} template description. You can "
                             f"now create the template in the {self.object.tool_type} tool...")

        return url


class SimpleInteractiveToolTemplateUpdateView(UserPassesTestMixin, generic.UpdateView):
    model = SimpleInteractiveToolTemplate
    pk_url_kwarg = "template_id"
    template_name = "composer/simple_interactive_tool/template_edit_description.html"
    fields = ['name', 'description', 'instructions', 'tool_type']
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        messages.add_message(self.request, messages.INFO, f"SimpleInteractiveTool updated.")
        url = reverse('composer:simple_interactive_tool_templates_list')
        return url

    def get_context_data(self, **kwargs):
        context = super(SimpleInteractiveToolTemplateUpdateView, self).get_context_data(**kwargs)
        extra_context = {
            "section": "simple_interactive_tool_template",
            "breadcrumbs": [
                {
                    "url": reverse('composer:simple_interactive_tool_templates_list'),
                    "label": "SimpleInteractiveTool Templates"
                }
            ],
            "title": "Edit Template Description",
            "description": f"Editing '{self.object.name}' SimpleInteractiveTool template description.",
        }
        context = {**context, **extra_context}
        return context


class SimpleInteractiveToolTemplateDeleteView(UserPassesTestMixin, DeleteView):
    model = SimpleInteractiveToolTemplate
    pk_url_kwarg = "template_id"
    template_name = "composer/simple_interactive_tool/template_confirm_delete.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_success_url(self):
        obj = self.get_object()
        messages.add_message(self.request, messages.INFO,
                             f"Deleted SimpleInteractiveTool \"{obj.name}\"")
        url = reverse('composer:simple_interactive_tool_templates_list')
        return url


class SimpleInteractiveToolTemplateDetailView(UserPassesTestMixin, generic.DetailView):
    """
    This is a DetailView that also allows editing the template's SIT configuration
    data stored in the template_json field. The view shows the template in the target SIT tool.

    So, this view is different from the classes defined above:
      - SimpleInteractiveToolTemplateCreateView
      - SimpleInteractiveToolTemplateUpdateView
    ... since those views are for creating and editing the template instance itself,
    not the configuration code in the template_json field.
    """
    model = SimpleInteractiveToolTemplate
    template_name = "composer/simple_interactive_tool/template_edit_in_tool.html"
    context_object_name = "simple_interactive_tool_template"
    pk_url_kwarg = "template_id"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super(SimpleInteractiveToolTemplateDetailView, self).get_context_data(**kwargs)
        context['simple_interactive_tool_template_form'] = SimpleInteractiveToolTemplateForm()
        simple_interactive_tool_template: SimpleInteractiveToolTemplate = self.get_object()

        # Collect libraries we need to render the SIT.
        js_helper_libraries = SimpleInteractiveTool.get_helper_javascript_libraries(
            tool_type=simple_interactive_tool_template.tool_type)

        extra_context = {
            "js_helper_libraries": js_helper_libraries,
            "section": "simple_interactive_tool_template",
            "breadcrumbs": [
                {
                    "url": reverse('composer:simple_interactive_tool_templates_list'),
                    "label": "Simple Interactive Tool Templates"
                }
            ],
            "title": "Edit Template",
            "description": f"Editing '{simple_interactive_tool_template.name}' SimpleInteractiveTool template",
        }
        context = {**context, **extra_context}
        return context
