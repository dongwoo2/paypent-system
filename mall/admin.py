from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["pk", "name"]
    list_display_links = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ["name"]  # 검색바, 다수로 지정하면 쿼리 셀렉문에 or로 들어감
    list_display = ["category", "name", "price", "status"]
    list_display_links = ["name"]
    list_filter = ["category", "status", "created_at", "updated_at"]
    date_hierarchy = "updated_at"
    actions = ["make_active"]

    @admin.display(
        description=f"지정 상품을 {Product.Status.ACTIVE.label} 상태로 변경합니다."
    )
    def make_active(self, request, queryset):
        count = queryset.update(  # count는 적용된 행의 개수
            status=Product.Status.ACTIVE
        )  # 이렇게 하면 뭉탱이로 한 번에 날아감
        self.message_user(
            request,
            f"{count}개의 상품을 {Product.Status.ACTIVE.label} 상태로 변경했습니다. ",
        )  # messages 더 편학게 쓸 수 있게 해주는거

        """
        for product in queryset:  # 이렇게 하면 쿼리셋이 하나하나 날라가서 느림
            product.status = Product.Status.ACTIVE
            product.save()
        """
