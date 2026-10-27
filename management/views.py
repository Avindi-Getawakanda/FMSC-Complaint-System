import json

from django.contrib import messages
from accounts.decorators import role_required
from accounts.models import UserProfile
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cases.models import AuditLog, Case
from .forms import CaseAssignmentForm


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def case_list(request):
    cases = Case.objects.select_related(
        "category",
        "submitted_by",
        "assigned_authority",
    ).order_by("-created_at")

    return render(
        request,
        "management/case_list.html",
        {"cases": cases},
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def case_detail(request, pk):
    case = get_object_or_404(
        Case.objects.select_related(
            "category",
            "submitted_by",
            "assigned_authority",
        ),
        pk=pk,
    )

    return render(
        request,
        "management/case_detail.html",
        {"case": case},
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@transaction.atomic
def case_assign(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
    )

    allowed_statuses = {
        Case.Status.SUBMITTED,
        Case.Status.UNDER_REVIEW,
        Case.Status.NOT_STARTED,
        Case.Status.ASSIGNED,
        Case.Status.REOPENED,
    }

    # Keep the original values before validating the form.
    old_values = {
        "category_id": case.category_id,
        "priority": case.priority,
        "authority_id": case.assigned_authority_id,
        "status": case.status,
    }

    if request.method == "POST":
        form = CaseAssignmentForm(request.POST, instance=case)

        if form.is_valid():
            if old_values["status"] not in allowed_statuses:
                form.add_error(
                    None,
                    "This case cannot be assigned in its current status.",
                )
            else:
                updated_case = form.save(commit=False)
                updated_case.status = Case.Status.ASSIGNED
                updated_case.save()

                new_values = {
                    "category_id": updated_case.category_id,
                    "priority": updated_case.priority,
                    "authority_id": updated_case.assigned_authority_id,
                    "status": updated_case.status,
                }

                AuditLog.objects.create(
                    case=updated_case,
                    actor=request.user,
                    action="Case reviewed and assigned",
                    old_value=json.dumps(old_values),
                    new_value=json.dumps(new_values),
                )

                messages.success(
                    request,
                    "Case assigned successfully.",
                )

                return redirect(
                    "management:case_detail",
                    pk=updated_case.pk,
                )
    else:
        form = CaseAssignmentForm(instance=case)

    return render(
        request,
        "management/case_assign.html",
        {"case": case, "form": form},
    )