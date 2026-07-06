from email.message import Message
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from beyo_manager.services.infra.email_providers.base import OutboundMessage


class MimeBuilder:
    def build(self, message: OutboundMessage) -> Message:
        root: Message
        if message.html_body is not None:
            root = MIMEMultipart("alternative")
            if message.text_body is not None:
                root.attach(MIMEText(message.text_body, "plain", "utf-8"))
            root.attach(MIMEText(message.html_body, "html", "utf-8"))
        else:
            root = MIMEText(message.text_body or "", "plain", "utf-8")

        root["From"] = (
            formataddr((message.from_name, message.from_address))
            if message.from_name
            else message.from_address
        )
        root["To"] = ", ".join(message.to_addresses)
        if message.cc_addresses:
            root["Cc"] = ", ".join(message.cc_addresses)
        root["Subject"] = message.subject
        root["Message-ID"] = message.rfc_message_id
        if message.in_reply_to:
            root["In-Reply-To"] = message.in_reply_to
        if message.references:
            root["References"] = " ".join(message.references)
        return root
