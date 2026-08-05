"""测试运行时目录自动创建逻辑"""

import os
import tempfile
import shutil

from app.core.config import settings
from app.core.dirs import ensure_dirs


class TestEnsureDirs:
    """测试 ensure_dirs 函数"""

    def test_create_data_dir(self, monkeypatch):
        """DATA_DIR 不存在时应自动创建"""
        tmpdir = tempfile.mkdtemp()
        data_dir = os.path.join(tmpdir, "data")
        monkeypatch.setattr(settings, "DATA_DIR", data_dir)
        monkeypatch.setattr(settings, "UPLOAD_DIR", os.path.join(data_dir, "uploads"))

        try:
            ensure_dirs()
            assert os.path.isdir(data_dir)
            assert os.path.isdir(os.path.join(data_dir, "uploads"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_create_upload_subdirs(self, monkeypatch):
        """UPLOAD_DIR 及其子目录应自动创建"""
        tmpdir = tempfile.mkdtemp()
        data_dir = os.path.join(tmpdir, "data")
        upload_dir = os.path.join(data_dir, "uploads")
        monkeypatch.setattr(settings, "DATA_DIR", data_dir)
        monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)

        try:
            ensure_dirs()
            assert os.path.isdir(upload_dir)
            assert os.path.isdir(os.path.join(upload_dir, "images"))
            assert os.path.isdir(os.path.join(upload_dir, "videos"))
            assert os.path.isdir(os.path.join(upload_dir, "frames"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_existing_dirs_are_safe(self, monkeypatch):
        """已存在的目录再次创建不应报错（exist_ok 行为）"""
        tmpdir = tempfile.mkdtemp()
        data_dir = os.path.join(tmpdir, "data")
        monkeypatch.setattr(settings, "DATA_DIR", data_dir)
        monkeypatch.setattr(settings, "UPLOAD_DIR", os.path.join(data_dir, "uploads"))

        try:
            ensure_dirs()
            # 第二次调用不应报错
            ensure_dirs()
            assert os.path.isdir(data_dir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upload_dir_can_be_absolute(self, monkeypatch):
        """UPLOAD_DIR 为绝对路径时也应正常创建"""
        tmpdir = tempfile.mkdtemp()
        upload_dir = os.path.join(tmpdir, "custom_uploads")
        monkeypatch.setattr(settings, "DATA_DIR", os.path.join(tmpdir, "data"))
        monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)

        try:
            ensure_dirs()
            assert os.path.isdir(upload_dir)
            assert os.path.isdir(os.path.join(upload_dir, "images"))
            assert os.path.isdir(os.path.join(upload_dir, "videos"))
            assert os.path.isdir(os.path.join(upload_dir, "frames"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
