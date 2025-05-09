import openpyxl
from openpyxl import load_workbook
import re
from collections import defaultdict

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.forms import formset_factory
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q
# from django.db.models.functions import Substr  # 未使用ならコメントアウト
from django.db import IntegrityError  # 必要に応じて

from .models import Project, Assignment, Customer, Photo
from .forms import (
    ProjectForm, AssignmentForm, PhotoForm,
    BulkAssignmentForm, CustomerExcelUploadForm,
    ExcelUploadForm, UserFilterForm,
    CustomUserForm, UserImportEditForm
)

User = get_user_model()



# ─── ホーム画面 ───────────────────────────────────────────
@login_required
def home(request):
    return render(request, 'core/home.html')


# ─── 案件一覧 ───────────────────────────────────────────
@login_required
def project_list(request):
    user = request.user

    # スタッフは全件、一般ユーザーは許可案件のみ取得
    base_qs = Project.objects.all() if user.is_staff else Project.objects.filter(allowed_users=user)

    # 未完了・完了の区分
    in_progress = Project.objects.filter(
        allowed_users=user,
        is_completed=False,
        is_deleted=False 
    ).order_by('-date')
    completed_qs = Project.objects.filter(
        allowed_users=user,
        is_completed=True,
        is_deleted=False  
    ).order_by('-date')

    # 地区フィルター用の選択肢（スタッフは全地区から、一般は自分に関係する地区のみ）
    district_choices = base_qs.values_list('district', flat=True).distinct()
    selected_district = request.GET.get('district', user.district)

    # 日付フィルター
    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')

    if selected_district:
        completed_qs = completed_qs.filter(district=selected_district)
    if date_from:
        completed_qs = completed_qs.filter(date__gte=date_from)
    if date_to:
        completed_qs = completed_qs.filter(date__lte=date_to)

    return render(request, 'core/project_list.html', {
        'in_progress':       in_progress,
        'completed':         completed_qs,
        'district_choices':  district_choices,
        'selected_district': selected_district,
        'date_from':         date_from or '',
        'date_to':           date_to   or '',
    })


@login_required
def project_create(request):
    # スタッフ以外はホームへ
    if not request.user.is_staff:
        return redirect('home')

    # フィルタ用（必要に応じて）
    def make_choices(field):
        vals = User.objects.order_by(field).values_list(field, flat=True).distinct()
        return [('', '全て')] + [(v, v) for v in vals if v]

    companies  = make_choices('company')
    districts  = make_choices('district')
    teams      = make_choices('team')
    groups     = make_choices('group')

    # 初期絞り込み（必要に応じて）
    default_company  = request.user.company
    default_district = request.user.district
    default_team     = request.user.team
    users = User.objects.filter(
        company=default_company,
        district=default_district,
        team=default_team,
    ).order_by('code')

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            # セッションに保存する基本情報
            session_data = {
                'form_data': {
                    'name':     form.cleaned_data['name'],
                    'order_no': form.cleaned_data.get('order_no') or None,
                },
                'allowed': request.POST.getlist('allowed_users'),
            }

            # Excel がアップロードされていればプレビューを作成
            excel = request.FILES.get('excel_file')
            if excel:
                wb      = load_workbook(excel)
                sheet   = wb.active
                headers = [c.value for c in sheet[1]]

                def idx(col):
                    try:
                        return headers.index(col)
                    except ValueError:
                        raise ValueError(f"ヘッダー「{col}」が見つかりません")

                preview = []
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    raw_usage = row[idx('ご使用番号')] or ''
                    usage_str = str(raw_usage).strip()
                    # 使用番号が空ならスキップ
                    if not usage_str:
                        continue
                    # 14桁なら末尾1文字を切り捨て
                    if len(usage_str) == 14:
                        usage_str = usage_str[:-1]
                    # 末尾4桁を抽出し、先頭ゼロを保持
                    four = usage_str[-4:].zfill(4)

                    raw_name      = row[idx('お名前')] or ''
                    raw_tower     = row[idx('棟番号')] or ''
                    raw_chou      = row[idx('丁番号')] or ''
                    raw_meter_tp  = row[idx('メーター種別')] or ''
                    raw_meter_no  = row[idx('メーター番号')] or ''

                    # メーター番号は数字なら0パディング
                    meter_number = str(raw_meter_no).strip()
                    if meter_number.isdigit():
                        meter_number = meter_number.zfill(4)

                    preview.append({
                        'usage_no':     four,
                        'name':         str(raw_name).strip(),
                        'room_number':  str(raw_tower).strip() or str(raw_chou).strip(),
                        'meter_type':   str(raw_meter_tp).strip(),
                        'meter_number': meter_number,
                    })

                session_data['customers'] = preview

            # セッションへ
            request.session['pending_project'] = session_data
            return redirect('core:project_create_confirm')

        else:
            messages.error(request, 'フォームにエラーがあります。')
    else:
        form = ProjectForm()

    return render(request, 'core/project_form.html', {
        'form':             form,
        'companies':        companies,
        'districts':        districts,
        'teams':            teams,
        'groups':           groups,
        'users':            users,
        'default_company':  default_company,
        'default_district': default_district,
        'default_team':     default_team,
    })



