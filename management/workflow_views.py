import json

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import UserProfile
from cases.models import AuditLog, Case

from .models import Authority, ProgressUpdate


class CaseReassignmentForm(forms.Form):
    authority = forms.ModelChoiceField(
        label="New responsible authority",
        queryset=Authority.objects.none(),
        empty_label="Select an authority",
    )

    reason = forms.CharField(
        label="Reason for reassignment",
        required=True,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Explain why responsibility is being transferred."
                ),
            }
        ),
    )

    def __init__(self, *args, case, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["authority"].queryset = (
            Authority.objects.filter(
                is_active=True
            ).exclude(
                pk=case.assigned_authority_id
            ).order_by("name")
        )


class CaseReopenForm(forms.Form):
    reason = forms.CharField(
        label="Reason for reopening",
        required=True,
        strip=True,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Explain why the previous resolution "
                    "was unsatisfactory or the issue has returned."
                ),
            }
        ),
        error_messages={
            "required": "Please provide a reason for reopening.",
        },
    )


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@require_POST
@transaction.atomic
def case_mark_under_review(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
    )

    if case.status != Case.Status.SUBMITTED:
        messages.error(
            request,
            "Only a submitted case can be marked under review.",
        )

        return redirect(
            "management:case_detail",
            pk=case.pk,
        )

    old_status = case.status
    case.status = Case.Status.UNDER_REVIEW
    case.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        case=case,
        actor=request.user,
        action="Case marked under review",
        old_value=json.dumps({
            "status": old_status,
        }),
        new_value=json.dumps({
            "status": case.status,
        }),
    )

    messages.success(
        request,
        "Case marked under review.",
    )

    return redirect(
        "management:case_detail",
        pk=case.pk,
    )


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@transaction.atomic
def case_reassign(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
    )

    allowed_statuses = {
        Case.Status.ASSIGNED,
        Case.Status.NOT_STARTED,
        Case.Status.IN_PROGRESS,
        Case.Status.WAITING_INFO,
        Case.Status.REOPENED,
    }

    can_reassign = (
        case.assigned_authority_id is not None
        and case.status in allowed_statuses
    )

    if request.method == "POST":
        form = CaseReassignmentForm(
            request.POST,
            case=case,
        )

        if form.is_valid():
            if not can_reassign:
                form.add_error(
                    None,
                    "This case cannot be reassigned in its current state.",
                )
            else:
                old_authority = case.assigned_authority
                new_authority = form.cleaned_data["authority"]
                reason = form.cleaned_data["reason"]

                case.assigned_authority = new_authority
                case.save(
                    update_fields=[
                        "assigned_authority",
                        "updated_at",
                    ]
                )

                ProgressUpdate.objects.create(
                    case=case,
                    status=case.status,
                    updated_by=request.user,
                    comment=(
                        f"Responsibility transferred from "
                        f"{old_authority.name} to {new_authority.name}.\n"
                        f"Reason: {reason}"
                    ),
                )

                AuditLog.objects.create(
                    case=case,
                    actor=request.user,
                    action="Case reassigned",
                    old_value=json.dumps({
                        "authority_id": old_authority.pk,
                        "status": case.status,
                    }),
                    new_value=json.dumps({
                        "authority_id": new_authority.pk,
                        "status": case.status,
                        "reason": reason,
                    }),
                )

                messages.success(
                    request,
                    "Case reassigned successfully.",
                )

                return redirect(
                    "management:case_detail",
                    pk=case.pk,
                )
    else:
        form = CaseReassignmentForm(case=case)

    return render(
        request,
        "management/case_reassign.html",
        {
            "case": case,
            "form": form,
            "can_reassign": can_reassign,
        },
    )


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@transaction.atomic
def case_reopen(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
    )

    can_reopen = case.status in {
        Case.Status.SOLVED,
        Case.Status.CLOSED,
    }

    if request.method == "POST":
        form = CaseReopenForm(request.POST)

        if form.is_valid():
            if not can_reopen:
                form.add_error(
                    None,
                    "Only solved or closed cases can be reopened.",
                )
            else:
                reason = form.cleaned_data["reason"]

                old_values = {
                    "status": case.status,
                    "authority_id": case.assigned_authority_id,
                    "resolution_note": case.resolution_note,
                    "solved_at": (
                        case.solved_at.isoformat()
                        if case.solved_at
                        else None
                    ),
                    "closed_at": (
                        case.closed_at.isoformat()
                        if case.closed_at
                        else None
                    ),
                }

                # Keep an existing active authority responsible.
                # Otherwise, the administrator must assign one.
                if case.assigned_authority_id:
                    if not case.assigned_authority.is_active:
                        case.assigned_authority = None

                case.status = Case.Status.REOPENED
                case.resolution_note = ""
                case.solved_at = None
                case.closed_at = None

                case.save(
                    update_fields=[
                        "status",
                        "assigned_authority",
                        "resolution_note",
                        "solved_at",
                        "closed_at",
                        "updated_at",
                    ]
                )

                ProgressUpdate.objects.create(
                    case=case,
                    status=Case.Status.REOPENED,
                    comment=f"Case reopened.\nReason: {reason}",
                    updated_by=request.user,
                )

                AuditLog.objects.create(
                    case=case,
                    actor=request.user,
                    action="Case reopened",
                    old_value=json.dumps(old_values),
                    new_value=json.dumps({
                        "status": case.status,
                        "authority_id": case.assigned_authority_id,
                        "reason": reason,
                        "resolution_note": "",
                        "solved_at": None,
                        "closed_at": None,
                    }),
                )

                messages.success(
                    request,
                    "Case reopened successfully.",
                )

                return redirect(
                    "management:case_detail",
                    pk=case.pk,
                )
    else:
        form = CaseReopenForm()

    return render(
        request,
        "management/case_reopen.html",
        {
            "case": case,
            "form": form,
            "can_reopen": can_reopen,
        },
    )