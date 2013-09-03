import logging

from django.conf import settings
from django.utils.translation import ugettext as _

import mandrill
import vanilla_django


log = logging.getLogger(__name__)


class TemplateBackend(vanilla_django.TemplateBackend):
    def __init__(self, *args, **kwargs):
        vanilla_django.TemplateBackend.__init__(self, *args, **kwargs)
        self.client = mandrill.Mandrill(settings.MANDRILL_API_KEY)

    def send(self, template_name, from_email, recipient_list, context, cc=None,
            bcc=None, fail_silently=False, headers=None, template_prefix=None,
            template_suffix=None, template_dir=None, file_extension=None,
            extra_params=None, dry_run=False, **kwargs):

        # some internal basic defaults
        config = {
            'subject': _('%s email' % template_name),
        }

        base_config = getattr(settings, 'TEMPLATED_EMAIL_MANDRILL', {})
        # get general message defaults from settings:
        config.update(base_config.get('_default', {}))
        # get template-specific message defaults from settings:
        config.update(base_config.get(template_name, {}))

        message = config.copy()
        message.update({
            'from_name': ' '.join(from_email.split(' ')[:-1]) or 'Nobody',
            'from_email': from_email,
            'to': recipient_list,
        })
        if 'message' not in context:
            context['message'] = message

        parts = self._render_email(template_name, context,
                                   template_dir=template_prefix or template_dir,
                                   file_extension=template_suffix or file_extension)

        message['html'] = parts.get('html', '')
        message['text'] = parts.get('plain', '')
        if cc:
            message['cc_address'] = ', '.join(cc)
        if bcc:
            message['bcc_address'] = ', '.join(bcc)
        if headers:
            message['headers'] = headers
        if extra_params:
            message.update(extra_params)

        if dry_run:
            return
        try:
            return self.client.messages.send(message=message, **kwargs)
        except mandrill.Error as e:
            log.error(e)
            if not fail_silently:
                raise

