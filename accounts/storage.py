import mimetypes
from io import BytesIO

from django.core.files import File
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseProfilePhotoStorage(Storage):
    def _save(self, name, content):
        from .models import StoredProfilePhoto

        data = b"".join(content.chunks())
        content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        StoredProfilePhoto.objects.update_or_create(
            name=name,
            defaults={"content": data, "content_type": content_type},
        )
        return name

    def _open(self, name, mode="rb"):
        from .models import StoredProfilePhoto

        try:
            photo = StoredProfilePhoto.objects.get(name=name)
        except StoredProfilePhoto.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        stored_file = File(BytesIO(bytes(photo.content)), name=name)
        stored_file.content_type = photo.content_type
        return stored_file

    def delete(self, name):
        from .models import StoredProfilePhoto

        StoredProfilePhoto.objects.filter(name=name).delete()

    def exists(self, name):
        from .models import StoredProfilePhoto

        return StoredProfilePhoto.objects.filter(name=name).exists()

    def url(self, name):
        prefix = "profile_photos/"
        if not name.startswith(prefix):
            raise ValueError("Database profile photo names must start with 'profile_photos/'.")
        return reverse("accounts:profile_photo", kwargs={"filename": name})
