# KinesinLMS API

KinesinLMS offers a limited set of API endpoints using [Django Rest Framework](https://www.django-rest-framework.org/).
These endpoints could be easily extended, as DRF is powerful and flexible.

There are two basic sets of API endpoints currently available:

1. "Internal" endpoints: for components within KinesinLMS that need to access the site via API, such as
   "Simple Interactive Tool" components, which load their initial data and submit student activity via API.
2. "Analytics" endpoints: for the external applications that need analytics data.

Both sets of endpoints are configured in the top-level `config/urls.py` module.

## Internal Endpoints

At the moment, the main use of "internal" API endpoints are the React-based video component and
simple interactive tools that we load in a course unit page.

Internal endpoints are configured in the Router under `router = routers.DefaultRouter()`

A call to an endpoint here starts with `/api/`

## Analytics Endpoints

Analytics endpoints are meant to be called by an external resource and therefore use
the default token-based authentication provided by DRF.

A call to an endpoint in this group starts with `/api/analytics/`
