# kaisenapp/urls.py

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views as core_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 管理画面
    path('admin/', admin.site.urls),

    # 認証（ログイン・ログアウト）
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # ホーム画面（トップページ）
    path('', core_views.home, name='home'),

    # 「/projects/」以下のルートを core.urls に委譲
    path('projects/', include('core.urls')),

    # core アプリ内のその他のルート
    path('core/', include('core.urls')),  


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)