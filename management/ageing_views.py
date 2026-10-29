from datetime import timedelta

from django import forms
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import UserProfile
from cases.models import Case

from .models import Authority


class AgeingFilterForm(forms.Form):
    authority = forms.ModelChoiceField(
        queryset=Authority.objects.all(),
        required=False,
        empty_label="All authorities",
    )

    status = forms.ChoiceField(
        required=False,
        choices=[
            ("", "Assigned and Not Started"),
            (Case.Status.ASSIGNED, "Assigned"),
            (Case.Status.NOT_STARTED, "Not Started"),
        ],
    )

    minimum_age = forms.IntegerField(
        label="Minimum age in days",
        required=False,
        min_value=0,
        max_value=36500,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "For example: 7",
            }
        ),
    )


@role_required(
    UserProfile.Role.ADMINISTRATOR,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.MANAGEMENT,
)
def ageing_report(request):
    today = timezone.localdate()
    form = AgeingFilterForm(request.GET)

    cases = Case.objects.filter(
        status__in=[
            Case.Status.ASSIGNED,
            Case.Status.NOT_STARTED,
        ]
    ).select_related(
        "category",
        "assigned_authority",
    ).order_by("created_at", "pk")

    filters_valid = form.is_valid()

    if filters_valid:
        filters = form.cleaned_data

        if filters["authority"]:
            cases = cases.filter(
                assigned_authority=filters["authority"]
            )

        if filters["status"]:
            cases = cases.filter(
                status=filters["status"]
            )

        minimum_age = filters.get("minimum_age")

        if minimum_age is not None:
            cutoff_date = today - timedelta(days=minimum_age)

            cases = cases.filter(
                created_at__date__lte=cutoff_date
            )
    else:
        cases = cases.none()

    paginator = Paginator(cases, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    rows = []

    for case in page_obj.object_list:
        submitted_date = timezone.localtime(
            case.created_at
        ).date()

        age_days = max(
            (today - submitted_date).days,
            0,
        )

        rows.append({
            "case": case,
            "age_days": age_days,
        })

    parameters = request.GET.copy()
    parameters.pop("page", None)

    return render(
        request,
        "management/ageing_report.html",
        {
            "form": form,
            "filters_valid": filters_valid,
            "rows": rows,
            "page_obj": page_obj,
            "total": paginator.count,
            "today": today,
            "filter_query": parameters.urlencode(),
        },
    )