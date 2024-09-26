from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from . import settings
from django.conf.urls.static import static
from django.shortcuts import render


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("mall_test/", include("mall_test.urls")),
    path("mall/", include("mall.urls")),
    path("", TemplateView.as_view(template_name="root.html"), name="root"),
]

if settings.DEBUG:  # 디버그 모드일 때만
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
