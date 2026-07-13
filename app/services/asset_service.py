import os
import uuid
import shutil
import logging
from typing import Optional
from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AssetService:
    """Local file storage for job images and profile pictures."""

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "mp4", "mov", "pdf"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    @staticmethod
    def _ensure_dir(path: str):
        """Create directory if it doesn't exist."""
        os.makedirs(path, exist_ok=True)

    @staticmethod
    async def save_upload(
        file: UploadFile,
        subfolder: str = "jobs",
    ) -> Optional[str]:
        """
        Save an uploaded file to the local filesystem.

        Args:
            file: FastAPI UploadFile
            subfolder: Subdirectory (e.g. 'jobs', 'profiles')

        Returns:
            Relative URL path to the saved file, or None on failure.
        """
        try:
            # Validate extension
            filename = file.filename or "unnamed"
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in AssetService.ALLOWED_EXTENSIONS:
                logger.warning(f"Rejected file with extension: {ext}")
                return None

            # Read file content
            content = await file.read()
            if len(content) == 0:
                logger.warning("Rejected empty file")
                return None
            if len(content) > AssetService.MAX_FILE_SIZE:
                logger.warning(f"Rejected file too large: {len(content)} bytes")
                return None

            # Magic byte validation — verify actual file type matches extension
            if not AssetService._validate_magic_bytes(content, ext):
                logger.warning(f"Rejected file: magic bytes don't match extension '{ext}'")
                return None

            # Generate unique filename
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            upload_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
            AssetService._ensure_dir(upload_dir)

            file_path = os.path.join(upload_dir, unique_name)

            # Write file
            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"✓ Saved file: {file_path} ({len(content)} bytes)")

            # Return the URL path (relative to static mount)
            return f"/static/uploads/{subfolder}/{unique_name}"

        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return None

    @staticmethod
    def delete_file(file_url: str) -> bool:
        """
        Delete a file from the local filesystem.

        Args:
            file_url: URL path (e.g. '/static/uploads/jobs/abc.jpg')

        Returns:
            True if deleted, False otherwise.
        """
        try:
            # Convert URL path to filesystem path
            # /static/uploads/jobs/abc.jpg -> ./uploaded_images/jobs/abc.jpg
            relative_path = file_url.replace("/static/uploads/", "")
            file_path = os.path.join(settings.UPLOAD_DIR, relative_path)

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✓ Deleted file: {file_path}")
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    @staticmethod
    def get_file_path(file_url: str) -> Optional[str]:
        """Convert a URL path to a filesystem path."""
        relative_path = file_url.replace("/static/uploads/", "")
        file_path = os.path.join(settings.UPLOAD_DIR, relative_path)
        return file_path if os.path.exists(file_path) else None

    @staticmethod
    def _validate_magic_bytes(content: bytes, ext: str) -> bool:
        """
        Validate that the file's binary signature (magic bytes) matches the claimed extension.
        Prevents users from uploading executables disguised as images.
        """
        magic_map = {
            "jpg":  [b"\xff\xd8\xff"],
            "jpeg": [b"\xff\xd8\xff"],
            "png":  [b"\x89PNG\r\n\x1a\n"],
            "gif":  [b"GIF87a", b"GIF89a"],
            "webp": [b"RIFF"],  # RIFF....WEBP
            "mp4":  [b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x1cftyp", b"\x00\x00\x00\x20ftyp", b"ftyp"],
            "mov":  [b"\x00\x00\x00\x14ftyp", b"moov", b"ftyp"],
            "pdf":  [b"%PDF"],
        }
        signatures = magic_map.get(ext)
        if not signatures:
            return False  # Unknown extension — reject

        for sig in signatures:
            if content[:len(sig)] == sig:
                return True
            # For MP4/MOV, also check bytes 4-8
            if ext in ("mp4", "mov") and len(content) > 8:
                if sig in content[:12]:
                    return True
        return False
