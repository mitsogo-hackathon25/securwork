import logging

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
from .models import Cart, CartItem, Order
from .paypal_payments import (
    PayPalError,
    PayPalVerificationError,
    create_paypal_checkout,
    paypal_enabled,
)
from .payments import (
    StripeVerificationError,
    cancel_order,
    create_stripe_checkout_session,
    handle_stripe_webhook,
    stripe_enabled,
    verify_and_confirm_paypal_order,
    verify_stripe_checkout_for_order,
)

logger = logging.getLogger(__name__)
from .serializers import (
    AddToCartSerializer,
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderSerializer,
)
from .services import create_order_from_cart, get_or_create_cart, quote_checkout_from_cart


def _cart_with_items(cart):
    return Cart.objects.prefetch_related(
        "items__customization",
        "items__variant__product",
    ).get(pk=cart.pk)


class CartView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        cart = _cart_with_items(get_or_create_cart(request))
        serializer = CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")})
        payload = dict(serializer.data)
        payment_method = request.query_params.get("payment_method")
        fulfillment_type = request.query_params.get("fulfillment_type", "delivery")
        if fulfillment_type not in ("delivery", "pickup"):
            fulfillment_type = "delivery"
        if request.user.is_authenticated and payment_method in ("stripe", "paypal", "bank_transfer", "card"):
            coupon_code = request.query_params.get("coupon_code", "")
            from .payment_methods import normalize_payment_method

            quote = quote_checkout_from_cart(
                cart,
                coupon_code=coupon_code,
                payment_method=normalize_payment_method(payment_method),
                fulfillment_type=fulfillment_type,
            )
            payload["checkout_preview"] = {
                key: f"{quote[key]:.2f}" if hasattr(quote[key], "quantize") else quote[key]
                for key in quote
            }
        return Response(payload)

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request)
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]

        customization = serializer.validated_data.get("customization")
        if customization:
            if quantity > variant.stock_quantity:
                return Response(
                    {"quantity": f"Only {variant.stock_quantity} units available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            CartItem.objects.create(
                cart=cart,
                variant=variant,
                quantity=quantity,
                customization=customization,
            )
        else:
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                customization=None,
                defaults={"quantity": quantity},
            )
            if not created:
                new_qty = item.quantity + quantity
                if new_qty > variant.stock_quantity:
                    return Response(
                        {"quantity": f"Only {variant.stock_quantity} units available."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                item.quantity = new_qty
                item.save()

        cart = _cart_with_items(cart)
        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

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

        cart = _cart_with_items(cart)
        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data
        )

    def delete(self, request, item_id):
        cart = get_or_create_cart(request)
        cart.items.filter(pk=item_id).delete()
        cart = _cart_with_items(cart)
        return Response(
            CartSerializer(cart, context={"request": request, "lang": request.query_params.get("lang", "it")}).data
        )


class PaymentConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "card_enabled": paypal_enabled(),
            "paypal_enabled": paypal_enabled(),
            "paypal_client_id": getattr(settings, "PAYPAL_CLIENT_ID", ""),
            "paypal_mode": getattr(settings, "PAYPAL_MODE", "sandbox"),
            "currency": settings.SECURWORK_CURRENCY,
            "bank_transfer_enabled": True,
            "bank_details": {
                "iban": getattr(settings, "SECURWORK_BANK_IBAN", "[PLACEHOLDER-IBAN]"),
                "bic": getattr(settings, "SECURWORK_BANK_BIC", "[PLACEHOLDER-BIC]"),
                "account_name": getattr(settings, "SECURWORK_BANK_ACCOUNT_NAME", "SecurWork S.r.l."),
            },
        })


class CheckoutQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payment_method = request.query_params.get("payment_method", "paypal")
        if payment_method not in ("stripe", "paypal", "bank_transfer", "card"):
            payment_method = "paypal"
        fulfillment_type = request.query_params.get("fulfillment_type", "delivery")
        if fulfillment_type not in ("delivery", "pickup"):
            fulfillment_type = "delivery"
        coupon_code = request.query_params.get("coupon_code", "")
        cart = get_or_create_cart(request)
        from .payment_methods import normalize_payment_method

        quote = quote_checkout_from_cart(
            cart,
            coupon_code=coupon_code,
            payment_method=normalize_payment_method(payment_method),
            fulfillment_type=fulfillment_type,
        )
        return Response({
            key: f"{quote[key]:.2f}" if hasattr(quote[key], "quantize") else quote[key]
            for key in quote
        })


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = get_or_create_cart(request)

        try:
            order = create_order_from_cart(
                cart,
                data,
                user=request.user,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = data.get("payment_method", Order.PaymentMethod.PAYPAL)
        checkout_url = None

        if payment_method in (Order.PaymentMethod.PAYPAL, Order.PaymentMethod.CARD) and paypal_enabled():
            try:
                checkout_url = create_paypal_checkout(order)
            except PayPalError as e:
                try:
                    cancel_order(order)
                except Exception:
                    logger.exception(
                        "Failed to cancel order %s after PayPal error",
                        order.order_number,
                    )
                logger.warning(
                    "PayPal checkout failed for order %s: issues=%s",
                    order.order_number,
                    e.issue_codes() or str(e)[:200],
                )
                return Response(
                    {"detail": e.user_message()},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
        elif payment_method in (Order.PaymentMethod.PAYPAL, Order.PaymentMethod.CARD):
            cancel_order(order)
            return Response(
                {"detail": "Selected payment method is not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif payment_method == "bank_transfer":
            send_order_confirmation(order)
            send_order_admin_notification(order)
        else:
            cancel_order(order)
            return Response(
                {"detail": "Unsupported payment method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "order": OrderSerializer(order).data,
            "checkout_url": checkout_url,
            "payment_method": payment_method,
        }, status=status.HTTP_201_CREATED)


class OrderVerifyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_number):
        session_id = request.query_params.get("session_id")
        paypal_token = request.query_params.get("token")
        try:
            order = Order.objects.prefetch_related("items__customization").get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if (
            session_id
            and stripe_enabled()
            and order.payment_status != Order.PaymentStatus.PAID
            and order.payment_method == Order.PaymentMethod.STRIPE
        ):
            try:
                order = verify_stripe_checkout_for_order(order, session_id)
            except (StripeVerificationError, stripe.error.StripeError) as exc:
                logger.warning(
                    "Stripe payment verification failed for order %s: %s",
                    order_number,
                    exc,
                )

        if (
            paypal_token
            and paypal_enabled()
            and order.payment_status != Order.PaymentStatus.PAID
            and order.payment_method in (Order.PaymentMethod.PAYPAL, Order.PaymentMethod.CARD)
            and order.paypal_order_id == paypal_token
        ):
            try:
                order = verify_and_confirm_paypal_order(order, paypal_token)
            except PayPalVerificationError as exc:
                logger.warning(
                    "PayPal payment verification failed for order %s: %s",
                    order_number,
                    exc,
                )
            except PayPalError as exc:
                logger.warning(
                    "PayPal API error during verification for order %s: %s",
                    order_number,
                    exc,
                )

        order.refresh_from_db()
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
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "items", "items__customization"
        )
