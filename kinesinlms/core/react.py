import json
import uuid

from django import template
from django.conf import settings
from django.template.base import Node
from django_react_templatetags.encoders import json_encoder_cls_factory
from django_react_templatetags.templatetags.react import load_from_ssr

"""
DMcQ: Jan 28 2022
This is my variation of the ReactTagManager that comes as part of the django-react-templatetags
library. We create our own (very slightly modified) version here so we can decide which
component prefix to use for the React class to be instantiated. 
 
We do this because we break up our Course Unit components into a core library loaded
on every page -- and thereby using the "kinesinlmsComponents." prefix -- and other libraries
that hold more expensive components that should only be loaded when needed.
 
This class is set in the settings variable REACT_RENDER_TAG_MANAGER in base.py so
django-react-templatetags knows to use it rather than the default.

"""

CONTEXT_KEY = "REACT_COMPONENTS"


def get_uuid():
    return uuid.uuid4().hex


def has_ssr(request):
    if request and request.META.get("HTTP_X_DISABLE_SSR"):
        return False

    return hasattr(settings, "REACT_RENDER_HOST") and settings.REACT_RENDER_HOST


class KinesinLMSReactTagManager(Node):
    """
    Handles the printing of React placeholders and queueing, is invoked by
    react_render.
    """

    def __init__(
            self,
            identifier,
            component,
            data=None,
            css_class=None,
            props=None,
            ssr_context=None,
            no_placeholder=None,
    ):
        component_prefix = ""
        if hasattr(settings, "REACT_COMPONENT_PREFIX"):
            component_prefix = settings.REACT_COMPONENT_PREFIX

        self.identifier = identifier
        self.component = component
        if component.literal in ['Diagram', 'DiagramTemplate']:
            self.component_prefix = 'kinesinlmsDiagramsComponents.'
        elif component.literal in ['Tabletool', 'TabletoolTemplate']:
            self.component_prefix = 'kinesinlmsTabletoolComponents.'
        else:
            self.component_prefix = component_prefix
        self.data = data
        self.css_class = css_class
        self.props = props
        self.ssr_context = ssr_context
        self.no_placeholder = no_placeholder

    def render(self, context):
        qualified_component_name = self.get_qualified_name(context)
        identifier = self.get_identifier(context, qualified_component_name)
        component_props = self.get_component_props(context)
        json_str = self.props_to_json(component_props, context)

        component = {
            "identifier": identifier,
            "data_identifier": "{}_data".format(identifier),
            "name": qualified_component_name,
            "json": json_str,
            "json_obj": json.loads(json_str),
        }

        placeholder_attr = (
            ("id", identifier),
            ("class", self.resolve_template_variable(self.css_class, context)),
        )
        placeholder_attr = [x for x in placeholder_attr if x[1] is not None]

        component_html = ""
        if has_ssr(context.get("request", None)):
            ssr_resp = load_from_ssr(
                component,
                ssr_context=self.get_ssr_context(context),
            )
            component_html = ssr_resp["html"]
            component["ssr_params"] = ssr_resp["params"]

        components = context.get(CONTEXT_KEY, [])
        components.append(component)
        context[CONTEXT_KEY] = components

        if self.no_placeholder:
            return component_html

        return self.render_placeholder(placeholder_attr, component_html)

    def get_qualified_name(self, context):
        component_name = self.resolve_template_variable(self.component, context)
        return "{}{}".format(self.component_prefix, component_name)

    def get_identifier(self, context, qualified_component_name):
        identifier = self.resolve_template_variable(self.identifier, context)

        if identifier:
            return identifier

        return "{}_{}".format(qualified_component_name, get_uuid())

    def get_component_props(self, context):
        resolved_data = self.resolve_template_variable_else_none(self.data, context)
        resolved_data = resolved_data if resolved_data else {}

        for prop in self.props:
            data = self.resolve_template_variable_else_none(
                self.props[prop],
                context,
            )
            resolved_data[prop] = data

        return resolved_data

    def get_ssr_context(self, context):
        if not self.ssr_context:
            return {}

        return self.resolve_template_variable(self.ssr_context, context)

    @staticmethod
    def resolve_template_variable(value, context):
        if isinstance(value, template.Variable):
            return value.resolve(context)
        return value

    @staticmethod
    def resolve_template_variable_else_none(value, context):
        try:
            data = value.resolve(context)
        except template.VariableDoesNotExist:
            data = None
        except AttributeError:
            data = None

        return data

    @staticmethod
    def props_to_json(resolved_data, context):
        cls = json_encoder_cls_factory(context)
        return json.dumps(resolved_data, cls=cls)

    @staticmethod
    def render_placeholder(attributes, component_html=""):
        attr_pairs = map(lambda x: '{}="{}"'.format(*x), attributes)
        return u"<div {}>{}</div>".format(
            " ".join(attr_pairs),
            component_html,
        )
