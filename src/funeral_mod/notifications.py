# Copyright (c) CommunityPoke contributors.
"""Toast/notification helpers built on the game's UiDialogNotification."""

from ui.ui_dialog_notification import UiDialogNotification

import sims4.log

from funeral_mod.factories import create_factory_wrapper
from funeral_mod.localize import localized_factory

logger = sims4.log.Logger('funeral_mod.notifications')


def _notification_factory(text, title=None):
    tuned = {
        'text': localized_factory(text),
    }
    if title is not None:
        tuned['title'] = localized_factory(title)
    try:
        return create_factory_wrapper(UiDialogNotification, **tuned)
    except Exception:
        logger.exception('failed to build notification factory')
        return None


def show_notification(owner, text, title=None):
    """Display a notification owned by ``owner`` (a Sim or SimInfo).

    Failures are logged and swallowed — a missing notification should never
    break the funeral itself.
    """
    if owner is None:
        return
    factory = _notification_factory(text, title=title)
    if factory is None:
        return
    try:
        dialog = factory(owner)
        try:
            dialog.urgency = UiDialogNotification.UiDialogNotificationUrgency.URGENT
        except Exception:
            pass
        dialog.show_dialog()
    except Exception:
        logger.exception('failed to show notification')