@login_required
def project_create_confirm(request):
    data = request.session.get('pending_project')
    if not data:
        messages.error(request, 'セッションが期限切れです。最初からやり直してください。')
        return redirect('core:project_create')

    if request.method == 'POST':
        # 1) プロジェクト作成
        fd = data['form_data']
        proj = Project.objects.create(
            name     = fd['name'],
            order_no = fd['order_no'],
            district = request.user.district,
        )
        # ログインユーザー＋選択ユーザーを登録
        proj.allowed_users.add(request.user)
        proj.allowed_users.add(*User.objects.filter(pk__in=data['allowed']))

        # 2) 顧客・割当を一括登録
        for c in data.get('customers', []):
            usage_no = c.get('usage_no')
            if not usage_no:
                continue
            cust, _ = Customer.objects.update_or_create(
                usage_no=usage_no,
                defaults={
                    'name':        c['name'],
                    'room_number': c['room_number'],
                }
            )
            # 重複を避けるため update_or_create
            Assignment.objects.update_or_create(
                project      = proj,
                customer     = cust,
                defaults     = {
                    'meter_type':   c['meter_type'],
                    'meter_number': c['meter_number'],
                }
            )

        # セッションをクリア
        request.session.pop('pending_project', None)
        messages.success(request, '案件と顧客を登録しました。')
        return redirect('core:project_detail', pk=proj.pk)

    # GET: 確認画面表示
    return render(request, 'core/project_create_confirm.html', {
        'form_data':     data['form_data'],
        'allowed_users': User.objects.filter(pk__in=data['allowed']),
        'customers':     data.get('customers', []),
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, allowed_users=request.user)

    # ─── Excelインポート処理（スタッフ専用） ──────────────────────
    excel_form = CustomerExcelUploadForm(request.POST or None, request.FILES or None)
    if request.user.is_staff and request.method == 'POST' and 'excel_file' in request.FILES:
        if excel_form.is_valid():
            data = request.session.get('pending_project')
            if not data:
                messages.error(request, 'セッションが期限切れです。')
                return redirect('core:project_create')

            form_data = data.get('form_data', {})
            allowed_ids = data.get('allowed', [])
            project = Project.objects.create(
                name=form_data['name'],
                order_no=form_data.get('order_no') or None,
                district=request.user.district,
            )
            project.allowed_users.set(User.objects.filter(pk__in=allowed_ids))

            wb = openpyxl.load_workbook(request.FILES['excel_file'])
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]

            def idx(col_name):
                if col_name not in headers:
                    raise ValueError(f"Excel のヘッダーに「{col_name}」列が見つかりません")
                return headers.index(col_name)

            for row in sheet.iter_rows(min_row=2, values_only=True):
                usage_no      = str(row[idx('ご使用番号')] or '').strip()
                name          = str(row[idx('お名前')] or '').strip()
                tou_number    = str(row[idx('棟番号')] or '').strip()
                chou_number   = str(row[idx('丁番号')] or '').strip()
                meter_type    = str(row[idx('メーター種別')] or '').strip()
                meter_number  = str(row[idx('メーター番号')] or '').zfill(4)

                # 棟番号が空なら丁番号を使用
                room_number = tou_number if tou_number else chou_number

                cust, _ = Customer.objects.update_or_create(
                    usage_no=usage_no,
                    defaults={
                        'name': name,
                        'room_number': room_number,
                    }
                )

                Assignment.objects.update_or_create(
                    project=project,
                    customer=cust,
                    defaults={
                        'meter_type': meter_type,
                        'meter_number': meter_number,
                    }
                )

            del request.session['pending_project']
            messages.success(request, '案件を作成し、顧客をExcelからインポートしました。')
            return redirect('core:project_detail', pk=project.pk)



    # フィルタ・オプション取得
    room_q = request.GET.get('room', '').strip()
    strip_tou = request.GET.get('strip_tou') == '1'

    # 棟番号除去して保存
    if request.method == 'POST' and 'strip_tou_apply' in request.POST:
        to_strip = Assignment.objects.filter(project=project, customer__room_number__contains='-').select_related('customer')
        for a in to_strip:
            parts = a.customer.room_number.split('-', 1)
            if len(parts) == 2:
                a.customer.room_number = parts[1]
                a.customer.save()
        messages.success(request, "棟番号を除去して部屋番号を上書き保存しました。")
        return redirect('core:project_detail', pk=pk)

    # 一覧取得（検索適用）
    assignments = Assignment.objects.filter(project=project).select_related('customer')
    if room_q:
        keyword = room_q.replace('*', '')
        if strip_tou:
            if room_q.startswith('*') and room_q.endswith('*'):
                assignments = assignments.filter(customer__room_number__iregex=rf'(^|\-).*\{keyword}.*')
            elif room_q.startswith('*'):
                assignments = assignments.filter(customer__room_number__iregex=rf'(^|\-).*\{keyword}$')
            elif room_q.endswith('*'):
                assignments = assignments.filter(customer__room_number__iregex=rf'(^|\-){keyword}.*')
            else:
                assignments = assignments.filter(customer__room_number__iregex=rf'(^|\-){keyword}($|[^0-9])')
        else:
            if room_q.startswith('*') and room_q.endswith('*'):
                assignments = assignments.filter(customer__room_number__icontains=keyword)
            elif room_q.startswith('*'):
                assignments = assignments.filter(customer__room_number__iendswith=keyword)
            elif room_q.endswith('*'):
                assignments = assignments.filter(customer__room_number__istartswith=keyword)
            else:
                assignments = assignments.filter(customer__room_number__icontains=room_q)

    # 一括更新処理
    bulk_form = BulkAssignmentForm(request.POST or None)
    if request.method == 'POST' and 'bulk_update' in request.POST and bulk_form.is_valid():
        selected = request.POST.getlist('selected')
        to_update = assignments.filter(pk__in=selected)
        data = {}
        for fld in [
            'pr_status', 'gauge_spec', 'absence_action',
            'open_round', 'open_status', 'leaflet_type',
            'leaflet_status', 'm_valve_state', 'm_valve_attach',
        ]:
            val = bulk_form.cleaned_data.get(fld)
            if val not in (None, '', []):
                data[fld] = val
        if data:
            to_update.update(**data)
        return redirect('core:project_detail', pk=pk)



    # ─── 進捗サマリ ────────────────────────────────
    total = assignments.count()
    done = assignments.filter(open_status='完了').count()
    not_done = total - done
    pct = int(done / total * 100) if total else 0
    not_pct = 100 - pct

    summary = {
        'total': total,
        'done': done,
        'not_done': not_done,
        'pct': pct,
        'not_pct': not_pct,
    }

    # ─── PRサマリ ────────────────────────────────
    from collections import Counter
    pr_counts = Counter(a.pr_status for a in assignments)

    pr_summary = {
        '未訪問': pr_counts.get('未訪問', 0),
        '在宅':   pr_counts.get('在宅', 0),
        '不在':   pr_counts.get('不在', 0),
    }
    pr_total = sum(pr_summary.values())

    pr_pct = {
        k: int(v / pr_total * 100) if pr_total else 0
        for k, v in pr_summary.items()
    }

    # ─── コンテキスト送信 ────────────────────────────────
    context = {
        'project': project,
        'assignments': assignments,
        'excel_form': excel_form,
        'bulk_form': bulk_form,
        'summary': summary,
        'pr_summary': pr_summary,
        'pr_pct': pr_pct,
        'room_q': room_q,
        'strip_tou': strip_tou,
    }
    return render(request, 'core/project_detail.html', context)



