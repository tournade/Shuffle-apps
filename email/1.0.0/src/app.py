import time
import glom
import json
import random
import socket
import asyncio
import requests
import datetime

import imaplib
import smtplib
import eml_parser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from walkoff_app_sdk.app_base import AppBase


def default(o):
    """helpers to store item in json
    arguments:
    - o: field of the object to serialize
    returns:
    - valid serialized value for unserializable fields
    """
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, set):
        return list(o)
    if isinstance(o, bytes):
        return o.decode("utf-8")


class Email(AppBase):
    __version__ = "1.0.0"
    app_name = "email"

    def __init__(self, redis, logger, console_logger=None):
        """
        Each app should have this __init__ to set up Redis and logging.
        :param redis:
        :param logger:
        :param console_logger:
        """
        super().__init__(redis, logger, console_logger)

    # This is an email function of Shuffle
    async def send_email_shuffle(self, apikey, recipients, subject, body):
        targets = [recipients]
        if ", " in recipients:
            targets = recipients.split(", ")
        elif "," in recipients:
            targets = recipients.split(",")

        data = {"targets": targets, "body": body, "subject": subject, "type": "alert"}

        url = "https://shuffler.io/functions/sendmail"
        headers = {"Authorization": "Bearer %s" % apikey}
        return requests.post(url, headers=headers, json=data).text

    async def send_email(
        self, username, password, smtp_host, recipient, subject, body, smtp_port
    ):
        if type(smtp_port) == str:
            try:
                smtp_port = int(smtp_port)
            except ValueError:
                return "SMTP port needs to be a number (Current: %s)" % smtp_port

        try:
            s = smtplib.SMTP(host=smtp_host, port=smtp_port)
        except socket.gaierror:
            return "Bad SMTP host or port"

        s.starttls()

        try:
            s.login(username, password)
        except smtplib.SMTPAuthenticationError:
            return "Bad username or password"

        # setup the parameters of the message
        msg = MIMEMultipart()
        msg["From"] = username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        s.send_message(msg)
        print("Successfully sent email with subject %s to %s" % (subject, recipient))
        return "Email sent to %s!" % recipient

    async def get_emails_imap(
        self,
        username,
        password,
        imap_server,
        foldername,
        amount,
        unread,
        fields,
        include_raw_body,
        include_attachment_data,
    ):
        if type(amount) == str:
            try:
                amount = int(amount)
            except ValueError:
                return "Amount needs to be a number, not %s" % amount

        try:
            email = imaplib.IMAP4_SSL(imap_server)
        except ConnectionRefusedError as error:
            try:
                email = imaplib.IMAP4(imap_server)
                email.starttls()
            except socket.gaierror as error:
                return "Can't connect to IMAP server %s: %s" % (imap_server, error)
        except socket.gaierror as error:
            return "Can't connect to IMAP server %s: %s" % (imap_server, error)

        try:
            email.login(username, password)
        except imaplib.IMAP4.error as error:
            return "Failed to log into %s: %s" % (username, error)

        email.select(foldername)
        unread = True if unread.lower().strip() == "true" else False
        try:
            # IMAP search queries, e.g. "seen" or "read"
            # https://www.rebex.net/secure-mail.net/features/imap-search.aspx
            mode = "(UNSEEN)" if unread else "ALL"
            thistype, data = email.search(None, mode)
        except imaplib.IMAP4.error as error:
            return "Couldn't find folder %s." % (foldername)

        email_ids = data[0]
        id_list = email_ids.split()
        if id_list == None:
            return "Couldn't retrieve email. Data: %s" % data

        try:
            print("LIST: ", len(id_list))
        except TypeError:
            return "Error getting email. Data: %s" % data

        emails = []
        error = None

        if type(fields) == str and fields.strip() != "":
            fields = {k.strip(): k.strip() for k in fields.split(",")}
        else:
            fields = None
        include_raw_body = True if include_raw_body.lower().strip() == "true" else False
        include_attachment_data = (
            True if include_attachment_data.lower().strip() == "true" else False
        )

        ep = eml_parser.EmlParser(
            include_attachment_data=include_attachment_data,
            include_raw_body=include_raw_body,
        )

        for i in range(len(id_list) - 1, len(id_list) - amount - 1, -1):
            resp, data = email.fetch(id_list[i], "(RFC822)")
            if resp != "OK":
                print("Failed getting %s" % id_list[i])
                continue

            if data == None:
                continue

            # Convert email in json
            try:
                data = json.loads(
                    json.dumps(ep.decode_email_bytes(data[0][1]), default=default)
                )
            except UnicodeDecodeError as err:
                print("Failed to decode part of email %s" % id_list[i])
                error = "Failed to decode email %s" % id_list[i]
            except IndexError as err:
                print("Indexerror: %s" % err)
                error = "Something went wrong while parsing. Check logs."

            # Pick only selected fields if specified
            try:
                data = glom.glom(data, fields) if fields else parsed_eml
            except glom.core.PathAccessError:
                print("Required fields are not valid")
                error = "Required fields are not valid"

            if error:
                emails.append({"id": id_list[i].decode("utf-8"), "error": error})
            else:
                emails.append(data)

        return json.dumps(emails)


# Run the actual thing after we've checked params
def run(request):
    action = request.get_json()
    authorization_key = action.get("authorization")
    current_execution_id = action.get("execution_id")

    if action and "name" in action and "app_name" in action:
        asyncio.run(Email.run(action), debug=True)
        return f'Attempting to execute function {action["name"]} in app {action["app_name"]}'
    else:
        return f"Invalid action"


if __name__ == "__main__":
    asyncio.run(Email.run(), debug=True)
