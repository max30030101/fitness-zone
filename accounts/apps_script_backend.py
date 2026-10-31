
import json
import os
import urllib.request
from django.core.mail.backends.base import BaseEmailBackend


class AppsScriptEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        script_url = os.environ.get("APPS_SCRIPT_URL")
        secret = os.environ.get("APPS_SCRIPT_SECRET")

        if not script_url or not secret:
            raise ValueError("Apps Script email settings are missing.")

        sent_count = 0

        for message in email_messages:
            html_body = ""

            for content, content_type in getattr(
                message, "alternatives", []
            ):
                if content_type == "text/html":
                    html_body = content
                    break

            data = {
                "token": secret,
                "to": ",".join(message.to),
                "subject": message.subject,
                "text": message.body or "",
                "html": html_body or message.body or "",
            }

            request = urllib.request.Request(
                script_url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(
                    request, timeout=30
                ) as response:
                    result = json.loads(
                        response.read().decode("utf-8")
                    )

                if not result.get("success"):
                    raise RuntimeError(
                        result.get("error", "Email sending failed.")
                    )

                sent_count += 1

            except Exception as error:
                if not self.fail_silently:
                    raise error

        return sent_count
