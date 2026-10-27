# Create your views here.

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import role_required
from accounts.models import UserProfile

from .forms import CaseSubmissionForm
from .models import Attachment, Case


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

@role_required(
    UserProfile.Role.STUDENT,
    UserProfile.Role.LECTURER,
)
def my_cases(request):
    cases = (
        Case.objects
        .filter(submitted_by=request.user)
        .select_related("category")
        .order_by("-created_at")
    )

    return render(
        request,
        "cases/my_cases.html",
        {"cases": cases}
    )



@role_required(
    UserProfile.Role.STUDENT,
    UserProfile.Role.LECTURER,
)
def case_detail(request, case_id):
    case = get_object_or_404(
        Case.objects.select_related("category", "assigned_authority"),
        pk=case_id,
        submitted_by=request.user,
    )

    activity_history = (
        case.audit_logs
        .select_related("actor")
        .order_by("created_at")
    )

    attachments = case.attachments.all()

    return render(
        request,
        "cases/case_detail.html",
        {
            "case": case,
            "activity_history": activity_history,
            "attachments": attachments,
        },
    )




