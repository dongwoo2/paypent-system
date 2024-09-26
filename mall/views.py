from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from mysite import settings
from mall.forms import CartProductForm
from mall.models import Product, CartProduct, Order, OrderPayment

# Create your views here.


"""
def product_list(request):
    product_qs = Product.objects.all().select_related(
        "category"
    )  # join 걸어서 category도 가져와야 n+1 문제가 발생하지 않음
    return render(
        request,
        "mall/product_list.html",
        {"product_list": product_qs},
    )
"""


class ProductListView(ListView):  # ListView 페이징 처리가 기본으로 적용되어 있음
    # 템플릿 경로 mall/product_list.html은 ProductListView 설정을 통해 디폴트로 찾아서 생략
    # context_data 이름인 product_list도 모델명소문자_list로서 디폴트로 지정되서 생략
    model = Product
    queryset = Product.objects.filter(status=Product.Status.ACTIVE).select_related(
        "category"
    )  # 정적
    paginate_by = 4

    def get_queryset(self):  # 동적으로 검색어 쿼리셋
        qs = super().get_queryset()
        # 클래스 기반 뷰에서는 self.request가 현재 요청 객체입니다. HttRequest 타입입니다.
        query = self.request.GET.get(
            "query", ""
        )  # 있으면 query 값 가져오고 없으면 빈 문자열 가져오기
        # 프로덕트의 name이라는 컬럼에서 대소문자를 무시하고 (ignore)검색어가 포함된 Product만을 조회합니다.
        if query:
            qs = qs.filter(name__icontains=query)
        return qs


product_list = ProductListView.as_view()


@login_required
def cart_detail(request):
    cart_product_qs = (
        CartProduct.objects.filter(
            user=request.user,
        )
        .select_related("product")
        .order_by("product__name")
    )  # 프로덕트가 외래키 묶여져 있어서 나중에 템플릿에서 참조해서 가져오기에 미리 참조시키기 미리 조인되서 쿼리 갯수가 줄어듬

    # 하나의 요청에서 다수의 인스턴스를 생성/수정하는 것은 formset 기능을 활용할 수 있다.
    CartProductFormSet = modelformset_factory(  # 폼셋 클래스 생성
        model=CartProduct,
        form=CartProductForm,
        can_delete=True,
        extra=0,  # 이거 안하면 인스턴스가 추가 되어서 템플릿에서 빈 인스턴스가 추가되어서 보임
    )

    if request.method == "POST":
        formset = CartProductFormSet(
            data=request.POST,
            queryset=cart_product_qs,
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, "장바구니를 업데이트했습니다.")
            return redirect("mall:cart_detail")
    else:
        formset = CartProductFormSet(
            queryset=cart_product_qs,
        )

    return render(
        request,
        "mall/cart_detail.html",
        {
            "formset": formset,
        },
    )


@login_required
@require_POST  # 포스트 요청일때만 add_to_cart 뷰가 호출됨
def add_to_cart(request, product_pk):
    # get_object_or_404의 특징은 첫 번 째 인자를 모델로 해도되고, 쿼리셋으로 해도됨
    """
    product_qs = Product.objects.all()
    product = get_object_or_404(product_qs, pk=product_pk)
    product = get_object_or_404(Product, pk=product_pk)
    둘이 같음
    """
    product_qs = Product.objects.filter(  # ACTIVE 상태의 물건만 장바구니에 담을 수 있게
        status=Product.Status.ACTIVE,
    )
    product = get_object_or_404(product_qs, pk=product_pk)

    quantity = int(
        request.GET.get("quantity", 1)
    )  # 담을 수량은 쿼리스트링의 quantity 인자로 받고, 없다면 1로 지정합니다.

    # 반환값으로 튜플을 받고, 첫 번째 값으로 CartProduct 인스턴스, 두번 째 값으로 생성여부를 받습니다.
    cart_product, is_created = CartProduct.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity},
    )

    # 새로 생성이 아닐시에는 담은 수만큼 수량 증가
    if not is_created:
        cart_product.quantity += quantity
        cart_product.save()

    messages.success(request, "장바구니에 추가했습니다.")

    #   redirect_url = request.META.get("HTTP_REFERER", "product_list")

    #  return redirect(redirect_url)  # 장바구니에 담은 후에는 상품목록 페이지로 이동

    return HttpResponse("ok")


