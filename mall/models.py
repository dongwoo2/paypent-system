import logging
from functools import cached_property
from typing import List


from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import UniqueConstraint, QuerySet
from uuid import uuid4

from django.http import Http404
from django.urls import reverse
from accounts.models import User
from mysite import settings
from iamport import Iamport

# 현재 소스파일이 mall/models.py 경로의 파일이니까
# __name__은 "mall.models" 문자열을 표현합니다.
logger = logging.getLogger(__name__)


# 상품에 대한 분류를 저장할 모델
# 하나의 Category는 다수의 Product를 가지는 1:N 관계
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = "상품 분류"


# 한 상품에 대한 정보를 저장하는 모델
class Product(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "a", "정상"
        SOLD_OUT = "s", "품절"
        OBSOLETE = "o", "단종"
        INACTIVE = "i", "비활성화"

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, db_constraint=False
    )
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)  # 빈 상태 허용
    price = models.PositiveIntegerField()  # 0 포함 0 이상
    status = models.CharField(
        choices=Status.choices, default=Status.INACTIVE, max_length=1
    )
    photo = models.ImageField(
        upload_to="mall/product/photo/%Y/%m/%d/",
    )
    # 이 두 필드는 추후에 추가했는데 필수필드 이기에 1회용 디폴트 값 지정이 필요해서
    # 1번 누르고 timezone.now 입력하였음
    created_at = models.DateTimeField(
        auto_now_add=True
    )  # 생성시간 자동으로 지금 만들어주는 필드
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시간 자동으로

    def __str__(self):
        return f"<{self.pk}> {self.name}"

    class Meta:
        verbose_name = verbose_name_plural = "상품"
        # 정렬은 하나의 기준으로 이루어져야 하기 때문에 매번 view단에서 쿼리셋에 정렬 지정하기보단 모델에서 정렬
        ordering = ["-pk"]


class CartProduct(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="cart_product_set",  # user.cart_product_set.all() = CartProduct.objects.filter(user=user) 쿼리셋과 같다.
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_constraint=False,
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ],
    )

    def __str__(self):
        return f"<{self.pk}> {self.product.name} - {self.quantity}"

    # 현재 객체의
    @property  # 메서드를 속성으로 사용할 수 있게 해주는 데코레이터
    # 이거 부를 때 cartproduct.amount 이렇게 부르면 cartproduct에는 price와 quantity가 있을때는 알아서 값이 더 해짐
    def amount(self):
        return self.product.price * self.quantity

    class Meta:
        verbose_name_plural = verbose_name = "장바구니 상품"
        constraints = [
            UniqueConstraint(
                fields=("user", "product"), name="unique_user_product"
            ),  # 여러 필드를 묶어서 unique 제약사항을 줄 수 있음
        ]


