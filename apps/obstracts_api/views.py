import requests
from django.conf import settings
from django.db.models import Exists, OuterRef, Value, BooleanField
from django.db.models.functions import Cast
from django.db.models.fields.json import KT as KeyTextTransform
from django.db.models import CharField, IntegerField, DateTimeField
from django.http import JsonResponse, HttpResponse
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, response, status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotFound,
    ValidationError as DRFValidationError,
    PermissionDenied,
)
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from apps.api.permissions import HasTeamApiKey, HasTeamFeedApiKey
from apps.teams.models import Membership, Team
from .models import Feed, FeedSubsription
from .pagination import CustomPagination
from .serializers import (
    FeedSerializer,
    SubscribedFeedSerializer,
    SkeletonFeedSerializer,
    FeedWithSubscriptionSerializer,
    SubscribeFeedSerializer,
)
from .utils import delete_obstracts_feed, get_posts_by_extractions, get_latest_posts


class ProxyView(APIView):
    def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?
        try:
            if not IsAdminUser().has_permission(self.request, self):
                raise PermissionDenied()
            # Modify the target URL as needed
            target_url = settings.OBSTRACT_SERVICE_API + "/" + kwargs["path"]

            # Forward the request to the target URL
            response = requests.request(
                method=request.method,
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=self.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
                content_type=self.headers.get("Content-Type"),
            )
        except Exception as exc:
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 10000


class FeedViewSet(
    GenericViewSet,
    ListModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
    RetrieveModelMixin,
):
    serializer_class = FeedSerializer
    pagination_class = LargeResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "profile_id",
    ]
    permission_classes = [IsAdminUser]

    def sort_queryset(self, queryset):
        order_by = self.request.query_params.get("order_by")
        order_types = {
            "url": CharField(),
            "title": CharField(),
            "feed_type": CharField(),
            "pretty_url": CharField(),
            "description": CharField(),
            "count_of_posts": IntegerField(),
            "datetime_added": DateTimeField(),
            "latest_item_pubdate": DateTimeField(),
            "earliest_item_pubdate": DateTimeField(),
        }
        annotate_field_name = f'sort_{order_by}'
        if order_by:
            desc = False
            if "-" in order_by:
                desc = True
                order_by = order_by.replace("-", "")
            if order_by not in order_types.keys():
                return queryset
            queryset = queryset.annotate(
                **{
                    annotate_field_name: Cast(
                        KeyTextTransform(f"obstract_feed_metadata__{order_by}"), order_types[order_by]
                    )
                }
            )
            order_by_field = ('-' if desc else '') + annotate_field_name
            queryset = queryset.order_by(order_by_field)
        return queryset

    def filter_queryset(self, queryset):
        title = self.request.query_params.get("title")
        queryset = self.sort_queryset(queryset)
        if title:
            queryset = queryset.annotate(
                title_filter=KeyTextTransform("obstract_feed_metadata__title")
            ).filter(title_filter__icontains=title)
        return super().filter_queryset(queryset)



    def get_queryset(self):
        return Feed.objects.all()

    def perform_destroy(self, *args, **kwargs):
        feed = self.get_object()
        delete_obstracts_feed(feed.obstract_feed_metadata["id"])
        feed.delete()

    @action(detail=False, methods=['POST'])
    def skeleton(self, *args, **kwargs):
        serializer = SkeletonFeedSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class TeamFeedViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    # pagination_class = PageNumberPagination
    pagination_class = CustomPagination
    serializer_class = FeedWithSubscriptionSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    # pagination_class = None

    def sort_queryset(self, queryset):
        order_by = self.request.query_params.get("order_by")
        order_types = {
            "url": CharField(),
            "title": CharField(),
            "feed_type": CharField(),
            "pretty_url": CharField(),
            "description": CharField(),
            "count_of_posts": IntegerField(),
            "datetime_added": DateTimeField(),
            "latest_item_pubdate": DateTimeField(),
            "earliest_item_pubdate": DateTimeField(),
        }
        annotate_field_name = f'sort_{order_by}'
        if order_by:
            desc = False
            if "-" in order_by:
                desc = True
                order_by = order_by.replace("-", "")
            if order_by not in order_types.keys():
                return queryset
            queryset = queryset.annotate(
                **{
                    annotate_field_name: Cast(
                        KeyTextTransform(f"obstract_feed_metadata__{order_by}"), order_types[order_by]
                    )
                }
            )
            order_by_field = ('-' if desc else '') + annotate_field_name
            queryset = queryset.order_by(order_by_field)
        return queryset

    def filter_queryset(self, queryset):
        title = self.request.query_params.get("title")
        queryset = self.sort_queryset(queryset)
        if title:
            queryset = queryset.annotate(
                title_filter=KeyTextTransform("obstract_feed_metadata__title")
            ).filter(title_filter__icontains=title)
        return super().filter_queryset(queryset)

    def get_feeds_with_subscription_status(self, team_id):
        # Subquery to check if the feed is subscribed by the given team
        subscriptions = FeedSubsription.objects.filter(
            feed=OuterRef("pk"), team_id=team_id
        )

        # Fetch all feeds and annotate them with subscription status
        feeds = Feed.objects.filter(is_public=True).annotate(
            is_subscribed=Exists(subscriptions)
        )
        if self.request.query_params.get("show_only_my_feeds") == "true":
            feeds = feeds.filter(is_subscribed=True)

        return feeds

    def get_queryset(self):
        return self.get_feeds_with_subscription_status(self.kwargs.get("team_id"))

    @action(detail=False, methods=["post"], url_path="subscribe")
    def subscribe(self, *args, **kwargs):
        team_id = self.kwargs.get("team_id")
        team = self.request.team
        if team.is_private:
            raise DRFValidationError("Team has no access to this API")
        if not team.active_stripe_subscription:
            raise DRFValidationError(
                {
                    "code": "E01",
                    "message": "Team subscription feed subscription limit exceeded",
                }
            )
        team_suscription_count = FeedSubsription.objects.filter(team=team).count()
        team_feed_suscription_limit = team.get_feed_limit()
        if (
            team_feed_suscription_limit
            and not team_feed_suscription_limit > team_suscription_count
        ):
            raise DRFValidationError(
                {
                    "code": "E01",
                    "message": "Team subscription feed subscription limit exceeded",
                }
            )
        serializer = SubscribeFeedSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        feed_id = serializer.validated_data["feed_id"]
        feed_exists = Feed.objects.filter(id=feed_id).exists()
        if not feed_exists:
            raise NotFound()
        FeedSubsription.objects.create(team_id=team_id, feed_id=feed_id)
        return Response({})

    @action(detail=False, methods=["post"], url_path="unsubscribe")
    def unsubscribe(self, *args, **kwargs):
        serializer = SubscribeFeedSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        feed_id = serializer.validated_data["feed_id"]
        feed_exists = Feed.objects.filter(id=feed_id).exists()
        if not feed_exists:
            raise NotFound()
        FeedSubsription.objects.filter(
            team_id=self.kwargs.get("team_id"), feed_id=feed_id
        ).delete()
        return Response({})

    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())
    #
    #     page = self.paginate_queryset(queryset)
    #     print(page.query)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)


