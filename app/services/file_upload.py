import os
import uuid
import aiofiles
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from PIL import Image, ImageOps
import io
from pydub import AudioSegment
import speech_recognition as sr
import logging

logger = logging.getLogger(__name__)


class FileUploadService:
    """Service for handling file uploads for chat messages"""
    
    def __init__(self):
        self.upload_dir = "uploads/messages_data"
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.max_audio_size = 20 * 1024 * 1024  # 20MB
        
        # Create upload directories
        os.makedirs(f"{self.upload_dir}/images", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/thumbnails", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/files", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/audio", exist_ok=True)
        os.makedirs(f"{self.upload_dir}/video", exist_ok=True)
    
    async def upload_image(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Upload and process an image file"""
        try:
            # Validate file size
            if file.size > self.max_image_size:
                raise HTTPException(status_code=413, detail="Image file too large")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                raise HTTPException(status_code=400, detail="Invalid image format")
            
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{self.upload_dir}/images/{unique_filename}"
            
            # Save original file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Generate thumbnail
            thumbnail_path = await self._generate_thumbnail(file_path, unique_filename)
            
            # Get image dimensions
            with Image.open(file_path) as img:
                width, height = img.size
            
            return {
                "file_url": f"/uploads/images/{unique_filename}",
                "thumbnail_url": f"/uploads/thumbnails/{unique_filename}",
                "file_name": file.filename,
                "file_size": file.size,
                "file_type": file.content_type,
                "width": width,
                "height": height,
                "uploaded_by": user_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image")
    
    async def upload_file(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Upload a general file"""
        try:
            # Validate file size
            if file.size > self.max_file_size:
                raise HTTPException(status_code=413, detail="File too large")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
            unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
            file_path = f"{self.upload_dir}/files/{unique_filename}"
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            return {
                "file_url": f"/uploads/files/{unique_filename}",
                "file_name": file.filename,
                "file_size": file.size,
                "file_type": file.content_type,
                "uploaded_by": user_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    async def upload_audio(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Upload and process an audio file"""
        try:
            # Validate file size
            if file.size > self.max_audio_size:
                raise HTTPException(status_code=413, detail="Audio file too large")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                raise HTTPException(status_code=400, detail="Invalid audio format")
            
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{self.upload_dir}/audio/{unique_filename}"
            
            # Save original file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Process audio
            audio_info = await self._process_audio(file_path, content)
            
            return {
                "file_url": f"/uploads/audio/{unique_filename}",
                "file_name": file.filename,
                "file_size": file.size,
                "file_type": file.content_type,
                "duration": audio_info.get("duration"),
                "waveform": audio_info.get("waveform"),
                "transcription": audio_info.get("transcription"),
                "uploaded_by": user_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading audio: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload audio")
    
    async def upload_video(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Upload and process a video file"""
        try:
            # Validate file size
            if file.size > self.max_file_size:
                raise HTTPException(status_code=413, detail="Video file too large")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
                raise HTTPException(status_code=400, detail="Invalid video format")
            
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"{self.upload_dir}/video/{unique_filename}"
            
            # Save original file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Generate video thumbnail
            thumbnail_path = await self._generate_video_thumbnail(file_path, unique_filename)
            
            return {
                "file_url": f"/uploads/video/{unique_filename}",
                "thumbnail_url": f"/uploads/thumbnails/video_{unique_filename}.jpg",
                "file_name": file.filename,
                "file_size": file.size,
                "file_type": file.content_type,
                "uploaded_by": user_id
            }
            
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload video")
    
    async def _generate_thumbnail(self, image_path: str, filename: str) -> str:
        """Generate thumbnail for an image"""
        try:
            thumbnail_filename = f"thumb_{filename}"
            thumbnail_path = f"{self.upload_dir}/thumbnails/{thumbnail_filename}"
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    async def _generate_video_thumbnail(self, video_path: str, filename: str) -> str:
        """Generate thumbnail for a video file"""
        try:
            # This would typically use ffmpeg or similar
            # For now, return a placeholder
            thumbnail_filename = f"video_{filename}.jpg"
            thumbnail_path = f"{self.upload_dir}/thumbnails/{thumbnail_filename}"
            
            # Create a placeholder thumbnail
            placeholder = Image.new('RGB', (300, 200), color='gray')
            placeholder.save(thumbnail_path, 'JPEG')
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Error generating video thumbnail: {e}")
            return None
    
    async def _process_audio(self, audio_path: str, audio_content: bytes) -> Dict[str, Any]:
        """Process audio file to extract metadata and generate waveform"""
        try:
            result = {}
            
            # Get audio duration using pydub
            try:
                audio = AudioSegment.from_file(io.BytesIO(audio_content))
                result["duration"] = len(audio) / 1000.0  # Convert to seconds
                
                # Generate simple waveform data
                samples = audio.get_array_of_samples()
                # Downsample for waveform visualization
                step = max(1, len(samples) // 100)  # 100 points for waveform
                waveform = [abs(samples[i]) for i in range(0, len(samples), step)]
                
                # Normalize waveform
                if waveform:
                    max_val = max(waveform)
                    if max_val > 0:
                        waveform = [val / max_val for val in waveform]
                
                result["waveform"] = waveform
                
            except Exception as e:
                logger.warning(f"Could not process audio metadata: {e}")
                result["duration"] = 0
                result["waveform"] = []
            
            # Attempt speech recognition
            try:
                r = sr.Recognizer()
                with sr.AudioFile(audio_path) as source:
                    audio_data = r.record(source, duration=30)  # Limit to 30 seconds
                    text = r.recognize_google(audio_data)
                    result["transcription"] = text
            except Exception as e:
                logger.warning(f"Could not transcribe audio: {e}")
                result["transcription"] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {"duration": 0, "waveform": [], "transcription": None}
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a file"""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            return {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "exists": True
            }
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def validate_file_type(self, filename: str, allowed_types: list) -> bool:
        """Validate file type based on extension"""
        if not filename or '.' not in filename:
            return False
        
        extension = filename.split('.')[-1].lower()
        return extension in allowed_types
    
    def get_file_size_mb(self, size_bytes: int) -> float:
        """Convert bytes to MB"""
        return size_bytes / (1024 * 1024)


# Global file upload service instance
file_upload_service = FileUploadService()