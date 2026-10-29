from django import forms
from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
)
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import UserProfile
from cases.models import Case


class DashboardPeriodForm(forms.Form):
    date_from = forms.DateField(
        label="Submitted from",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        ),
    )

    date_to = forms.DateField(
        label="Submitted to",
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            self.add_error(
                "date_to",
                "The end date must be on or after the start date.",
            )

        return cleaned_data


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def management_dashboard(request):
    form = DashboardPeriodForm(request.GET)
    filters_valid = form.is_valid()

    cases = Case.objects.all()

    if filters_valid:
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")

        if date_from:
            cases = cases.filter(
                created_at__date__gte=date_from
            )

        if date_to:
            cases = cases.filter(
                created_at__date__lte=date_to
            )
    else:
        cases = cases.none()

    pending_statuses = [
        Case.Status.SUBMITTED,
        Case.Status.UNDER_REVIEW,
        Case.Status.NOT_STARTED,
        Case.Status.ASSIGNED,
        Case.Status.IN_PROGRESS,
        Case.Status.WAITING_INFO,
        Case.Status.REOPENED,
    ]

    not_started_statuses = [
        Case.Status.ASSIGNED,
        Case.Status.NOT_STARTED,
    ]

    stats = cases.aggregate(
        total=Count("pk"),
        attempted=Count(
            "pk",
            filter=~Q(status=Case.Status.SUBMITTED),
        ),
        not_attempted=Count(
            "pk",
            filter=Q(status=Case.Status.SUBMITTED),
        ),
        open=Count(
            "pk",
            filter=~Q(status=Case.Status.CLOSED),
        ),
        pending=Count(
            "pk",
            filter=Q(status__in=pending_statuses),
        ),
        not_started=Count(
            "pk",
            filter=Q(status__in=not_started_statuses),
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
        urgent=Count(
            "pk",
            filter=Q(priority=Case.Priority.URGENT),
        ),
        normal=Count(
            "pk",
            filter=Q(priority=Case.Priority.NORMAL),
        ),
        complaints=Count(
            "pk",
            filter=Q(case_type=Case.CaseType.COMPLAINT),
        ),
        suggestions=Count(
            "pk",
            filter=Q(case_type=Case.CaseType.SUGGESTION),
        ),
        urgent_pending=Count(
            "pk",
            filter=Q(
                priority=Case.Priority.URGENT,
                status__in=pending_statuses,
            ),
        ),
    )

    metrics = [
        {
            "label": "Total Cases",
            "value": stats["total"],
            "style": "",
        },
        {
            "label": "Attempted",
            "value": stats["attempted"],
            "style": "stat-card-slate",
        },
        {
            "label": "Not Attempted",
            "value": stats["not_attempted"],
            "style": "stat-card-gold",
        },
        {
            "label": "Open — Not Closed",
            "value": stats["open"],
            "style": "stat-card-gold",
        },
        {
            "label": "Pending Action",
            "value": stats["pending"],
            "style": "",
        },
        {
            "label": "Not Started / Assigned",
            "value": stats["not_started"],
            "style": "stat-card-gold",
        },
        {
            "label": "In Progress",
            "value": stats["in_progress"],
            "style": "stat-card-slate",
        },
        {
            "label": "Solved — Awaiting Closure",
            "value": stats["solved"],
            "style": "stat-card-gold",
        },
        {
            "label": "Closed",
            "value": stats["closed"],
            "style": "stat-card-slate",
        },
        {
            "label": "Rejected",
            "value": stats["rejected"],
            "style": "",
        },
        {
            "label": "Urgent",
            "value": stats["urgent"],
            "style": "",
        },
        {
            "label": "Normal",
            "value": stats["normal"],
            "style": "stat-card-slate",
        },
    ]

    resolved_cases = cases.filter(
        status__in=[
            Case.Status.SOLVED,
            Case.Status.CLOSED,
        ]
    ).annotate(
        resolved_on=Coalesce(
            "solved_at",
            "closed_at",
        )
    ).filter(
        resolved_on__isnull=False,
        resolved_on__gte=F("created_at"),
    )

    average_duration = resolved_cases.aggregate(
        average=Avg(
            ExpressionWrapper(
                F("resolved_on") - F("created_at"),
                output_field=DurationField(),
            )
        )
    )["average"]

    average_resolution_days = None

    if average_duration is not None:
        average_resolution_days = (
            average_duration.total_seconds() / 86400
        )

    resolved_count = stats["solved"] + stats["closed"]

    resolution_rate = (
        resolved_count / stats["total"] * 100
        if stats["total"]
        else 0
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

    authority_summary = (
        cases.filter(status__in=pending_statuses)
        .order_by()
        .values(
            "assigned_authority_id",
            "assigned_authority__name",
        )
        .annotate(
            total=Count("pk"),
            assigned=Count(
                "pk",
                filter=Q(status=Case.Status.ASSIGNED),
            ),
            not_started=Count(
                "pk",
                filter=Q(status=Case.Status.NOT_STARTED),
            ),
            in_progress=Count(
                "pk",
                filter=Q(status=Case.Status.IN_PROGRESS),
            ),
            waiting_info=Count(
                "pk",
                filter=Q(status=Case.Status.WAITING_INFO),
            ),
        )
        .order_by("-total", "assigned_authority__name")
    )

    # Calendar-day ages match the ageing report and configured local timezone.
    # Reuse the existing SQL workload counts; add only the pending-age summary.
    today = timezone.localdate()
    ages_by_authority = {}
    for authority_id, created_at in (
        cases.filter(status__in=pending_statuses)
        .order_by()
        .values_list("assigned_authority_id", "created_at")
        .iterator(chunk_size=500)
    ):
        total_age, count = ages_by_authority.get(authority_id, (0, 0))
        age = max((today - timezone.localtime(created_at).date()).days, 0)
        ages_by_authority[authority_id] = (total_age + age, count + 1)

    authority_summary = list(authority_summary)
    for row in authority_summary:
        total_age, count = ages_by_authority[row["assigned_authority_id"]]
        row["average_age"] = total_age / count

    category_summary = (
        cases.order_by()
        .values("category_id", "category__name")
        .annotate(total=Count("pk"))
        .order_by("-total", "category__name")
    )

    recent_cases = cases.select_related(
        "category",
        "assigned_authority",
    ).order_by("-created_at", "-pk")[:5]

    return render(
        request,
        "management/dashboard.html",
        {
            "form": form,
            "filters_valid": filters_valid,
            "stats": stats,
            "metrics": metrics,
            "average_resolution_days": average_resolution_days,
            "resolution_rate": resolution_rate,
            "status_summary": status_summary,
            "authority_summary": authority_summary,
            "category_summary": category_summary,
            "recent_cases": recent_cases,
        },
    )