"""Callback functions needed during creation of a Poll."""
from telegram import InlineKeyboardMarkup

from pollbot.helper import poll_required
from pollbot.helper.update import update_poll_messages
from pollbot.helper.display import get_settings_text
from pollbot.telegram.keyboard import (
    get_anonymization_confirmation_keyboard,
    get_settings_keyboard,
    get_option_sorting_keyboard,
    get_back_to_settings_button,
    get_remove_option_keyboad,
)
from pollbot.helper.enums import OptionSorting, UserSorting, ExpectedInput
from pollbot.models import PollOption


@poll_required
def show_anonymization_confirmation(session, context, poll):
    """Show the delete confirmation message."""
    context.query.message.edit_text(
        'Do you really want to anonymize this poll?\n⚠️ This action is unrevertable. ⚠️',
        reply_markup=get_anonymization_confirmation_keyboard(poll),
    )


@poll_required
def make_anonymous(session, context, poll):
    """Change the anonymity settings of a poll."""
    poll.anonymous = True

    context.query.message.edit_text(
        get_settings_text(poll),
        parse_mode='markdown',
        reply_markup=get_settings_keyboard(poll)
    )

    update_poll_messages(session, context.bot, poll)


@poll_required
def show_sorting_menu(session, context, poll):
    """Show the menu for sorting settings."""
    context.query.message.edit_reply_markup(
        parse_mode='markdown',
        reply_markup=get_option_sorting_keyboard(poll)
    )


@poll_required
def set_user_order(session, context, poll):
    """Set the order in which user are listed."""
    user_sorting = UserSorting(context.action)
    poll.user_sorting = user_sorting.name

    context.query.message.edit_text(
        text=get_settings_text(poll),
        parse_mode='markdown',
        reply_markup=get_option_sorting_keyboard(poll)
    )
    update_poll_messages(session, context.bot, poll)


@poll_required
def set_option_order(session, context, poll):
    """Set the order in which options are listed."""
    option_sorting = OptionSorting(context.action)
    poll.option_sorting = option_sorting.name

    context.query.message.edit_text(
        text=get_settings_text(poll),
        parse_mode='markdown',
        reply_markup=get_option_sorting_keyboard(poll)
    )

    update_poll_messages(session, context.bot, poll)


@poll_required
def expect_new_option(session, context, poll):
    """Send a text and tell the user that we expect a new option."""
    context.user.expected_input = ExpectedInput.new_option.name
    context.user.current_poll = poll

    keyboard = InlineKeyboardMarkup([[get_back_to_settings_button(poll)]])
    context.query.message.edit_text(
        text='Please send me the new option or multiple options at once, each option in a new line.)',
        parse_mode='markdown',
        reply_markup=keyboard,
    )


@poll_required
def show_remove_options_menu(session, context, poll):
    """Show the menu for removing options."""
    keyboard = get_remove_option_keyboad(poll)
    context.query.message.edit_text(
        text='Just click the buttons below to remove the desired options.',
        parse_mode='markdown',
        reply_markup=keyboard,
    )


@poll_required
def remove_option(session, context, poll):
    """Remove the option."""
    session.query(PollOption) \
        .filter(PollOption.id == context.action) \
        .delete()
    session.commit()

    keyboard = get_remove_option_keyboad(poll)
    context.query.message.edit_reply_markup(reply_markup=keyboard)

    update_poll_messages(session, context.bot, poll)


@poll_required
def toggle_percentage(session, context, poll):
    """Toggle the visibility of the percentage bar."""
    poll = poll
    poll.show_percentage = not poll.show_percentage

    update_poll_messages(session, context.bot, poll)
    context.query.message.edit_text(
        text=get_settings_text(poll),
        parse_mode='markdown',
        reply_markup=get_settings_keyboard(poll)
    )


@poll_required
def toggle_allow_new_options(session, context, poll):
    """Toggle the visibility of the percentage bar."""
    poll.allow_new_options = not poll.allow_new_options

    update_poll_messages(session, context.bot, poll)
    context.query.message.edit_text(
        text=get_settings_text(poll),
        parse_mode='markdown',
        reply_markup=get_settings_keyboard(poll)
    )