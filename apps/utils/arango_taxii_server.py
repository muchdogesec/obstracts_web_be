import re
from apps.api import permissions
from apps.obstracts_api.models import FeedSubsription, Feed
from rest_framework.views import APIView
from django.conf import settings
from  apps.teams.models import Team


API_ROOTS = ["obstracts_database"]
def filter_api_roots(view: APIView, api_roots: list[str]):
    roots = []
    for api_root in api_roots:
        root = [part for part in api_root.split('/') if part][-1]
        if root in API_ROOTS:
            roots.append(api_root)
    return roots

def filter_collections(view: APIView, collections: list[dict]):
    feeds: list[Feed] = view.request.team.feeds.all()

    accessible_feeds = []
    for feed in feeds:
        feed_id = feed.obstract_feed_metadata.get('id', '').replace('-', '')
        accessible_feeds.append(feed_id)

    retval = []
    for collection in collections:
        collection_name = collection['id']
        feed_id = collection_name.split('_')[-1]
        if feed_id in accessible_feeds:
            retval.append(collection)
    return retval


class Authenticated(permissions.HasTeamApiKey):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        return super().has_permission(
            request, view
        ) and self.has_permission_to_api_root(request, view) and self.has_permission_to_collection(request, view)

    def has_permission_to_api_root(self, request, view):
        api_root = view.kwargs.get('api_root')
        if not api_root:
            return True
        return api_root in API_ROOTS

    def has_permission_to_collection(self, request, view):
        feeds: list[Feed] = view.request.team.feeds.all()
        
        collection_name = view.kwargs.get('collection_id')
        if not collection_name:
            return True
        feed_id = collection_name.split('_')[-1]
        for feed in feeds:
            if feed.obstract_feed_metadata.get('id', '').replace('-', '') == feed_id:
                return True
        return False


def get_arango_auth(view: APIView):
    return settings.ARANGODB_USERNAME, settings.ARANGODB_PASSWORD