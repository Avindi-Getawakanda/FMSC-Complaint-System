# Create your views here.

from django.contrib import messages
from django.shortcuts import render, redirect

from accounts.decorators import role_required
from accounts.models import UserProfile

from .forms import CaseSubmissionForm
from .models import Attachment


@role_required(
    UserProfile.Role.STUDENT,
    UserProfile.Role.LECTURER,
)
def submit_case(request):
    if request.method == "POST":
        form = CaseSubmissionForm(request.POST, request.FILES)

        if form.is_valid():
            case = form.save(commit=False)
            case.submitted_by = request.user
            case.save()

            uploaded_file = form.cleaned_data.get("attachment")

            if uploaded_file:
                Attachment.objects.create(
                    case=case,
                    file=uploaded_file,
                    uploaded_by=request.user
                )

            messages.success(
                request,
                f"Your case {case.case_number} was submitted successfully!"
            )
            return redirect("dashboard")

    else:
        form = CaseSubmissionForm()

    return render(
        request,
        "cases/submit_case.html",
        {"form": form}
    )


