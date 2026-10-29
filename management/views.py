import json
import csv

from django.core.paginator import Paginator
from django.http import HttpResponse

from django.contrib import messages
from accounts.decorators import role_required
from accounts.models import UserProfile
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cases.models import AuditLog, Case
from .forms import CaseAssignmentForm , CaseRejectionForm
from .forms import (
    AuthorityForm,
    CaseAssignmentForm,
    CaseRejectionForm,
    CaseResolutionForm,
    ProgressUpdateForm,
    CaseClosureForm,
    CaseReportFilterForm
)
from .models import Authority, ProgressUpdate

from pathlib import Path

from django.http import FileResponse, Http404
from django.utils import timezone

from django.db.models import Count, Q

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

    progress_updates = case.progress_updates.select_related(
        "updated_by"
    ).order_by("created_at", "pk")

    audit_logs = case.audit_logs.select_related(
        "actor"
    ).order_by("created_at", "pk")

    return render(
        request,
        "management/case_detail.html",
        {
            "case": case,
            "progress_updates": progress_updates,
            "audit_logs": audit_logs,
        },
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

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@transaction.atomic
def case_reject(request, pk):
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

    old_values = {
        "status": case.status,
        "rejection_reason": case.rejection_reason,
        "authority_id": case.assigned_authority_id,
    }

    if request.method == "POST":
        form = CaseRejectionForm(request.POST, instance=case)

        if form.is_valid():
            if old_values["status"] not in allowed_statuses:
                form.add_error(
                    None,
                    "This case cannot be rejected in its current status.",
                )
            else:
                updated_case = form.save(commit=False)
                updated_case.status = Case.Status.REJECTED
                updated_case.assigned_authority = None
                updated_case.save()

                new_values = {
                    "status": updated_case.status,
                    "rejection_reason": updated_case.rejection_reason,
                    "authority_id": updated_case.assigned_authority_id,
                }

                AuditLog.objects.create(
                    case=updated_case,
                    actor=request.user,
                    action="Case rejected",
                    old_value=json.dumps(old_values),
                    new_value=json.dumps(new_values),
                )

                messages.success(request, "Case rejected successfully.")

                return redirect(
                    "management:case_detail",
                    pk=updated_case.pk,
                )
    else:
        form = CaseRejectionForm(instance=case)

    return render(
        request,
        "management/case_reject.html",
        {"case": case, "form": form},
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
def authority_list(request):
    authorities = Authority.objects.select_related("user").order_by("name")

    return render(
        request,
        "management/authority_list.html",
        {"authorities": authorities},
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
def authority_create(request):
    if request.method == "POST":
        form = AuthorityForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Authority added successfully.",
            )

            return redirect("management:authority_list")
    else:
        form = AuthorityForm()

    return render(
        request,
        "management/authority_form.html",
        {"form": form},
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
def authority_edit(request, pk):
    authority = get_object_or_404(Authority, pk=pk)

    if request.method == "POST":
        form = AuthorityForm(request.POST, instance=authority)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Authority updated successfully.",
            )

            return redirect("management:authority_list")
    else:
        form = AuthorityForm(instance=authority)

    return render(
        request,
        "management/authority_form.html",
        {
            "form": form,
            "authority": authority,
        },
    )

@role_required(UserProfile.Role.AUTHORITY)
def assigned_case_list(request):
    authority = Authority.objects.filter(
        user=request.user,
        is_active=True,
    ).first()

    cases = Case.objects.none()

    if authority:
        cases = Case.objects.filter(
            assigned_authority=authority,
        ).select_related(
            "category",
            "submitted_by",
            "assigned_authority",
        ).order_by("-created_at")

    return render(
        request,
        "management/assigned_case_list.html",
        {
            "authority": authority,
            "cases": cases,
        },
    )

@role_required(UserProfile.Role.AUTHORITY)
def assigned_case_detail(request, pk):
    case = get_object_or_404(
        Case.objects.select_related(
            "category",
            "submitted_by",
            "assigned_authority",
        ),
        pk=pk,
        assigned_authority__user=request.user,
        assigned_authority__is_active=True,
    )

    progress_updates = case.progress_updates.select_related(
        "updated_by"
    ).order_by("created_at")

    return render(
        request,
        "management/assigned_case_detail.html",
        {
            "case": case,
            "progress_updates": progress_updates,
        },
    )
@role_required(UserProfile.Role.AUTHORITY)
@transaction.atomic
def case_progress_update(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
        assigned_authority__user=request.user,
        assigned_authority__is_active=True,
    )

    if request.method == "POST":
        form = ProgressUpdateForm(
            request.POST,
            request.FILES,
            case=case,
        )

        if form.is_valid():
            old_status = case.status
            new_status = form.cleaned_data["status"]

            progress = ProgressUpdate.objects.create(
                case=case,
                comment=form.cleaned_data["comment"],
                status=new_status,
                updated_by=request.user,
                evidence=form.cleaned_data.get("evidence"),
            )

            case.status = new_status
            case.save(update_fields=["status", "updated_at"])

            AuditLog.objects.create(
                case=case,
                actor=request.user,
                action="Case progress updated",
                old_value=json.dumps({"status": old_status}),
                new_value=json.dumps({
                    "status": new_status,
                    "progress_update_id": progress.pk,
                    "has_evidence": bool(progress.evidence),
                }),
            )

            messages.success(
                request,
                "Progress update saved successfully.",
            )

            return redirect(
                "management:assigned_case_detail",
                pk=case.pk,
            )
    else:
        form = ProgressUpdateForm(case=case)

    return render(
        request,
        "management/case_progress_form.html",
        {"case": case, "form": form},
    )

@role_required(
    UserProfile.Role.AUTHORITY,
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
def progress_evidence_download(request, pk):
    updates = ProgressUpdate.objects.select_related("case")

    if not request.user.is_superuser:
        if request.user.profile.role == UserProfile.Role.AUTHORITY:
            updates = updates.filter(
                case__assigned_authority__user=request.user,
                case__assigned_authority__is_active=True,
            )

    progress = get_object_or_404(updates, pk=pk)

    if not progress.evidence:
        raise Http404("No evidence is attached to this update.")

    try:
        evidence_file = progress.evidence.open("rb")
    except FileNotFoundError:
        raise Http404("The evidence file could not be found.")

    response = FileResponse(
        evidence_file,
        as_attachment=True,
        filename=Path(progress.evidence.name).name,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"

    return response

@role_required(UserProfile.Role.AUTHORITY)
@transaction.atomic
def case_resolve(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
        assigned_authority__user=request.user,
        assigned_authority__is_active=True,
    )

    can_resolve = case.status in {
        Case.Status.IN_PROGRESS,
        Case.Status.WAITING_INFO,
    }

    if request.method == "POST":
        form = CaseResolutionForm(request.POST)

        if form.is_valid():
            if not can_resolve:
                form.add_error(
                    None,
                    "This case cannot be marked as solved "
                    "in its current status.",
                )
            else:
                old_values = {
                    "status": case.status,
                    "resolution_note": case.resolution_note,
                }

                case.resolution_note = form.cleaned_data[
                    "resolution_note"
                ]
                case.status = Case.Status.SOLVED
                case.solved_at = timezone.now()

                case.save(
                    update_fields=[
                        "resolution_note",
                        "status",
                        "solved_at",
                        "updated_at",
                    ]
                )

                ProgressUpdate.objects.create(
                    case=case,
                    comment=case.resolution_note,
                    status=Case.Status.SOLVED,
                    updated_by=request.user,
                )

                AuditLog.objects.create(
                    case=case,
                    actor=request.user,
                    action="Case marked as solved",
                    old_value=json.dumps(old_values),
                    new_value=json.dumps({
                        "status": case.status,
                        "resolution_note": case.resolution_note,
                        "solved_at": case.solved_at.isoformat(),
                    }),
                )

                messages.success(
                    request,
                    "Case marked as solved successfully.",
                )

                return redirect(
                    "management:assigned_case_detail",
                    pk=case.pk,
                )
    else:
        form = CaseResolutionForm()

    return render(
        request,
        "management/case_resolve.html",
        {
            "case": case,
            "form": form,
            "can_resolve": can_resolve,
        },
    )
@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@transaction.atomic
def case_close(request, pk):
    case = get_object_or_404(
        Case.objects.select_for_update(),
        pk=pk,
    )

    can_close = case.status == Case.Status.SOLVED

    if request.method == "POST":
        form = CaseClosureForm(request.POST)

        if form.is_valid():
            if not can_close:
                form.add_error(
                    None,
                    "Only a solved case can be closed.",
                )
            else:
                old_status = case.status

                case.status = Case.Status.CLOSED
                case.closed_at = timezone.now()

                case.save(
                    update_fields=[
                        "status",
                        "closed_at",
                        "updated_at",
                    ]
                )

                ProgressUpdate.objects.create(
                    case=case,
                    comment=(
                        "Resolution reviewed and case closed "
                        "by an administrator."
                    ),
                    status=Case.Status.CLOSED,
                    updated_by=request.user,
                )

                AuditLog.objects.create(
                    case=case,
                    actor=request.user,
                    action="Case closed",
                    old_value=json.dumps({
                        "status": old_status,
                    }),
                    new_value=json.dumps({
                        "status": case.status,
                        "closed_at": case.closed_at.isoformat(),
                    }),
                )

                messages.success(
                    request,
                    "Case closed successfully.",
                )

                return redirect(
                    "management:case_detail",
                    pk=case.pk,
                )
    else:
        form = CaseClosureForm()

    progress_updates = case.progress_updates.select_related(
        "updated_by"
    ).order_by("created_at")

    return render(
        request,
        "management/case_close.html",
        {
            "case": case,
            "form": form,
            "can_close": can_close,
            "progress_updates": progress_updates,
        },
    )

@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def management_dashboard(request):
    cases = Case.objects.all()

    # Open cases are those still awaiting completion.
    open_statuses = [
        Case.Status.SUBMITTED,
        Case.Status.UNDER_REVIEW,
        Case.Status.NOT_STARTED,
        Case.Status.ASSIGNED,
        Case.Status.IN_PROGRESS,
        Case.Status.WAITING_INFO,
        Case.Status.REOPENED,
    ]

    stats = cases.aggregate(
        total=Count("pk"),
        open=Count(
            "pk",
            filter=Q(status__in=open_statuses),
        ),
        in_progress=Count(
            "pk",
            filter=Q(status=Case.Status.IN_PROGRESS),
        ),
        solved=Count(
            "pk",
            filter=Q(status=Case.Status.SOLVED),
        ),
        closed=Count(
            "pk",
            filter=Q(status=Case.Status.CLOSED),
        ),
        rejected=Count(
            "pk",
            filter=Q(status=Case.Status.REJECTED),
        ),
        urgent_open=Count(
            "pk",
            filter=Q(
                priority=Case.Priority.URGENT,
                status__in=open_statuses,
            ),
        ),
    )

    counts_by_status = dict(
        cases.order_by()
        .values("status")
        .annotate(total=Count("pk"))
        .values_list("status", "total")
    )

    status_summary = [
        {
            "value": value,
            "label": label,
            "total": counts_by_status.get(value, 0),
        }
        for value, label in Case.Status.choices
    ]

    recent_cases = cases.select_related(
        "category",
        "assigned_authority",
    ).order_by("-created_at")[:5]

    return render(
        request,
        "management/dashboard.html",
        {
            "stats": stats,
            "status_summary": status_summary,
            "recent_cases": recent_cases,
        },
    )
@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def case_report(request):
    form = CaseReportFilterForm(request.GET)

    cases = Case.objects.select_related(
        "category",
        "assigned_authority",
    ).order_by("-created_at", "-pk")

    filters_valid = form.is_valid()

    if filters_valid:
        filters = form.cleaned_data

        if filters["status"]:
            cases = cases.filter(status=filters["status"])

        if filters["category"]:
            cases = cases.filter(category=filters["category"])

        if filters["authority"]:
            cases = cases.filter(
                assigned_authority=filters["authority"]
            )

        if filters["date_from"]:
            cases = cases.filter(
                created_at__date__gte=filters["date_from"]
            )

        if filters["date_to"]:
            cases = cases.filter(
                created_at__date__lte=filters["date_to"]
            )
    else:
        cases = cases.none()

    if request.GET.get("export") == "csv" and filters_valid:
        response = HttpResponse(
            content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="fmsc-case-report.csv"'
        )

        # Helps spreadsheet applications recognise UTF-8.
        response.write("\ufeff")

        writer = csv.writer(response)

        writer.writerow([
            "Case Number",
            "Title",
            "Type",
            "Category",
            "Priority",
            "Status",
            "Authority",
            "Submitted On",
            "Solved On",
            "Closed On",
        ])

        def safe_cell(value):
            text = str(value) if value is not None else ""

            # Prevent case text being interpreted as a spreadsheet formula.
            if text.lstrip().startswith(("=", "+", "-", "@")):
                return "'" + text

            return text

        def display_date(value):
            if not value:
                return ""

            return timezone.localtime(value).strftime(
                "%Y-%m-%d %H:%M"
            )

        for case in cases.iterator(chunk_size=500):
            writer.writerow([
                safe_cell(case.case_number),
                safe_cell(case.title),
                safe_cell(case.get_case_type_display()),
                safe_cell(case.category.name),
                safe_cell(case.get_priority_display()),
                safe_cell(case.get_status_display()),
                safe_cell(
                    case.assigned_authority.name
                    if case.assigned_authority
                    else "Unassigned"
                ),
                display_date(case.created_at),
                display_date(case.solved_at),
                display_date(case.closed_at),
            ])

        return response

    paginator = Paginator(cases, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    parameters = request.GET.copy()
    parameters.pop("page", None)
    parameters.pop("export", None)

    return render(
        request,
        "management/case_report.html",
        {
            "form": form,
            "filters_valid": filters_valid,
            "page_obj": page_obj,
            "total": paginator.count,
            "filter_query": parameters.urlencode(),
        },
    )