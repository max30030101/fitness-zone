
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        api_key = os.environ.get("RESEND_API_KEY")
        default_sender = os.environ.get("RESEND_FROM_EMAIL")

        if not api_key:
            raise ImproperlyConfigured("RESEND_API_KEY is missing.")

        sent = 0

        for message in email_messages:
            sender = default_sender or message.from_email
            if not sender:
                raise ImproperlyConfigured("RESEND_FROM_EMAIL is missing.")

            payload = {
                "from": sender,
                "to": message.to,
                "subject": message.subject,
                "text": message.body or "",
            }

            if message.cc:
                payload["cc"] = message.cc

            if message.bcc:
                payload["bcc"] = message.bcc

            for content, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    payload["html"] = content

            request = Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            try:
                with urlopen(request, timeout=20) as response:
                    if 200 <= response.status < 300:
                        sent += 1
                    else:
                        raise OSError(
                            f"Resend returned HTTP {response.status}"
                        )

            except HTTPError as exc:
                details = exc.read().decode(
                    "utf-8", errors="replace"
                )
                raise OSError(
                    f"Resend API error {exc.code}: {details[:400]}"
                ) from None

            except (URLError, TimeoutError) as exc:
                raise OSError(
                    f"Resend connection failed: {exc}"
                ) from None

        return sent
