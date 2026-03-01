# -*- coding: utf-8 -*-
default_app_config = 'release.apps.ReleaseConfig'

# 显式导入 Celery tasks，确保 autodiscover_tasks 能发现
from . import tasks