# Pagination 처리가 필요하다면 ListView를 사용.
@login_required
def order_list(request):
    order_qs = Order.objects.all().filter(user=request.user, status=Order.Status.PAID)
    return render(
        request,
        "mall/order_list.html",
        {
            "order_list": order_qs,
        },
    )


@login_required
def order_new(request):
    # 현재 유저의 장바구니 내역은 밑에 쿼리를 통해 조회할 수 있다.
    cart_product_qs = CartProduct.objects.filter(user=request.user)

    order = Order.create_from_cart(request.user, cart_product_qs)
    cart_product_qs.delete()

    return redirect("mall:order_pay", order.pk)


@login_required
def order_pay(request, pk):
    order = get_object_or_404(
        Order, pk=pk, user=request.user
    )  # 해댱 유저만 접근을 해야하니까
    # 결제를 할려면 지금 현재 결제건이 결제가 가능한 상황인지 판단이 필요합니다.
    # 판단 로직을 view에서 구현하지 않고, 비즈니스 로직이니 Model에서 cam_pay 메서드로 몰아서 구현해주겠습니다.
    # order.status가 주문요청(REQUESTED)이나 결제실패(FAILED_PAYMENT)일 때 에만 결제를 허용하고 싶다.
    if not order.can_pay():  # 결제가 안되는 상황이라면
        messages.error(request, "현재 결제를 할 수 없는 주문입니다.")
        return redirect(order)

    # 결제진행을 위해 order 인스턴스로부터 OrderPayment 인스턴스를 생성합니다.

    # order 기반에서 새로운 결제시도에 대한 OrderPayment 모델 인스턴스를 생성합니다.

    # order_pay 뷰가 호출될 때마다 , 매번 새로운 OrderPayment 인스턴스를 생성
    payment = OrderPayment.create_by_order(order)

    # 포트원 IMP.request_pay API를 호출 시에 전달할 인자들을 payment_props 사전에 정의하겠습니다.
    payment_props = {
        "pg": settings.PORTONE_PG,
        "merchant_uid": payment.merchant_uid,
        "name": payment.name,
        "amount": payment.desired_amount,
        "buyer_name": payment.buyer_name,
        "buyer_email": payment.buyer_email,
    }

    return render(
        request,
        "mall/order_pay.html",
        {
            # IMP.request_pay 결제에서 payment_props 외에도 포트원 가맹점 아이디가 필요합니다.
            "portone_shop_id": settings.PORTONE_SHOP_ID,
            "payment_props": payment_props,
            # 포트원 IMP.request_pay 자바스크립트 API를 호출할 때
            # 두 번째 인자로 지정한 콜백함수에서 페이지 이동 시에 사용할 결제검증 페이지 주소도 같이 지정
            "next_url": reverse("mall:order_check", args=[order.pk, payment.pk]),
        },
    )


# 아래에 결제를 검증할 order_check 뷰를 추가하고 인자로 order_pk를 받도록 합니다.
# order_check 뷰에서는 check가 아니라 payment에 대한 검증이 필요합니다.
# 그래서 찾는 대상은 Order가 아닌 OrderPayment를 찾아야하기에 pk=payment_pk를 지정합니다.
@login_required
def order_check(request, order_pk, payment_pk):
    # order__pk 대신에 order__user = request.user가 원래 의도에 맞습니다.
    payment = get_object_or_404(OrderPayment, pk=payment_pk, order__pk=order_pk)
    payment.update()
    # return redirect(payment.order)
    return redirect("mall:order_detail", order_pk)


@login_required
def order_detail(request, pk):
    # 로그인 유저만이 본인의 주문만 볼 수 있도록 조건 걸기
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(
        request,
        "mall/order_detail.html",
        {
            "order": order,
        },
    )
