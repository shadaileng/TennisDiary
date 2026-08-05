"""运行时目录自动创建"""

import os

from app.core.config import settings

# 上传目录下的子目录列表
_UPLOAD_SUBDIRS = ["images", "videos", "frames"]


def ensure_dirs():
    """确保所有运行时需要的目录存在（幂等，exist_ok=True）

    创建：
    - DATA_DIR（数据库目录）
    - UPLOAD_DIR（上传根目录）
    - UPLOAD_DIR/images、UPLOAD_DIR/videos、UPLOAD_DIR/frames
    """
    # DATA_DIR
    data_dir = os.path.abspath(settings.DATA_DIR)
    os.makedirs(data_dir, exist_ok=True)

    # UPLOAD_DIR + 子目录
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    for subdir in _UPLOAD_SUBDIRS:
        os.makedirs(os.path.join(upload_dir, subdir), exist_ok=True)

    # LOG_DIR（日志目录）
    log_dir = os.path.abspath(settings.LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
