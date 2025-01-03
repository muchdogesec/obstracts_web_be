# your_app/management/commands/your_command.py
import os
import json
import requests
import yaml

from django.core.management.base import BaseCommand
from django.conf import settings

OBSTRACT_SERVICE_BASE_URL = settings.OBSTRACT_SERVICE_BASE_URL


class Command(BaseCommand):
    
    def filter_path(self, path):
        if "get" not in path[1]:
            return False
        if 'feed_id' in path[0]:
            return True
        if '/objects/'in path[0] and "reports" not in path[0]:
            return True
        if '/object/'in path[0] and "reports" not in path[0]:
            return True
        return False
    
    def handle(self, *args, **kwargs):
        res = requests.get(OBSTRACT_SERVICE_BASE_URL + '/api/schema/')
        data_json = yaml.safe_load(res.text)
        path_items = data_json["paths"].items()
        filtered_paths = list(filter(lambda item: self.filter_path(item), path_items))
        path_dict = {}
        security_requirement = [{'api_key': []}]
        for key, value in filtered_paths:
            get_value = value["get"]
            get_value['security'] = security_requirement
            path_dict['/obstracts_api' + key] = {"get": get_value}
        data_json["paths"] = path_dict
        data_json['components']['securitySchemes'] = {
            'api_key': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'API-KEY'
            }
        }
        data_json['security'] = [{
            'api_key': []
        }]

        schema_filename = os.path.join('templates', 'obstracts_api', 'schema.json')
        with open(schema_filename, 'w') as file:
            file.write(json.dumps(data_json))
