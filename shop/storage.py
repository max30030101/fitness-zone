import mimetypes
from io import BytesIO

from django.core.files import File
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseProductImageStorage(Storage):
    def _save(self, name, content):
        from .models import StoredProductImage

        data = b"".join(content.chunks())
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        StoredProductImage.objects.update_or_create(
            name=name,
            defaults={"content": data, "content_type": content_type},
        )
        return name

    def _open(self, name, mode="rb"):
        from .models import StoredProductImage

        try:
            image = StoredProductImage.objects.get(name=name)
        except StoredProductImage.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        stored_file = File(BytesIO(bytes(image.content)), name=name)
        stored_file.content_type = image.content_type
        return stored_file

    def delete(self, name):
        from .models import StoredProductImage

        StoredProductImage.objects.filter(name=name).delete()

    def exists(self, name):
        from .models import StoredProductImage

        return StoredProductImage.objects.filter(name=name).exists()

    def url(self, name):
        prefix = "products/"
        if not name.startswith(prefix):
            raise ValueError("Database product image names must start with 'products/'.")
        return reverse("shop:product_image", kwargs={"filename": name[len(prefix):]})
