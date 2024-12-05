from djstripe.models import Product, Subscription, Price, SubscriptionItem
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class PriceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name")
    human_readable_price = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_human_readable_price(self, obj):
        # this needs to be here because djstripe can return a proxy object which can't be serialized
        return str(obj.human_readable_price)

    @extend_schema_field(OpenApiTypes.STR)
    def get_payment_amount(self, obj):
        if self.context.get("product_metadata", None):
            return self.context["product_metadata"].get_price_display(obj)
        return str(obj.human_readable_price)

    class Meta:
        model = Price
        fields = (
            "id",
            "product_name",
            "human_readable_price",
            "payment_amount",
            "nickname",
            "unit_amount",
        )

class PriceWithRecurringInfoSerializer(PriceSerializer):
    recurring_type = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = (
            "id",
            "product_name",
            "human_readable_price",
            "payment_amount",
            "nickname",
            "unit_amount",
            "recurring_type"
        )
    def get_recurring_type(self, obj):
        return obj.recurring['interval']


class SubscriptionProductSerializer(serializers.ModelSerializer):
    prices = PriceWithRecurringInfoSerializer(many=True)

    class Meta:
        fields = "__all__"
        model = Product


class InitSubscriptionSerializer(serializers.Serializer):
    price_id = serializers.CharField(write_only=True)
    redirect_url = serializers.CharField(read_only=True)


class SubscriptionItemSerializer(serializers.ModelSerializer):
    price = PriceSerializer()

    class Meta:
        model = SubscriptionItem
        fields = ("id", "price", "quantity")


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    A serializer for Subscriptions which uses the SubscriptionWrapper object under the hood
    """

    items = SubscriptionItemSerializer(many=True)

    class Meta:
        # we use Subscription instead of SubscriptionWrapper so DRF can infer the model-based fields automatically
        model = Subscription
        fields = (
            "id",
            "start_date",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "start_date",
            "status",
            "quantity",
            "items",
        )


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name")