class Order(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "주문요청"
        FAILED_PAYMENT = "failed_payment", "결제실패"
        PAID = "paid", "결제완료"
        PREPARED_PRODUCT = "prepared_product", "상품준비중"
        SHIPPED = "shipped", "배송중"
        DELIVERED = "delivered", "배송완료"
        CANCELED = "canceled", "주문취소"

    uid = models.UUIDField(default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_constraint=False,
    )
    total_amount = models.PositiveIntegerField("결제금액")
    status = models.CharField(
        "진행상태",
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    product_set = models.ManyToManyField(
        Product,
        through="OrderedProduct",
        blank=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 반환값의 타입은 Order입니다. 반환값 타입 지정하는 코드 부분은 Order 클래스 정의가 마무리되기 전에 수행되므로
    # 문자열 Order로 반환

    # self.product_set.all() 쿼리셋은 현 주문의 상품목록입니다.
    # 덧: self.orderedproduct_set.all()이 더 적합합니다.

    def get_absolute_url(self) -> str:
        return reverse("order_detail", args=[self.pk])

    # status 필드가 REQUESTED, FAILED_PAYMENT 일 때 에만 결제를 허용
    def can_pay(self) -> bool:
        return self.status in (self.Status.REQUESTED, self.Status.FAILED_PAYMENT)

    @property
    def name(self):
        first_product = self.product_set.first()  # 현 주문의 상품 중에 첫 번째 상품
        # 쿼리셋.first() 첫 번째 상품이 없으면
        if first_product is None:
            return "등록된 상품이 없습니다."
        size = self.product_set.all().count()  # 전체 갯수
        if size < 2:  # 1건일 때
            return first_product.name
        return f"{first_product.name} 외 {size-1} 건"

    @classmethod
    def create_from_cart(
        cls, user: User, cart_product_qs: QuerySet[CartProduct]
    ) -> "Order":  # 반환값은 Order
        cart_product_list: List[CartProduct] = list(cart_product_qs)
        # total amount의 경우에는 cart_product_qs를 다 돌아야함
        total_amount = sum(cart_product.amount for cart_product in cart_product_list)
        # cls는 order 클래스를 뜻함
        order = cls.objects.create(
            user=user, total_amount=total_amount
        )  # order 클래스 새로 생성

        ordered_product_list = []
        for cart_product in cart_product_list:  # 새로운 OrderedProduct 객체를 만들거임
            product = cart_product.product
            ordered_product = OrderedProduct(
                order=order,
                product=product,
                name=product.name,
                price=product.price,
                quantity=cart_product.quantity,
            )
            ordered_product_list.append(ordered_product)

        OrderedProduct.objects.bulk_create(ordered_product_list)

        return order

    class Meta:
        ordering = ["-pk"]


class OrderedProduct(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_constraint=False,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_constraint=False,
    )
    name = models.CharField(
        "상품명", max_length=100, help_text="주문 시점의 상품명을 저장합니다."
    )
    price = models.PositiveIntegerField(
        "상품가격", help_text="주문 시점의 상품가격을 저장합니다."
    )
    quantity = models.PositiveIntegerField("수량")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# abstract 클래스는 마이그레이션시에 테이블을 생성하지 않습니다.
# 단지 상속하기 위한 목적으로만 사용됩니다.


# 포트원 결제를 적용할 모델에서는 AbstractPortonePayment를 상속만 받으면
# 포트원 결제가 지원되도록 구현
class AbstractPortonePayment(models.Model):

    class PayMethod(models.TextChoices):
        CARD = "card", "신용카드"

    # 포트원 선택지로만 상태값 구성
    class PayStatus(models.TextChoices):
        READY = "ready", "결제 준비"
        PAID = "paid", "결제 완료"
        CANCELED = "canceled", "결제 취소"
        FAILED = "failed", "결제 실패"

    # 포트원 결제 새부 내역을 meta 필드로 저장
    # models.JSONField는 리스트, 사전 자료구조 뿐만 아니라 복잡한 형태의 JSON 데이터를 저장할 수 있습니다.
    meta = models.JSONField("포트원 결제내역", default=dict, editable=False)
    # 결제 식별자 필드
    uid = models.UUIDField("쇼핑몰 결제내역", default=uuid4, editable=False)
    # 결제명
    name = models.CharField("결제명", max_length=200)
    # 결제 금액
    desired_amount = models.PositiveIntegerField("결제 금액", editable=False)
    # 구매자 이름
    buyer_name = models.CharField("구매자 이름", max_length=100, editable=False)
    # 구매자 이메일
    buyer_email = models.EmailField("구매자 이메일", editable=False)

    # choices 인자로는 PayMethod.choices를 지정하고 default 인자로는 PayMethod.CARD를 지정합니다.
    pay_method = models.CharField(
        "결제수단", max_length=20, choices=PayMethod.choices, default=PayMethod.CARD
    )
    pay_status = models.CharField(
        "결제상태", max_length=20, choices=PayStatus.choices, default=PayStatus.READY
    )
    # 완벽한 결제성공은 status=PAID 이면서, 결제 요청금액이 실 결제 금액과 정확히 일치할 때, 결제 성공이라고
    # 판단해야만 합니다. ( 해킹의 위협 때문에 )
    is_paid_ok = models.BooleanField(
        "결제성공 여부", default=False, db_index=True, editable=False
    )

    @property
    def merchant_uid(self) -> str:
        # 이렇게 str 변환을 하면 하이픈(-)이 포함된 uuid 문자열이 됩니다.
        return str(self.uid)

    # meta 내역을 갱신하고, pay_status 필드와 is_paid_ok 필드에 반영하는 메서드 구현이 필요 update 구현

    # 그냥 property만 이용하면 호출될 때 마다 iamport 인스턴스를 계속 만드는데
    # cached_property를 이용하면 self.api 속성 두번 째 접근부터는 메서드가 호출되지 않고, 캐싱된 iamport 인스턴스를 활용합니다.
    @cached_property
    def api(self):
        return Iamport(
            imp_key=settings.PORTONE_API_KEY, imp_secret=settings.PORTONE_API_SECRET
        )

    def update(self):
        # self.api.find를 통해 결제내역 조회
        # 반환값을 결제 세부내역을 받으니, self.meta 필드에 반영합니다.
        # iamport-rest-client를 활용한 API 호출시에 2개의 예외가 발생할 수 있는데
        try:
            self.meta = self.api.find(merchant_uid=self.merchant_uid)
        except (Iamport.ResponseError, Iamport.HttpError) as e:
            # 예외가 발생하면 예외를 잡아서 에러메세지와 예외정보를 지정하고,
            # Http404 에러를 발생시키겠습니다.
            logger.error(str(e), exc_info=e)
            raise Http404("포트원에서 결제내역을 찾을 수 없습니다.")
        # self.meta에 결제 세부내역이 저장되어있다
        # 왜 저장되어있는거지?
        self.pay_status = self.meta[
            "status"
        ]  # 예외가 발생하지 않는다면 이 값을 그대로 반영

        # Iamport 인스턴스에 is_paid 메서드를 지원하고 있습니다.
        # API 호출하지 않고 결제완료 여부를 판단해줌
        self.is_paid_ok = self.api.is_paid(self.desired_amount, response=self.meta)

    class Meta:
        abstract = True


# 하나의 주문의 여러번의 결제시도가 있을 수 있다
# 하나의 결제시도를 OrderPayMent와 Order와 묶겠다
# 결제시도와 묶은것임
class OrderPayment(AbstractPortonePayment):  # 상속 받았음
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_constraint=False)

    def update(self):
        super().update()
        if self.is_paid_ok:  # 완료라면
            self.order.status = Order.Status.PAID
            self.order.save()
            # 다수의 결제시도
            self.order.orderpayment_set.exclude(pk=self.pk).delete()
        elif self.pay_status in (
            self.PayStatus.CANCELED,
            self.PayStatus.FAILED,
        ):  # 두 가지 상태중 하나일 때
            self.order.status = Order.Status.FAILED_PAYMENT
            self.order.save()

    # order 인자로부터 OrderPayment를 생성해서 반환하겠습니다.
    @classmethod
    def create_by_order(cls, order: Order) -> "OrderPayment":
        # cls.objects.create를 통해 OrderPayment인스턴스를 즉시 생성
        return cls.objects.create(
            order=order,
            name=order.name,  # 결제명을 order.name에서 가져온다
            desired_amount=order.total_amount,
            # get_full_name()이 빈 문자열일 때 username 값을 지정해보실 수도 있습니다.
            buyer_name=order.user.get_full_name() or order.user.username,
            buyer_email=order.user.email,
        )
