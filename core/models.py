# core/models.py

from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from datetime import timedelta


class CustomUser(AbstractUser):
    code = models.CharField("氏名コード", max_length=7, unique=True)
    company = models.CharField("会社", max_length=50, blank=True)
    district = models.CharField("地区", max_length=50, blank=True)
    team = models.CharField("チーム", max_length=50, blank=True)
    group = models.CharField("グループ", max_length=50, blank=True)

    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="customuser_set"
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="customuser_set"
    )

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー一覧"

    def __str__(self):
        return f"{self.code} - {self.get_full_name()}"


class Project(models.Model):
    order_no = models.CharField(
        "オーダーNo.",
        max_length=6,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z][0-9]{5}$',
                message='オーダーNo.は大文字1字＋数字5桁（例：A01234）で入力してください。'
            )
        ],
        help_text='大文字1字＋数字5桁（例：A01234）'
    )
    name = models.CharField("案件名", max_length=200)
    date = models.DateField("作成日", auto_now_add=True)
    district = models.CharField(
        "地区",
        max_length=50,
        blank=True,
        help_text='作成者の所属地区が自動セットされます'
    )
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="アクセス許可ユーザー",
        blank=True,
    )
    is_completed = models.BooleanField(
        "完了サイン",
        default=False,
        help_text='スタッフが対応完了後にチェックします'
    )
    is_deleted = models.BooleanField(default=False, verbose_name="削除フラグ")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="削除予定日時")

    class Meta:
        verbose_name = "案件"
        verbose_name_plural = "案件一覧"

    def save(self, *args, **kwargs):
        if not self.pk and hasattr(self, '_creator'):
            self.district = self._creator.district
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now() + timedelta(days=30)
        self.save()

    def __str__(self):
        status = "完了" if self.is_completed else "未完了"
        return f"{self.order_no} | {self.name} ({self.date}) [{status}]"


class Customer(models.Model):
    usage_no = models.CharField(
        "ご使用番号",
        max_length=4,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{4}$',
                message='ご使用番号は必ず4桁の数字で指定してください。'
            )
        ]
    )
    name = models.CharField("氏名", max_length=20, blank=True)
    room_number = models.CharField("部屋番号", max_length=20, blank=True)
    building_name = models.CharField(
        "集合住宅名", max_length=50, blank=True,
        help_text='将来の建物名管理用'
    )

    class Meta:
        verbose_name = "顧客"
        verbose_name_plural = "顧客一覧"

    def save(self, *args, **kwargs):
        raw = self.usage_no or ''
        if len(raw) == 14:
            raw = raw[:-1]
        self.usage_no = raw[-4:].zfill(4)
        if self.name and len(self.name) > 20:
            self.name = self.name[:20]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usage_no} – {self.name}"


