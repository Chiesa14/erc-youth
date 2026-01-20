"""
Profile and Cover Photo Upload Service.
Handles uploading and managing profile photos for family members
and cover photos for families.
"""

import os
import uuid
import aiofiles
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class ProfileUploadService:
    """Service for handling profile and cover photo uploads."""

    def __init__(self):
        self.upload_base = "uploads"
        self.profile_dir = f"{self.upload_base}/profiles"
        self.family_dir = f"{self.upload_base}/families"
        self.user_dir = f"{self.upload_base}/users"
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        self.thumbnail_size = (200, 200)

        # Create upload directories
        os.makedirs(self.profile_dir, exist_ok=True)
        os.makedirs(self.family_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)

    async def upload_profile_photo(
        self,
        file: UploadFile,
        member_id: int
    ) -> Dict[str, Any]:
        """
        Upload a profile photo for a family member.
        
        Args:
            file: The uploaded file
            member_id: The family member's ID
            
        Returns:
            Dict with file URL and metadata
        """
        try:
            # Validate file
            self._validate_image(file)

            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            unique_filename = f"member_{member_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = f"{self.profile_dir}/{unique_filename}"

            # Read and save file
            content = await file.read()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            # Generate thumbnail
            thumbnail_path = self._generate_thumbnail(file_path, unique_filename, "profile")

            # Get image dimensions
            with Image.open(file_path) as img:
                width, height = img.size

            return {
                "file_url": f"/uploads/profiles/{unique_filename}",
                "thumbnail_url": thumbnail_path,
                "file_name": file.filename,
                "file_size": len(content),
                "width": width,
                "height": height,
                "member_id": member_id
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading profile photo: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload profile photo")

    async def upload_family_cover_photo(
        self,
        file: UploadFile,
        family_id: int
    ) -> Dict[str, Any]:
        """
        Upload a cover photo for a family.
        
        Args:
            file: The uploaded file
            family_id: The family's ID
            
        Returns:
            Dict with file URL and metadata
        """
        try:
            # Validate file
            self._validate_image(file)

            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            unique_filename = f"family_{family_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = f"{self.family_dir}/{unique_filename}"

            # Read and save file
            content = await file.read()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            # Generate thumbnail
            thumbnail_path = self._generate_thumbnail(file_path, unique_filename, "family")

            # Get image dimensions
            with Image.open(file_path) as img:
                width, height = img.size

            return {
                "file_url": f"/uploads/families/{unique_filename}",
                "thumbnail_url": thumbnail_path,
                "file_name": file.filename,
                "file_size": len(content),
                "width": width,
                "height": height,
                "family_id": family_id
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading family cover photo: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload family cover photo")

    async def upload_user_profile_photo(
        self,
        file: UploadFile,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Upload a profile photo for a user.
        
        Args:
            file: The uploaded file
            user_id: The user's ID
            
        Returns:
            Dict with file URL and metadata
        """
        try:
            # Validate file
            self._validate_image(file)

            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            unique_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = f"{self.user_dir}/{unique_filename}"

            # Read and save file
            content = await file.read()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)

            # Generate thumbnail
            thumbnail_path = self._generate_thumbnail(file_path, unique_filename, "user")

            # Get image dimensions
            with Image.open(file_path) as img:
                width, height = img.size

            return {
                "file_url": f"/uploads/users/{unique_filename}",
                "thumbnail_url": thumbnail_path,
                "file_name": file.filename,
                "file_size": len(content),
                "width": width,
                "height": height,
                "user_id": user_id
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading user profile photo: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload user profile photo")

    def _validate_image(self, file: UploadFile) -> None:
        """Validate the uploaded image file."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: {', '.join(self.allowed_extensions)}"
            )

        if file.size and file.size > self.max_image_size:
            raise HTTPException(
                status_code=413,
                detail=f"Image file too large. Maximum size: {self.max_image_size // (1024*1024)}MB"
            )

    def _generate_thumbnail(
        self,
        image_path: str,
        filename: str,
        photo_type: str
    ) -> Optional[str]:
        """Generate a thumbnail for the image."""
        try:
            thumb_dir = f"{self.upload_base}/thumbnails"
            os.makedirs(thumb_dir, exist_ok=True)

            thumbnail_filename = f"thumb_{photo_type}_{filename}"
            thumbnail_path = f"{thumb_dir}/{thumbnail_filename}"

            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85)

            return f"/uploads/thumbnails/{thumbnail_filename}"

        except Exception as e:
            logger.warning(f"Could not generate thumbnail: {e}")
            return None

    async def delete_photo(self, file_url: str) -> bool:
        """Delete a photo from storage."""
        try:
            # Convert URL to file path
            if file_url.startswith("/uploads/"):
                file_path = file_url.replace("/uploads/", f"{self.upload_base}/")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted photo: {file_path}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error deleting photo: {e}")
            return False


# Global service instance
profile_upload_service = ProfileUploadService()
