import logging
from uuid import uuid4

from django.core.validators import MinValueValidator
from django.db import models
from django.http import Http404
from iamport import Iamport


logger = logging.getLogger("portone")
# from iamport import Iamport

from mysite import settings


# Create your models here.
class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        READY = "ready", "미결제"
        PAID = "paid", "결제완료"
        CANCELLED = "cancelled", "결제취소"
        FAILED = "failed", "결제실패"

    uid = models.UUIDField(default=uuid4, editable=False)
    name = models.CharField(max_length=100)
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, message="1원 이상의 금액을 지정해주세요."),
        ]
    )
    # ready, paid, cancelled, failed
    status = models.CharField(
        max_length=9,
        default=StatusChoices.READY,
        choices=StatusChoices.choices,
        db_index=True,
    )
    is_paid_ok = models.BooleanField(
        default=False, db_index=True
    )  # 정말로 결제가 성공했는지

    @property
    def merchant_uid(self) -> str:
        return self.uid.hex

    # commit true는 필드를 변경하고, commit 참/거짓에 따라 self.save()
    # 호출 여부를 조절하고 싶을 목적으로 사용

    def portone_check(self, commit=True):  # 결제 내역 검증 로직 view에서는 호출만 할 것
        api = Iamport(
            imp_key=settings.PORTONE_API_KEY, imp_secret=settings.PORTONE_API_SECRET
        )
        try:
            meta = api.find(merchant_uid=self.merchant_uid)
        except (
            Iamport.ResponseError,
            Iamport.HttpError,
        ) as e:  # iamport 라이브러리에 이 두개의 커스텀 예외가 있고
            logger.error(str(e), exc_info=e)  # 로거를 보게하고
            raise Http404(
                str(e)
            )  # 500에러 보다는 우리서버의 오류니까 404에러로 보게 만들기
        # 필드 변경 하는 애들
        self.status = meta["status"]  # 상태값
        self.is_paid_ok = (
            meta["status"] == "paid" and meta["amount"] == self.amount
        )  # 실 결제금액이 요청한 결제금액과 같아야함
        # 계속 save하기보다는 몰아서 save하고 싶을 때 이렇게 사용 commit이 참일 때만
        if commit:
            self.save()
