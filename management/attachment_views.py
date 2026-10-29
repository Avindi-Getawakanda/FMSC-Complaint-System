from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from accounts.models import UserProfile
from cases.models import Attachment, Case


def accessible_cases(user):
    if user.is_superuser:
        return Case.objects.all()
    role = UserProfile.objects.filter(user=user).values_list("role", flat=True).first()
    if role in {UserProfile.Role.ADMINISTRATOR, UserProfile.Role.SYSTEM_ADMIN, UserProfile.Role.MANAGEMENT}:
        return Case.objects.all()
    allowed = Q(submitted_by=user)
    if role == UserProfile.Role.AUTHORITY:
        allowed |= Q(assigned_authority__user=user, assigned_authority__is_active=True)
    return Case.objects.filter(allowed)


@login_required(login_url="login")
def submission_attachment_download(request, pk):
    attachment = get_object_or_404(Attachment.objects.filter(
        case__in=accessible_cases(request.user)
    ), pk=pk)
    if not attachment.file:
        raise Http404("No attachment is available.")
    try:
        stream = attachment.file.open("rb")
    except FileNotFoundError:
        raise Http404("The attachment file could not be found.")
    response = FileResponse(stream, as_attachment=True,
        filename=Path(attachment.file.name).name,
        content_type="application/octet-stream")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response