class Assignment(models.Model):
    sequence = models.PositiveIntegerField(
        "通し番号",
        null=True,
        blank=True,
        help_text='プロジェクト内での通し番号（後ほど自動採番）'
    )
    block_number    = models.CharField("丁番号", max_length=10, blank=True)
    building_number = models.CharField("棟番号", max_length=10, blank=True)
    meter_type      = models.CharField("メーター種別", max_length=10, blank=True)
    meter_number    = models.CharField("メーター番号", max_length=20, blank=True)

    PR_STATUS_CHOICES = [
        ('not_visited', '未訪問'),
        ('home',        '在宅'),
        ('absent',      '不在'),
    ]
    pr_status = models.CharField(
        "PR状況",
        max_length=20,
        choices=PR_STATUS_CHOICES,
        default='not_visited'
    )

    OPEN_ROUND_CHOICES = [(i, f"{i}巡目") for i in range(1, 6)]
    open_round = models.PositiveSmallIntegerField(
        "開栓巡目",
        choices=OPEN_ROUND_CHOICES,
        default=1
    )

    OPEN_STATUS_CHOICES = [
        ('not_visited',   '未訪問'),
        ('in_progress',   '開栓作業中'),
        ('not_done',      '開栓未実施'),
        ('completed',     '開栓完了'),
        ('final_checked', '最終チェック完了'),
    ]
    open_status = models.CharField(
        "開栓状況",
        max_length=20,
        choices=OPEN_STATUS_CHOICES,
        default='not_visited'
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="実施ユーザー",
        related_name='performed_assignments',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    performed_at = models.DateTimeField("実施日時", null=True, blank=True)

    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="チェックユーザー",
        related_name='checked_assignments',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    checked_at = models.DateTimeField("チェック日時", null=True, blank=True)

    GAUGE_SPEC_CHOICES = [
        ('none',   '不要'),
        ('supply', '供給圧'),
        ('test',   'テスト圧'),
    ]
    gauge_spec = models.CharField(
        "ゲージ仕様",
        max_length=10,
        choices=GAUGE_SPEC_CHOICES,
        default='none',
        blank=True
    )

    ABSENCE_ACTION_CHOICES = [
        ('open',   '開栓'),
        ('safety', '保安閉栓'),
    ]
    absence_action = models.CharField(
        "不在時処置",
        max_length=20,
        choices=ABSENCE_ACTION_CHOICES,
        default='open',
        blank=True
    )

    LEAFLET_TYPE_CHOICES = [
        ('none',  '不要'),
        ('shu',   '修'),
        ('f',     'F'),
        ('other', 'その他'),
    ]
    leaflet_type = models.CharField(
        "投函用紙種別",
        max_length=10,
        choices=LEAFLET_TYPE_CHOICES,
        default='none',
        blank=True
    )

    LEAFLET_STATUS_CHOICES = [
        ('not_posted', '未投函'),
        ('posted',     '投函済'),
    ]
    leaflet_status = models.CharField(
        "投函ステータス",
        max_length=20,
        choices=LEAFLET_STATUS_CHOICES,
        blank=True, null=True
    )

    MVALVE_STATE_CHOICES = [
        ('closed', 'シマリ'),
        ('open',   'アキ'),
    ]
    m_valve_state = models.CharField(
        "M栓状態",
        max_length=10,
        choices=MVALVE_STATE_CHOICES,
        blank=True
    )

    MVALVE_ATTACH_CHOICES = [
        ('attached', '取付'),
        ('detached', '取外'),
    ]
    m_valve_attach = models.CharField(
        "M取付外",
        max_length=10,
        choices=MVALVE_ATTACH_CHOICES,
        default='attached',
        blank=True
    )

    project  = models.ForeignKey(
        Project,
        verbose_name="案件",
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    customer = models.ForeignKey(
        Customer,
        verbose_name="顧客",
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    class Meta:
        verbose_name = "割当"
        verbose_name_plural = "割当一覧"
        unique_together = ('project', 'customer')

    def clean(self):
        if self.performed_by and self.checked_by and self.performed_by == self.checked_by:
            raise ValidationError('実施ユーザーとチェックユーザーは異なる必要があります。')
        if self.leaflet_type != 'none' and not self.leaflet_status:
            raise ValidationError('投函用紙種別が不要以外のときは投函ステータスを設定してください。')
        if self.leaflet_type == 'none':
            self.leaflet_status = None

    def save(self, *args, **kwargs):
        if not self.pk:
            last = Assignment.objects.filter(project=self.project).order_by('-sequence').first()
            self.sequence = (last.sequence if last else 0) + 1

        if not self.m_valve_state:
            # meter_type によらずデフォルトは「シマリ」
            self.m_valve_state = 'closed'

        now = timezone.now()
        if self.performed_by and not self.performed_at:
            self.performed_at = now
        if self.checked_by and not self.checked_at:
            self.checked_at = now

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.customer.usage_no} [{self.sequence}]"


class Photo(models.Model):
    PHOTO_TYPE_CHOICES = [
        ('before',      '施工前'),
        ('union_rust',  'ユニオン錆確認'),
        ('packing',     'パッキン取付'),
        ('m_attach',    'M取付'),
        ('pre_purge',   'パージ前'),
        ('post_purge',  'パージ後'),
        ('chart',       'チャートor5分指針'),
        ('safety_close','保安閉栓'),
        ('m_open_meter','M栓開+メーター'),
        ('other',       'その他'),
    ]
    assignment = models.ForeignKey(
        Assignment,
        verbose_name="割当",
        on_delete=models.CASCADE,
        related_name='photos'
    )
    photo_type = models.CharField(
        "写真種別",
        max_length=20,
        choices=PHOTO_TYPE_CHOICES
    )
    image = models.ImageField(
        "画像",
        upload_to='photos/%Y/%m/%d/'
    )
    timestamp = models.DateTimeField(
        "撮影日時",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "写真"
        verbose_name_plural = "写真一覧"

    def __str__(self):
        return f"{self.assignment} - {self.photo_type}"
