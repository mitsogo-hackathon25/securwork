import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .emails import send_order_admin_notification, send_order_confirmation
from .models import CartItem, Order
from .payments import (
    cancel_order,
    confirm_order_payment,
    create_stripe_checkout_session,
    handle_stripe_webhook,
    stripe_enabled,
)
from .serializers import (
    AddToCartSerializer,
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderSerializer,
)
from .services import create_order_from_cart, get_or_create_cart


class CartView(APIView):
    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")})
        return Response(serializer.data)

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request)
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]

        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity": quantity})
        if not created:
            new_qty = item.quantity + quantity
            if new_qty > variant.stock_quantity:
                return Response(
                    {"quantity": f"Only {variant.stock_quantity} units available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.quantity = new_qty
            item.save()

        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemView(APIView):
    def patch(self, request, item_id):
        cart = get_or_create_cart(request)
        try:
            item = cart.items.get(pk=item_id)
        except CartItem.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get("quantity")
        if quantity is None:
            return Response({"quantity": "Required."}, status=status.HTTP_400_BAD_REQUEST)
        quantity = int(quantity)
        if quantity <= 0:
            item.delete()
        else:
            if quantity > item.variant.stock_quantity:
                return Response(
                    {"quantity": f"Only {item.variant.stock_quantity} units available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.quantity = quantity
            item.save()

        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data
        )

    def delete(self, request, item_id):
        cart = get_or_create_cart(request)
        cart.items.filter(pk=item_id).delete()
        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data
        )


class PaymentConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "stripe_enabled": stripe_enabled(),
            "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
            "currency": settings.SECURWORK_CURRENCY,
            "bank_transfer_enabled": True,
            "bank_details": {
                "iban": getattr(settings, "SECURWORK_BANK_IBAN", "[PLACEHOLDER-IBAN]"),
                "bic": getattr(settings, "SECURWORK_BANK_BIC", "[PLACEHOLDER-BIC]"),
                "account_name": getattr(settings, "SECURWORK_BANK_ACCOUNT_NAME", "SecurWork S.r.l."),
            },
        })


class CheckoutView(APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = get_or_create_cart(request)

        try:
            order = create_order_from_cart(
                cart,
                data,
                user=request.user if request.user.is_authenticated else None,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = data.get("payment_method", "stripe")
        checkout_url = None

        if payment_method == "stripe" and stripe_enabled():
            try:
                checkout_url = create_stripe_checkout_session(order)
            except stripe.error.StripeError as e:
                cancel_order(order)
                return Response({"detail": str(e.user_message if hasattr(e, "user_message") else e)}, status=status.HTTP_502_BAD_GATEWAY)
        elif payment_method == "bank_transfer":
            send_order_confirmation(order)
            send_order_admin_notification(order)
        else:
            confirm_order_payment(order)

        return Response({
            "order": OrderSerializer(order).data,
            "checkout_url": checkout_url,
            "payment_method": payment_method,
        }, status=status.HTTP_201_CREATED)


class OrderVerifyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_number):
        session_id = request.query_params.get("session_id")
        try:
            order = Order.objects.prefetch_related("items").get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if session_id and stripe_enabled() and order.payment_status != Order.PaymentStatus.PAID:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                session = stripe.checkout.Session.retrieve(session_id)
                if session.payment_status == "paid" and session.metadata.get("order_number") == order_number:
                    confirm_order_payment(order, payment_intent_id=session.payment_intent or "")
            except stripe.error.StripeError:
                pass

        return Response(OrderSerializer(order).data)


@csrf_exempt
def stripe_webhook_view(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        handle_stripe_webhook(request.body, request.META.get("HTTP_STRIPE_SIGNATURE", ""))
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=400)
    return HttpResponse(status=200)


class OrderViewSet(ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")