class LatestPostView(ListAPIView):
    permission_classes = [IsAuthenticated]
    
    def list(self, *args, **kwargs):
        team_id = kwargs.get("team_id")
        page = self.request.query_params.get("page")
        title = self.request.query_params.get("title")
        sort = self.request.query_params.get("sort", "pubdate_descending")
        feed_title_dict = {}
        feed_ids = None
        if team_id:
            subscriptions = FeedSubsription.objects.filter(team_id=team_id).select_related('feed')
            feed_ids = [subscription.feed_id for subscription in subscriptions]
            for subscription in subscriptions:
                feed_title_dict[str(subscription.feed_id)] = subscription.feed.obstract_feed_metadata.get('title')
        else:
            if not self.request.user.is_staff:
                raise PermissionDenied()
        response = get_latest_posts(feed_ids, sort, title, page)
        posts = response['posts']
        if feed_ids == None:
            post_feed_ids = [post['feed_id'] for post in posts]
            feeds = Feed.objects.filter(id__in=post_feed_ids)
            for feed in feeds:
                feed_title_dict[str(feed.id)] = feed.obstract_feed_metadata.get('title')
        for post in posts:
            post['feed_title'] = feed_title_dict.get(post['feed_id'])
        return Response(response)


class PostsByExtractionView(ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_feeds_with_subscription_status(self, team_id):
        # Subquery to check if the feed is subscribed by the given team
        subscriptions = FeedSubsription.objects.filter(
            feed=OuterRef("pk"), team_id=team_id
        )

        # Fetch all feeds and annotate them with subscription status
        feeds = Feed.objects.filter(is_public=True).annotate(
            is_subscribed=Exists(subscriptions)
        )
        if self.request.query_params.get("show_only_my_feeds") == "true":
            feeds = feeds.filter(is_subscribed=True)

        return feeds

    def list(self, *args, **kwargs):
        team_id = kwargs.get("team_id")
        object_id = kwargs.get("object_id")
        page = self.request.query_params.get("page")
        posts, feed_ids, obstracts_api_response = get_posts_by_extractions(object_id, page)
        feeds = []
        if team_id:
            feeds = self.get_feeds_with_subscription_status(team_id).filter(
                id__in=feed_ids
            )
        else:
            if not self.request.user.is_staff:
                raise PermissionDenied()
            feeds = Feed.objects.filter(id__in=feed_ids).annotate(
                is_subscribed=Value(True)
            )
        feed_dict = {}
        for feed in feeds:
            feed_dict[str(feed.id)] = FeedWithSubscriptionSerializer(feed).data
        result = []

        for post in posts:
            feed = feed_dict.get(post["feed_id"])
            if not feed:
                continue
            post["feed"] = feed
            result.append(post)
        del obstracts_api_response['reports']
        obstracts_api_response['posts'] = posts
        return Response(obstracts_api_response)


class FeedProxyView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not HasTeamFeedApiKey().has_permission(self.request, self):
                raise PermissionDenied()
            # Modify the target URL as needed
            feed_id = self.feed_id
            target_url = (
                f"{settings.OBSTRACT_SERVICE_API}/feeds/{feed_id}/{kwargs['path']}"
            )
            if request.method != "GET":
                raise MethodNotAllowed()

            # Forward the request to the target URL
            response = requests.request(
                method="GET",
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
            )
        except Exception as exc:
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response

class ObjectsProxyView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not IsAuthenticated().has_permission(self.request, self):
                raise PermissionDenied()
            # Modify the target URL as needed
            target_url = (
                f"{settings.OBSTRACT_SERVICE_API}/objects/{kwargs['path']}"
            )
            if request.method != "GET":
                raise MethodNotAllowed()

            # Forward the request to the target URL
            response = requests.request(
                method="GET",
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
            )
        except Exception as exc:
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response

class ObjectProxyView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not IsAuthenticated().has_permission(self.request, self):
                raise PermissionDenied()
            # Modify the target URL as needed
            target_url = (
                f"{settings.OBSTRACT_SERVICE_API}/object/{kwargs['object_id']}"
            )
            if request.method != "GET":
                raise MethodNotAllowed()

            # Forward the request to the target URL
            response = requests.request(
                method="GET",
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
            )
        except Exception as exc:
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response


class TeamFeedProxyView(APIView):
    def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            if not IsAuthenticated().has_permission(self.request, self):
                raise PermissionDenied()

            team_id = kwargs.get("team_id")
            feed_id = kwargs.get("feed_id")
            team = Team.objects.filter(id=team_id).first()
            if not team or not team.active_stripe_subscription:
                raise PermissionDenied("Team has no access to this API")
            if not Membership.objects.filter(
                user=self.request.user, team_id=team_id
            ).exists():
                raise PermissionDenied()
            if not FeedSubsription.objects.filter(
                feed_id=feed_id, team_id=team_id
            ).exists():
                raise PermissionDenied()
            # Modify the target URL as needed
            target_url = (
                f"{settings.OBSTRACT_SERVICE_API}/feeds/{feed_id}/{kwargs['path']}"
            )
            if request.method != "GET":
                raise MethodNotAllowed()

            # Forward the request to the target URL
            response = requests.request(
                method="GET",
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
            )
        except Exception as exc:
            raise exc
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response


class OpenFeedProxyView(APIView):
    def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers

        try:
            if not IsAuthenticated().has_permission(self.request, self):
                raise PermissionDenied()

            url = request.path
            path = url.split("proxy/open/")[1]
            # Modify the target URL as needed
            target_url = f"{settings.OBSTRACT_SERVICE_API}/{path}"
            if request.method != "GET":
                raise MethodNotAllowed()

            # Forward the request to the target URL
            response = requests.request(
                method="GET",
                url=target_url,
                headers={
                    key: value
                    for key, value in request.headers.items()
                    if key != "Host"
                },
                data=request.body,
                params={key: value for key, value in request.GET.items()},
                allow_redirects=False,
            )

            # Return the response to the original request
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type"),
            )
        except PermissionDenied:
            return HttpResponse(
                {},
                status=401,
            )
        except Exception as exc:
            response = self.handle_exception(exc)
            self.response = self.finalize_response(request, response, *args, **kwargs)
            return self.response


class TeamTokenFeedViewSet(GenericViewSet, ListModelMixin):
    pagination_class = CustomPagination
    serializer_class = SubscribedFeedSerializer
    permission_classes = [HasTeamApiKey]
    lookup_field = "feed_id"

    def get_queryset(self):
        return FeedSubsription.objects.filter(team=self.team).select_related("feed")

    @extend_schema(
        summary="Fetch list of subscribed feeds",
        description="Retrieve the list of feeds that the team has subscribed to.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
