from django.db import models
from django.utils import timezone



class IdentityVerification(models.Model):
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    DOCUMENT_TYPES = (
        ('passport', 'Passport'),
        ('id_card', 'National ID Card'),
        ('driving_license', 'Driving License'),
    )
    
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, null=True)
    document_number = models.CharField(max_length=50, null=True)
    document_front = models.ImageField(upload_to='verification_documents/', null=True)
    document_back = models.ImageField(upload_to='verification_documents/', null=True, blank=True)
    selfie = models.ImageField(upload_to='verification_selfies/', null=True)
    secret_code = models.CharField(max_length=100)
    status = models.CharField(max_length=12, choices=VERIFICATION_STATUS, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    rejection_reason = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Verification {self.id} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)

class DocumentType(models.Model):
    name = models.CharField(max_length=255)
    file_format = models.CharField(max_length=255)
    mandatory = models.BooleanField(default=False)  
    required_for = models.IntegerField()

    def __str__(self):
        return self.name

class Document(models.Model):
    document_name = models.CharField(max_length=255)
    document_url = models.ImageField(max_length=255)  
    status = models.CharField(max_length=255)
    uploaded_by = models.CharField(max_length=255)
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name="documents", null=True, blank=True)
    submission_date = models.DateTimeField(null=True, blank=True)  # Ajout de null=True, blank=True
    verification_date = models.DateTimeField(null=True, blank=True)  # Ajout de null=True, blank=True

    def __str__(self):
        return self.document_name