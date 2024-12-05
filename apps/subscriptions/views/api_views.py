import rest_framework.serializers
from djstripe.models import Product
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from apps.subscriptions.helpers import (
    create_stripe_checkout_session,
    get_subscription_urls,
    provision_subscription,
)
from apps.subscriptions.wrappers import SubscriptionWrapper
from apps.teams.decorators import login_and_team_required
from apps.utils.billing import get_stripe_module
from apps.api.permissions import IsAuthenticatedOrHasUserAPIKey
from apps.teams.decorators import team_admin_required

from ..exceptions import SubscriptionConfigError
from ..helpers import create_stripe_checkout_session, create_stripe_portal_session
from ..metadata import get_active_products_with_metadata, ProductWithMetadata
from ..serializers import (
    SubscriptionProductSerializer,
    InitSubscriptionSerializer,
    SubscriptionSerializer,
)


@extend_schema(tags=["subscriptions"], exclude=True)
class ProductWithMetadataAPI(APIView):
    permission_classes = (IsAuthenticatedOrHasUserAPIKey,)

    @extend_schema(
        operation_id="active_products_list",
        responses={200: ProductWithMetadata.serializer()},
    )
    def get(self, request, *args, **kw):
        products_with_metadata = get_active_products_with_metadata()
        return Response(data=[p.to_dict() for p in products_with_metadata])


@extend_schema(tags=["subscriptions"], exclude=True)
class CreateCheckoutSession(APIView):
    @extend_schema(
        operation_id="create_checkout_session",
        request=inline_serializer(
            "CreateCheckout", {"priceid": rest_framework.serializers.CharField()}
        ),
        responses={
            200: OpenApiTypes.URI,
        },
    )
    @method_decorator(team_admin_required)
    def post(self, request, team_slug):
        subscription_holder = request.team
        price_id = request.POST["priceId"]
        checkout_session = create_stripe_checkout_session(
            subscription_holder,
            price_id,
            request.user,
        )
        return Response(checkout_session.url)


@extend_schema(tags=["subscriptions"], exclude=True)
class CreatePortalSession(APIView):
    @extend_schema(
        operation_id="create_portal_session",
        request=None,
        responses={
            200: OpenApiTypes.URI,
        },
    )
    @method_decorator(team_admin_required)
    def post(self, request, team_slug):
        try:
            portal_session = create_stripe_portal_session(subscription_holder)
            return Response(portal_session.url)
        except SubscriptionConfigError as e:
            return Response(str(e), status=500)


class SubscriptionProductViewSet(GenericViewSet, ListModelMixin):
    serializer_class = SubscriptionProductSerializer

    def get_queryset(self):
        return Product.objects.filter(active=True).prefetch_related("prices").all()


class TeamSubscriptionViewSet(GenericViewSet, CreateModelMixin):
    serializer_class = InitSubscriptionSerializer

    @action(detail=False, methods=["get"], url_path="active-subscription")
    def get_active_subscription(self, request, *args, **kwargs):
        subscription = request.team.subscription
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription_holder = request.team
        price_id = serializer.validated_data.get("price_id")
        checkout_session = create_stripe_checkout_session(
            subscription_holder,
            price_id,
            request.user,
        )
        return Response(
            {"redirect_url": checkout_session.url}, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="confirm-subscription")
    def confirm_subscription(self, request, *args, **kwargs):
        session_id = request.data.get("session_id")
        session = get_stripe_module().checkout.Session.retrieve(session_id)
        client_reference_id = int(session.client_reference_id)
        subscription_holder = request.user.teams.select_related(
            "subscription", "customer"
        ).get(id=client_reference_id)
        if (
            not subscription_holder.subscription
            or subscription_holder.subscription.id != session.subscription
        ):
            # provision subscription
            djstripe_subscription = provision_subscription(
                subscription_holder, session.subscription
            )
        else:
            # already provisioned (likely by webhook)
            djstripe_subscription = subscription_holder.subscription

        subscription_name = SubscriptionWrapper(djstripe_subscription).display_name
        return Response({"status": True})

    @action(detail=False, methods=["post"], url_path="create-portal-session")
    def init_portal(self, request, *args, **kwargs):
        subscription_holder = request.team
        if subscription_holder.is_private:
            raise ValidationError("Subscription can't be changed for a private space")
        portal_session = create_stripe_portal_session(subscription_holder)
        return Response(
            {"redirect_url": portal_session.url}, status=status.HTTP_201_CREATED
        )
