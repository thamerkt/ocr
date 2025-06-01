from django.urls import path
from .views import verify_company,validate_and_extract_image_data,verify_face,verify_identity,generate_qr,liveness_detection_view,DocumentTypeViewSet,DocumentViewSet,publish_identity_verification_event,verify_data,_verifyy,get_ip
from . import views
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'documenttype', DocumentTypeViewSet, basename='documenttype')
router.register(r'document', DocumentViewSet, basename='document')

urlpatterns = [
    path('upload-image/', validate_and_extract_image_data, name='upload_image'),
    path('verify-data/',_verifyy,name="verify_data"),
    path('publish-event/', publish_identity_verification_event, name='publish-event'),
    path('verify-face/', verify_face, name='verify-face'),
    path('verify/', verify_identity, name='chatbot_response'),
    path('selfie/',liveness_detection_view ,name='livensss'),
    path('generate-qr/', generate_qr, name='generate_qr'),
    path('getipp/', get_ip, name='get_ip'),
    path('verification/start/', views.start_verification, name='start_verification'),
    path('verification/company/', views.verify_company, name='start_verification'),
    path('/verification/<uuid:verification_id>/upload/', views.upload_documents, name='upload_documents'),
    path('/verification/verify/<uuid:verification_id>/<str:secret_code>/', views.verify_qr_code, name='verify_qr_code'),
    path('/verification/<uuid:verification_id>/status/', views.check_status, name='check_status'),
    path('/verification/admin/<uuid:verification_id>/update/', views.admin_update_status, name='admin_update_status')
]
urlpatterns += router.urls