from pathlib import Path
p=Path('app/routes.py')
s=p.read_bytes()
old=b'''    apartments = _project_apartment_options(project.id)
    points = _remark_point_options(min_number=10)
    concession_candidates_by_apartment = {
        apartment.id: _open_concession_candidate_tasks(project=project, apartment=apartment)
        for apartment in apartments
        if apartment.id
    }
    add_mode = (request.form.get("add_mode") or request.args.get("mode") or "").strip()
    manual_kind = (request.form.get("manual_kind") or request.args.get("kind") or "").strip()
'''
new=b'''    add_mode = (request.form.get("add_mode") or request.args.get("mode") or "").strip()
    manual_kind = (request.form.get("manual_kind") or request.args.get("kind") or "").strip()
    needs_form_data = add_mode == "manual" and manual_kind in {"single", "act"}
    apartments = _project_apartment_options(project.id) if needs_form_data else []
    points = _remark_point_options(min_number=10)
    concession_candidates_by_apartment = (
        _project_concession_candidates(project=project, apartments=apartments)
        if add_mode == "manual" and manual_kind == "single" else {}
    )
'''
assert old in s
s=s.replace(old,new,1)
idx=s.index(b'def _apply_concession_to_tasks_by_ids(')
helper=b'''def _project_concession_candidates(*, project: Project, apartments: list[Apartment]) -> dict[int, list[Task]]:
    """Load candidates once, preserving duplicate-premise grouping and project isolation."""
    representatives = {_apartment_group_key(item): item.id for item in apartments}
    result = {item.id: [] for item in apartments}
    if not representatives:
        return result
    representative_by_id = {
        item.id: representatives[_apartment_group_key(item)]
        for item in Apartment.query.filter_by(project_id=project.id).all()
        if _is_visible_apartment_row(item) and _apartment_group_key(item) in representatives
    }
    tasks = (
        Task.query.join(WorkPoint, Task.work_point_id == WorkPoint.id)
        .options(selectinload(Task.work_point))
        .filter(
            Task.project_id == project.id,
            Task.apartment_id.in_(representative_by_id),
            Task.is_archived.is_(False),
            WorkPoint.point_number != "26",
        )
        .order_by(cast(WorkPoint.point_number, Integer).asc(), Task.created_at.asc(), Task.id.asc())
        .all()
    )
    for task in tasks:
        result[representative_by_id[task.apartment_id]].append(task)
    return result


'''
s=s[:idx]+helper+s[idx:];p.write_bytes(s)
