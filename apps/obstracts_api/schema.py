import json
from django.http import JsonResponse
from django.views import View
import os
from importlib import import_module
from collections import namedtuple
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.settings import patched_settings, spectacular_settings
from drf_spectacular.renderers import (
    OpenApiJsonRenderer, OpenApiJsonRenderer2, OpenApiYamlRenderer, OpenApiYamlRenderer2,
)
from drf_spectacular.views import SpectacularSwaggerView


def merge_components(comp1, comp2):
    merged = comp1.copy()

    for key, value in comp2.items():
        if key not in merged:
            merged[key] = value
        else:
            if isinstance(value, dict):
                merged[key].update(value)  # Simple merge, adjust as needed

    return merged


def merge_paths(paths1, paths2):
    merged = {}
    
    def add_to_merged_dict(paths):
        for original_path, methods in paths.items():
            path = original_path.replace('/obstracts_api/api/v1/', '/v1/')
            if path not in merged:
                merged[path] = methods
            else:
                for method, details in methods.items():
                    if method not in merged[path]:
                        merged[path][method] = details
                    else:
                        merged[path][method].update(details)        
    add_to_merged_dict(paths1)
    add_to_merged_dict(paths2)

    return merged


def extract_paths_and_schemas(openapi_data):
    # Extract paths
    paths = openapi_data.get('paths', {})

    # Initialize a dictionary to store the paths and their corresponding schemas
    path_schemas = {}

    for path, methods in paths.items():
        for method, details in methods.items():
            response_schemas = {}
            responses = details.get('responses', {})
            for status_code, response in responses.items():
                content = response.get('content', {})
                for media_type, media_details in content.items():
                    schema = media_details.get('schema', {})
                    if '$ref' in schema:
                        ref = schema['$ref']
                        response_schemas[status_code] = ref
                        path_schemas[ref] = True

    return path_schemas


import json


def find_unresolved_references(schemas):
    # Gather all component refs
    components = schemas
    resolved_refs = set(components.keys())
    results = set()

    # A function to recursively check for refs in the paths
    def check_refs(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == '$ref':
                    if value.split('/')[-1] not in resolved_refs:
                        print(f"Unresolved reference: {value}")
                        results.add(value)
                else:
                    check_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                check_refs(item)

    # Check paths for unresolved references
    for schema in schemas.values():
        check_refs(schema)
    return results

class SchemaView(APIView):
    renderer_classes = [
        OpenApiYamlRenderer, OpenApiYamlRenderer2, OpenApiJsonRenderer, OpenApiJsonRenderer2
    ]
    permission_classes = spectacular_settings.SERVE_PERMISSIONS
    authentication_classes = []
    generator_class= spectacular_settings.DEFAULT_GENERATOR_CLASS
    serve_public: bool = spectacular_settings.SERVE_PUBLIC
    urlconf = spectacular_settings.SERVE_URLCONF
    api_version = None
    custom_settings = None
    patterns = None
    def get(self, request, *args, **kwargs):
        if isinstance(self.urlconf, list) or isinstance(self.urlconf, tuple):
            ModuleWrapper = namedtuple('ModuleWrapper', ['urlpatterns'])
            if all(isinstance(i, str) for i in self.urlconf):
                # list of import string for urlconf
                patterns = []
                for item in self.urlconf:
                    url = import_module(item)
                    patterns += url.urlpatterns
                self.urlconf = ModuleWrapper(tuple(patterns))
            else:
                # explicitly resolved urlconf
                self.urlconf = ModuleWrapper(tuple(self.urlconf))
        api_schema = self._get_schema_response(request)

        schema_path = self.get_schema_path()
        with open(schema_path) as schema_file:
            obstracts_schema = json.load(schema_file)

        merged_components = merge_components(
            api_schema.get('components', {}),
            obstracts_schema.get('components', {})
        )

        merged_paths = merge_paths(obstracts_schema.get('paths', {}), api_schema.get('paths', {}))
        merged_components['securitySchemes'] = {
            'api_key': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'API-KEY'
            }
        }
        merged_swagger = {
            'openapi': '3.0.0',
            'info': {
                'title': 'Obstracts Web API',
                'version': '1.0.0',
                'description': '[Back to Obstracts Web](https://app.obstracts.com)'
            },
            'components': merged_components,
            'paths': merged_paths
        }

        schema = extract_paths_and_schemas(merged_swagger)
        new_schema_dict = {}
        schemas = merged_components['schemas']
        for component_key in schemas:
            if f"#/components/schemas/{component_key}" in schema:
                new_schema_dict[component_key] = schemas[component_key]
        refs = find_unresolved_references(new_schema_dict)
        for ref in refs:
            ref_key = ref.split("/")[-1]
            if ref_key in new_schema_dict:
                continue
            new_schema_dict[ref_key] = schemas[ref_key]

        merged_components['schemas'] = new_schema_dict
        return JsonResponse(merged_swagger)

    def get_schema_path(self):
        os.path.join('templates', 'obstracts_api', 'schema.json')

    def _get_schema_response(self, request):
        # version specified as parameter to the view always takes precedence. after
        # that we try to source version through the schema view's own versioning_class.
        version = self.api_version or request.version or self._get_version_parameter(request)
        generator = self.generator_class(urlconf=self.urlconf, api_version=version, patterns=self.patterns)
        data = generator.get_schema(request=request, public=self.serve_public)
        path_items = data["paths"].items()

        filtered_paths = list(filter(lambda item: '/api/v1/feeds/' in item[0] and "get" in item[1], path_items))
        path_dict = {}
        security_requirement = [{'api_key': []}]
        for key, value in filtered_paths:
            get_value = value["get"]
            get_value['security'] = security_requirement
            get_value['tags'] = ["Feeds"]
            path_dict[key] = {"get": get_value}

        data["paths"] = path_dict
        return data

    def _get_filename(self, request, version):
        return "{title}{version}.{suffix}".format(
            title=spectacular_settings.TITLE or 'schema',
            version=f' ({version})' if version else '',
            suffix=self.perform_content_negotiation(request, force=True)[0].format
        )

    def _get_version_parameter(self, request):
        return None

class AdminSchemaView(SchemaView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def resolve_schemas(self, merged_swagger):
        pass

    def get_schema_path(self):
        return os.path.join('templates', 'obstracts_api', 'admin-schema.json')


class AdminSwaggerView(SpectacularSwaggerView):
    permission_classes = [IsAdminUser]
