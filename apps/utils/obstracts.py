import requests
from django.conf import settings

OBSTRACT_SERVICE_API = settings.OBSTRACT_SERVICE_API


def get_profile(profile_id):
    response = requests.get(OBSTRACT_SERVICE_API+ '/profiles/')
    # print(response.json()['profiles'])
    data = response.json()['profiles']
    for item in data:
        print(item['id'], profile_id)
        if str(item['id']) == str(profile_id):
            print(True)
            return item
    return {}
