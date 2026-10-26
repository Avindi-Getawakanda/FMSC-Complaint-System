from django.contrib import admin
from .models import Authority, ProgressUpdate

admin.site.register([Authority, ProgressUpdate])