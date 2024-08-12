import logging
from typing import Dict, Optional

from django import template
from django.contrib.auth import get_user_model

from kinesinlms.sits.models import SimpleInteractiveTool
from kinesinlms.sits.utils import get_static_view_of_tabletool

logger = logging.getLogger(__name__)
register = template.Library()

User = get_user_model()


@register.simple_tag
def get_discourse_group_info(discourse_groups_lookup: Dict, group_id: int) -> Optional[Dict]:
    data = discourse_groups_lookup.get(group_id, None)
    return data


@register.simple_tag
def get_static_table_dict_for_tabletool(sit: SimpleInteractiveTool) -> Dict:
    table_dict = get_static_view_of_tabletool(sit=sit)
    return table_dict
