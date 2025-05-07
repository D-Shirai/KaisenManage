# core/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from .models import Project, Assignment, Photo

User = get_user_model()



class ProjectForm(forms.ModelForm):
    """
    新規・編集用の案件フォーム。
    company/district/team/group によるユーザー絞り込みが可能。
    """

    order_no = forms.CharField(
        label='オーダーNo.',
        max_length=6,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '例：A01234',
            'class': 'form-control'
        })
    )

    company = forms.CharField(
        label='会社',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '会社名',
            'class': 'form-control'
        })
    )
    district = forms.CharField(
        label='地区',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '地区',
            'class': 'form-control'
        })
    )
    team = forms.CharField(
        label='チーム',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'チーム',
            'class': 'form-control'
        })
    )
    group = forms.CharField(
        label='グループ',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'グループ',
            'class': 'form-control'
        })
    )

    allowed_users = forms.ModelMultipleChoiceField(
        label='アクセス許可ユーザー',
        queryset=User.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Project
        fields = ['order_no', 'name', 'allowed_users', 'company', 'district', 'team', 'group']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': '案件名を入力',
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初期状態では全ユーザーを対象。ビューで絞り込みを行う。
        self.fields['allowed_users'].queryset = User.objects.all()

    def clean_order_no(self):
        order_no = self.cleaned_data.get('order_no')
        if order_no and len(order_no) > 6:
            raise ValidationError('オーダーNo.は最大6文字までです。')
        return order_no


class CustomerExcelUploadForm(forms.Form):
    """
    顧客一括登録用 Excel インポートフォーム。
    """
    excel_file = forms.FileField(
        label="顧客Excelファイル",
        help_text="※.xlsx ファイルをアップロード。1行目にヘッダーが必要です。",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if not f.name.lower().endswith('.xlsx'):
            raise ValidationError('Excelファイル（.xlsx）をアップロードしてください。')
        return f



class AssignmentForm(forms.ModelForm):
    """
    割当ステータス更新用フォーム
    """
    class Meta:
        model = Assignment
        fields = [
            'pr_status',
            'open_round',
            'open_status',
            'performed_by',
            'checked_by',
            'gauge_spec',
            'absence_action',
            'leaflet_type',
            'leaflet_status',
            'm_valve_state',
            'm_valve_attach',
        ]
        widgets = {
            'pr_status':      forms.Select(attrs={'class': 'form-select'}),
            'open_round':     forms.Select(attrs={'class': 'form-select'}),
            'open_status':    forms.Select(attrs={'class': 'form-select'}),
            'performed_by':   forms.Select(attrs={'class': 'form-select'}),
            'checked_by':     forms.Select(attrs={'class': 'form-select'}),
            'gauge_spec':     forms.Select(attrs={'class': 'form-select'}),
            'absence_action': forms.Select(attrs={'class': 'form-select'}),
            'leaflet_type':   forms.Select(attrs={'class': 'form-select'}),
            'leaflet_status': forms.Select(attrs={'class': 'form-select'}),
            'm_valve_state':  forms.Select(attrs={'class': 'form-select'}),
            'm_valve_attach': forms.Select(attrs={'class': 'form-select'}),
        }


class PhotoForm(forms.ModelForm):
    """
    写真アップロード用フォーム
    """
    class Meta:
        model = Photo
        fields = ['photo_type', 'image']
        widgets = {
            'photo_type': forms.Select(attrs={'class': 'form-select'}),
            'image':      forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class BulkAssignmentForm(forms.Form):
    """
    絞り込んだ割当の一括更新用フォーム
    """
    pr_status = forms.ChoiceField(
        label="PR状況",
        choices=[('', '――')] + list(Assignment.PR_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    gauge_spec = forms.ChoiceField(
        label="ゲージ仕様",
        choices=[('', '――')] + list(Assignment.GAUGE_SPEC_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    absence_action = forms.ChoiceField(
        label="不在時処置",
        choices=[('', '――')] + list(Assignment.ABSENCE_ACTION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    open_status = forms.ChoiceField(
        label="開栓状況",
        choices=[('', '――')] + list(Assignment.OPEN_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    open_round = forms.ChoiceField(
        label="開栓巡目",
        choices=[('', '――')] + [(str(c[0]), c[1]) for c in Assignment.OPEN_ROUND_CHOICES],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    leaflet_type = forms.ChoiceField(
        label="用紙種別",
        choices=[('', '――')] + list(Assignment.LEAFLET_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    leaflet_status = forms.ChoiceField(
        label="投函ステータス",
        choices=[('', '――')] + list(Assignment.LEAFLET_STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    m_valve_state = forms.ChoiceField(
        label="M栓状態",
        choices=[('', '――')] + list(Assignment.MVALVE_STATE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    m_valve_attach = forms.ChoiceField(
    label="メーター取外",
    choices=[('', '――')] + list(Assignment.MVALVE_ATTACH_CHOICES),
    required=False,
    widget=forms.Select(attrs={'class': 'form-select'})
)



class ExcelUploadForm(forms.Form):
    """
    ユーザー一括登録用 Excel インポートフォーム
    """
    excel_file = forms.FileField(
        label="ユーザーExcelファイル",
        help_text="氏名コード・姓・名・会社・地区・チーム・グループ・スタッフフラグ",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if not f.name.lower().endswith('.xlsx'):
            raise ValidationError('Excelファイル（.xlsx）をアップロードしてください。')
        return f


class UserPreviewForm(forms.ModelForm):
    """
    インポートプレビュー用フォーム（既存ユーザーの確認・編集に使用）
    """
    class Meta:
        model = User
        fields = [
            'code', 'last_name', 'first_name',
            'company', 'district', 'team', 'group', 'is_staff'
        ]
        widgets = {
            'code':       forms.TextInput(attrs={'readonly': True, 'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company':    forms.TextInput(attrs={'class': 'form-control'}),
            'district':   forms.TextInput(attrs={'class': 'form-control'}),
            'team':       forms.TextInput(attrs={'class': 'form-control'}),
            'group':      forms.TextInput(attrs={'class': 'form-control'}),
            'is_staff':   forms.Select(attrs={'class': 'form-select'}),
        }


class UserFilterForm(forms.Form):
    """
    ユーザー一覧フィルタリング用プルダウンフォーム
    """
    company  = forms.ChoiceField(label="会社",   required=False)
    district = forms.ChoiceField(label="地区",   required=False)
    team     = forms.ChoiceField(label="チーム", required=False)
    group    = forms.ChoiceField(label="グループ", required=False)
    is_staff = forms.ChoiceField(
        label="スタッフ権限",
        choices=[('', '全て'), ('1', 'あり'), ('0', 'なし')],
        required=False
    )


class CustomUserForm(forms.ModelForm):
    """
    ユーザー編集用フォーム
    """
    is_staff = forms.ChoiceField(
        label='スタッフ権限',
        choices=[(False, 'なし'), (True, 'あり')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=False,
    )

    class Meta:
        model = User
        fields = [
            'code',
            'last_name', 'first_name',
            'company', 'district', 'team', 'group',
            'is_staff'
        ]
        widgets = {
            'code':       forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company':    forms.TextInput(attrs={'class': 'form-control'}),
            'district':   forms.TextInput(attrs={'class': 'form-control'}),
            'team':       forms.TextInput(attrs={'class': 'form-control'}),
            'group':      forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = Layout(
            'code',
            'last_name', 'first_name',
            'company', 'district', 'team', 'group',
            'is_staff',
        )


class UserImportEditForm(forms.Form):
    """
    プレビュー編集用フォーム
    """
    code       = forms.CharField(label='氏名コード', max_length=7)
    last_name  = forms.CharField(label='姓',       max_length=10)
    first_name = forms.CharField(label='名',       max_length=10)
    company    = forms.CharField(label='会社',     max_length=10)
    district   = forms.CharField(label='地区',     max_length=10)
    team       = forms.CharField(label='チーム',   max_length=20)
    group      = forms.CharField(label='グループ', max_length=20)
    is_staff   = forms.BooleanField(label='スタッフ権限', required=False)
