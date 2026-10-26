from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render

from cases.models import Case


@login_required(login_url="/admin/login/")
@permission_required("cases.view_case", raise_exception=True)
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

@login_required(login_url="/admin/login/")
@permission_required("cases.view_case", raise_exception=True)
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