# ─── 顧客詳細・ステータス更新・写真アップロード ───────────────────
@login_required
def assignment_detail(request, pk, assignment_pk):
    project    = get_object_or_404(Project, pk=pk, allowed_users=request.user)
    assignment = get_object_or_404(Assignment, pk=assignment_pk, project=project)

    status_form = AssignmentForm(request.POST or None, instance=assignment)
    photo_form  = PhotoForm(request.POST or None, request.FILES or None)

    # 写真削除
    if request.method == 'POST' and 'delete_photo' in request.POST:
        ptype = request.POST['delete_photo']
        Photo.objects.filter(assignment=assignment, photo_type=ptype).delete()
        return redirect('core:assignment_detail', pk=pk, assignment_pk=assignment_pk)

    # 写真アップロード
    if request.method == 'POST' and request.FILES.get('image'):
        if photo_form.is_valid():
            photo = photo_form.save(commit=False)
            photo.assignment = assignment
            photo.save()
        return redirect('core:assignment_detail', pk=pk, assignment_pk=assignment_pk)

    # ステータス更新
    if request.method == 'POST' and status_form.is_valid():
        status_form.save()
        return redirect('core:assignment_detail', pk=pk, assignment_pk=assignment_pk)

    # 写真スロット情報
    photo_slots = []
    for ptype, plabel in Photo.PHOTO_TYPE_CHOICES:
        existing = assignment.photos.filter(photo_type=ptype).first()
        photo_slots.append({
            'type':  ptype,
            'label': plabel,
            'photo': existing,
        })

    return render(request, 'core/assignment_detail.html', {
        'project':     project,
        'assignment':  assignment,
        'status_form': status_form,
        'photo_form':  photo_form,
        'photo_slots': photo_slots,
    })


