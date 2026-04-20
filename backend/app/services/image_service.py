import os
import uuid
from datetime import datetime
from werkzeug.datastructures import FileStorage
from flask import current_app

from ..models.image import Image
from ..extensions import db


class ImageService:

    @staticmethod
    def save_image(file: FileStorage, dataset_id: int) -> Image:
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        dataset_folder = os.path.join(upload_folder, str(dataset_id))
        os.makedirs(dataset_folder, exist_ok=True)

        ext = os.path.splitext(file.filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(dataset_folder, unique_name)
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        mime_type = file.mimetype or ImageService._guess_mime(ext)

        # Extract metadata
        width, height, bands, band_names = ImageService._extract_dimensions(file_path, ext)
        thumbnail_path = ImageService._generate_thumbnail(file_path, dataset_folder, unique_name)

        image = Image(
            filename=unique_name,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            bands=bands,
            band_names=band_names,
            thumbnail_path=thumbnail_path,
            dataset_id=dataset_id,
        )
        db.session.add(image)
        db.session.commit()
        return image

    @staticmethod
    def delete_image(image: Image):
        """Remove image file from disk and delete DB record."""
        for path in (image.file_path, image.thumbnail_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        db.session.delete(image)
        db.session.commit()

    @staticmethod
    def _guess_mime(ext: str) -> str:
        mapping = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".tif": "image/tiff",
            ".tiff": "image/tiff", ".nc": "application/x-netcdf",
            ".h5": "application/x-hdf5", ".hdf5": "application/x-hdf5",
        }
        return mapping.get(ext, "application/octet-stream")

    @staticmethod
    def _extract_dimensions(file_path: str, ext: str):
        """Extract image dimensions and band info using available libraries."""
        width, height, bands, band_names = None, None, 1, None

        try:
            if ext in (".tif", ".tiff"):
                try:
                    import rasterio
                    with rasterio.open(file_path) as ds:
                        width = ds.width
                        height = ds.height
                        bands = ds.count
                        band_names = list(ds.descriptions) if ds.descriptions else None
                except ImportError:
                    pass
            elif ext in (".png", ".jpg", ".jpeg"):
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(file_path) as img:
                        width, height = img.size
                        bands = len(img.getbands())
                except ImportError:
                    pass
            elif ext in (".nc",):
                try:
                    import netCDF4 as nc
                    ds = nc.Dataset(file_path)
                    # Try to extract spatial dims from common variable names
                    for var in ds.variables.values():
                        if len(var.shape) >= 2:
                            height, width = var.shape[-2], var.shape[-1]
                            break
                    ds.close()
                except ImportError:
                    pass
        except Exception:
            pass

        return width, height, bands, band_names

    @staticmethod
    def _generate_thumbnail(file_path: str, folder: str, base_name: str) -> str:
        thumbnail_path = os.path.join(folder, f"thumb_{base_name}.jpg")
        try:
            from PIL import Image as PILImage
            with PILImage.open(file_path) as img:
                img.thumbnail((256, 256))
                img.convert("RGB").save(thumbnail_path, "JPEG", quality=80)
            return thumbnail_path
        except Exception:
            return None
