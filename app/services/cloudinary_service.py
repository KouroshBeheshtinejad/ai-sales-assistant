import os
from io import BytesIO

import cloudinary
import cloudinary.uploader


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_image(
    content: bytes,
    *,
    public_id: str,
    folder: str,
) -> str:
    _configure_cloudinary()

    result = cloudinary.uploader.upload(
        BytesIO(content),
        public_id=public_id,
        folder=folder,
        resource_type="image",
        overwrite=True,
        invalidate=True,
    )

    return result["secure_url"]


def delete_image(image_url: str | None) -> None:
    if not image_url or "res.cloudinary.com" not in image_url:
        return

    _configure_cloudinary()

    parts = image_url.split("/upload/", 1)
    if len(parts) != 2:
        return

    path = parts[1]
    segments = path.split("/")

    while segments and segments[0].startswith("v") and segments[0][1:].isdigit():
        segments.pop(0)

    public_id_with_extension = "/".join(segments)

    if "." in public_id_with_extension:
        public_id = public_id_with_extension.rsplit(".", 1)[0]
    else:
        public_id = public_id_with_extension

    cloudinary.uploader.destroy(
        public_id,
        resource_type="image",
        invalidate=True,
    )