# ─── ビジュアルマップ表示 ───────────────────────────────────
@login_required
def project_map(request, pk):
    project     = get_object_or_404(Project, pk=pk, allowed_users=request.user)
    assignments = Assignment.objects.filter(project=project).select_related('customer')

    floors = defaultdict(list)
    for a in assignments:
        room = a.customer.room_number or ''
        if room.isdigit():
            floor = int(room[:-2]) if len(room) >= 3 else (int(room[0]) if len(room) == 2 else 0)
        else:
            floor = -1
        floors[floor].append(a)

    sorted_floors = sorted(
        floors.items(),
        key=lambda x: (x[0] == -1, -x[0] if x[0] != -1 else 0)
    )

    return render(request, 'core/project_map.html', {
        'project':             project,
        'grouped_assignments': sorted_floors,
    })

# ─── 案件削除 完了 ──────────────────────────────────────────
@login_required
def project_delete(request, pk):
    proj = get_object_or_404(Project, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        proj.soft_delete()
        messages.success(request, '案件を削除フォルダに移動しました（30日後に自動削除）')
        return redirect('core:project_list')

@login_required
def project_complete(request, pk):
    proj = get_object_or_404(Project, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        proj.is_completed = True
        proj.save()
        messages.success(request, '案件を完了としてマークしました')
        return redirect('core:project_list')



# ─── ユーザー管理 ───────────────────────────────────────────
@login_required
def user_manage(request):
    if not request.user.is_staff:
        return redirect('home')

    # 一括削除
    if request.method == 'POST' and 'bulk_delete' in request.POST:
        selected = request.POST.getlist('selected_user')
        if not selected:
            messages.warning(request, '削除するユーザーを選択してください。')
        else:
            if str(request.user.pk) in selected:
                messages.error(request, '自分自身は削除できません。')
            else:
                count, _ = User.objects.filter(pk__in=selected).delete()
                messages.success(request, f'{count} 件のユーザーを削除しました。')
        return redirect('core:user_manage')

    # Excel プレビュー
    excel_form = ExcelUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and 'bulk_delete' not in request.POST and excel_form.is_valid():
        wb = openpyxl.load_workbook(request.FILES['excel_file'])
        sheet = wb.active
        headers = [c.value for c in sheet[1]]
        def idx(col):
            if col not in headers:
                raise ValueError(f"ヘッダー「{col}」が見つかりません")
            return headers.index(col)

        preview_data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            code       = str(row[idx('氏名コード')] or '').strip().zfill(7)
            last_name  = str(row[idx('姓')]        or '').strip()
            first_name = str(row[idx('名')]        or '').strip()
            company    = str(row[idx('会社')]      or '').strip()
            district   = str(row[idx('地区')]      or '').strip()
            team       = str(row[idx('チーム')]    or '').strip()
            group      = str(row[idx('グループ')]  or '').strip()
            is_staff   = str(row[idx('スタッフ権限')] or '').strip() == '1'
            exists     = User.objects.filter(code=code).exists()

            preview_data.append({
                'code':       code,
                'last_name':  last_name,
                'first_name': first_name,
                'company':    company,
                'district':   district,
                'team':       team,
                'group':      group,
                'is_staff':   is_staff,
                'exists':     exists,
            })

        request.session['preview_data'] = preview_data
        return redirect('core:import_users_confirm')

    # フィルタ＆一覧
    filter_form = UserFilterForm(request.GET or None)
    def make_choices(field):
        vals = User.objects.order_by(field).values_list(field, flat=True).distinct()
        return [('', '全て')] + [(v, v) for v in vals if v]

    filter_form.fields['company'].choices  = make_choices('company')
    filter_form.fields['district'].choices = make_choices('district')
    filter_form.fields['team'].choices     = make_choices('team')
    filter_form.fields['group'].choices    = make_choices('group')

    users = User.objects.order_by('code')
    if filter_form.is_valid():
        cd = filter_form.cleaned_data
        if cd['company']:
            users = users.filter(company=cd['company'])
        if cd['district']:
            users = users.filter(district=cd['district'])
        if cd['team']:
            users = users.filter(team=cd['team'])
        if cd['group']:
            users = users.filter(group=cd['group'])
        if cd['is_staff'] in ['0', '1']:
            users = users.filter(is_staff=(cd['is_staff'] == '1'))

    return render(request, 'core/user_manage.html', {
        'excel_form':  excel_form,
        'filter_form': filter_form,
        'users':       users,
    })


# ─── ユーザー編集 ─────────────────────────────────────
@login_required
def user_edit(request, pk):
    if not request.user.is_staff:
        return redirect('home')
    usr = get_object_or_404(User, pk=pk)
    form = CustomUserForm(request.POST or None, instance=usr)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('core:user_manage')
    return render(request, 'core/user_edit.html', {
        'form':     form,
        'user_obj': usr,
    })


# ─── ユーザーインポート確認 ─────────────────────────────
@require_http_methods(["GET", "POST"])
def import_users_confirm(request):
    preview_data = list(request.session.get('preview_data', []))

    if request.method == 'POST':
        action    = request.POST.get('action')
        index_str = request.POST.get('index')

        # ─── 編集 ─────────────────────────────
        if action == 'edit' and index_str is not None:
            idx = int(index_str)
            request.session['edit_index'] = idx
            return redirect('core:import_users_edit')

        # ─── 削除 ─────────────────────────────
        if action == 'delete' and index_str is not None:
            idx = int(index_str)
            if 0 <= idx < len(preview_data):
                preview_data.pop(idx)
                if preview_data:
                    request.session['preview_data'] = preview_data
                else:
                    request.session.pop('preview_data', None)
                messages.info(request, f"{idx+1} 行目を削除しました。")
            return redirect('core:import_users_confirm')

        # ─── 登録 ─────────────────────────────
        if action == 'register':
            imported = []
            skipped  = []

            for row in preview_data:
                code = row.get('code')
                if not code:
                    continue

                # code または username が既存ならスキップ
                if User.objects.filter(Q(code=code) | Q(username=code)).exists():
                    skipped.append(code)
                    continue

                # 新規作成
                user = User.objects.create_user(
                    code=code,
                    username=code,
                    last_name=row.get('last_name', ''),
                    first_name=row.get('first_name', ''),
                    company=row.get('company', ''),
                    district=row.get('district', ''),
                    team=row.get('team', ''),
                    group=row.get('group', ''),
                    is_staff=row.get('is_staff', False),
                    password=code,
                )
                imported.append(code)

            # セッションとメッセージ
            request.session.pop('preview_data', None)
            messages.success(
                request,
                f"{len(imported)} 人をインポート（初期パスワードは氏名コード）。"
                + (f" {len(skipped)} 人は既に存在していたためスキップしました。" if skipped else "")
            )
            return redirect('core:user_manage')

    return render(request, 'core/import_users_confirm.html', {
        'preview_data': preview_data,
    })


# ─── ユーザーインポート編集 ─────────────────────────────
@require_http_methods(["GET", "POST"])
def import_users_edit(request):
    preview_data = list(request.session.get('preview_data', []))
    idx = request.session.get('edit_index')
    if idx is None or not (0 <= idx < len(preview_data)):
        messages.error(request, '編集対象の行が存在しません。')
        return redirect('core:import_users_confirm')

    if request.method == 'POST':
        form = UserImportEditForm(request.POST)
        if form.is_valid():
            preview_data[idx] = form.cleaned_data
            request.session['preview_data'] = preview_data
            request.session.pop('edit_index', None)
            messages.success(request, f"{idx+1} 行目を更新しました。")
            return redirect('core:import_users_confirm')
    else:
        form = UserImportEditForm(initial=preview_data[idx])

    return render(request, 'core/import_users_edit.html', {
        'form':  form,
        'index': idx,
    })


# ─── パスワード変更 ─────────────────────────────────────
@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'パスワードを変更しました。')
            return redirect('core:password_change_done')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'core/password_change.html', {
        'form': form,
    })


@login_required
def password_change_done(request):
    return render(request, 'core/password_change_done.html')
