"""校验前端权限码与数据库按钮表的一致性。

扫描前端源码中所有权限码引用（hasPermission / v-auth / :auth / auth），
检查它们是否都存在于数据库 Menu(type=button).auth_code 中。

权限码规范见 docs/docs/essential/permission_code_convention.md：
    <app_label>:<model_name>:<action>
其中 model_name 必须为下划线 snake_case（如 code_repository、release_record）。

用法：
    python manage.py check_permission_codes
    python manage.py check_permission_codes --frontend-dir /abs/path/to/src
存在缺失时退出码为 1，可用于 CI 卡点。
"""
import os
import re
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from system.models import Menu, MenuType

# 匹配前端权限码引用的正则（精确提取码字符串）
PATTERNS = [
    re.compile(r"hasPermission\(\s*['\"]([^'\"]+)['\"]\s*\)"),
    re.compile(r"v-auth\s*=\s*\[['\"]([^'\"]+)['\"]\]"),
    re.compile(r"\bauth\s*[:=]\s*\[['\"]([^'\"]+)['\"]\]"),
]

# 合法的权限码格式：app:model:action（允许段内连字符，用于自定义 action）
CODE_RE = re.compile(r"^[a-zA-Z_][\w-]*:[a-zA-Z_][\w-]*:[a-zA-Z_][\w-]*$")

DEFAULT_FRONTEND_REL = os.path.join("..", "web", "apps", "web-antd", "src")
SCAN_EXTS = (".vue", ".ts")


class Command(BaseCommand):
    help = "校验前端权限码是否都存在于数据库按钮表中"

    def add_arguments(self, parser):
        parser.add_argument(
            "--frontend-dir",
            default=None,
            help="前端 src 目录绝对路径（默认：<backend>/../web/apps/web-antd/src）",
        )

    def handle(self, *args, **options):
        frontend_dir = options["frontend_dir"] or os.path.abspath(
            os.path.join(settings.BASE_DIR, DEFAULT_FRONTEND_REL)
        )
        if not os.path.isdir(frontend_dir):
            self.stderr.write(self.style.WARNING(
                f"前端目录不存在，跳过校验：{frontend_dir}"
            ))
            return

        # 数据库已有按钮权限码集合
        db_codes = set(
            Menu.objects.filter(type=MenuType.BUTTON)
            .values_list("auth_code", flat=True)
        )

        # 扫描前端，收集 (code, file, line)
        referenced = {}  # code -> list of "file:line"
        for root, _dirs, files in os.walk(frontend_dir):
            for fname in files:
                if not fname.endswith(SCAN_EXTS):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except (OSError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(fpath, frontend_dir)
                for idx, line in enumerate(lines, start=1):
                    for pat in PATTERNS:
                        for m in pat.finditer(line):
                            code = m.group(1).strip()
                            if CODE_RE.match(code) and code not in db_codes:
                                referenced.setdefault(code, []).append(f"{rel}:{idx}")

        if not referenced:
            self.stdout.write(self.style.SUCCESS(
                "✅ 校验通过：前端引用的所有权限码均存在于数据库按钮表中。"
            ))
            return

        self.stderr.write(self.style.ERROR(
            "❌ 发现前端引用但数据库缺失的权限码（共 %d 个）：" % len(referenced)
        ))
        for code in sorted(referenced):
            self.stderr.write(f"  • {code}")
            for loc in referenced[code]:
                self.stderr.write(f"      └─ {loc}")
        self.stderr.write("")
        self.stderr.write(
            "请按规范 docs/docs/essential/permission_code_convention.md 修正："
            "model_name 段使用下划线（如 code_repository、release_record）。"
        )
        sys.exit(1)
