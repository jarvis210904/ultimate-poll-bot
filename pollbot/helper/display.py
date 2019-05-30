"""Poll creation helper."""
import math
from telegram.error import BadRequest

from pollbot.telegram.keyboard import get_vote_keyboard, get_management_keyboard
from pollbot.helper.enums import (
    ExpectedInput,
    VoteTypeTranslation,
    UserSorting,
    OptionSorting,
    SortOptionTranslation,
)
from pollbot.models import (
    User,
    PollOption,
    Vote,
)


def update_poll_messages(session, bot, poll):
    """Update all messages (references) of a poll."""
    for reference in poll.references:
        try:
            # Admin poll management interface
            if reference.admin_message_id is not None and not poll.in_options:
                if poll.expected_input == ExpectedInput.votes.name:
                    keyboard = get_vote_keyboard(poll, show_back=True)
                else:
                    keyboard = get_management_keyboard(poll)

                text = get_poll_management_text(session, poll)
                bot.edit_message_text(
                    text,
                    chat_id=reference.admin_chat_id,
                    message_id=reference.admin_message_id,
                    reply_markup=keyboard,
                    parse_mode='markdown',
                )

            # Edit message via inline_message_id
            elif reference.inline_message_id is not None:
                # Create text and keyboard
                text = get_poll_text(session, poll)
                keyboard = get_vote_keyboard(poll)

                bot.edit_message_text(
                    text,
                    inline_message_id=reference.inline_message_id,
                    reply_markup=keyboard,
                    parse_mode='markdown',
                )
        except BadRequest as e:
            if e.message.startswith('Message_id_invalid'):
                session.delete(reference)
                session.commit()
            else:
                raise


def remove_poll_messages(session, bot, poll):
    """Remove all messages (references) of a poll."""
    for reference in poll.references:
        try:
            # Admin poll management interface
            if reference.inline_message_id is None:
                bot.edit_message_text(
                    'This poll has been permanently deleted.',
                    chat_id=reference.admin_chat_id,
                    message_id=reference.admin_message_id,
                )

            # Edit message via inline_message_id
            else:
                # Create text and keyboard
                bot.edit_message_text(
                    'This poll has been permanently deleted.',
                    inline_message_id=reference.inline_message_id,
                )
        except BadRequest as e:
            if e.message.startswith('Message_id_invalid'):
                pass
            else:
                raise


def get_poll_text(session, poll):
    """Create the text of the poll."""
    lines = [f"{poll.name}"]
    lines.append(f'{poll.description}')

    total_user_count = session.query(User.id) \
        .join(Vote) \
        .join(PollOption) \
        .filter(PollOption.poll == poll) \
        .group_by(User.id) \
        .count()

    # Name and description
    lines = []
    lines.append(f'*{poll.name}*')
    lines.append(f'_{poll.description}_')

    options = get_sorted_options(poll, poll.options.copy(), total_user_count)

    # All options with their respective people percentage
    for option in options:
        lines.append('')
        if len(option.votes) > 0:
            lines.append(f'*{option.name}* ({len(option.votes)} votes)')
        else:
            lines.append(f'*{option.name}*')

        lines.append(get_percentage_line(option, total_user_count))

        # Add the names of the voters to the respective options
        if not poll.anonymous and len(option.votes) > 0:
            votes = get_sorted_votes(poll, option.votes)
            for index, vote in enumerate(votes):
                if index != len(poll.votes) - 1:
                    line = f'├ {vote.user.name}'
                else:
                    line = f'└ {vote.user.name}'

                lines.append(line)

    # Total user count information
    if total_user_count > 1:
        lines.append(f'\n*{total_user_count} users* voted so far')
    elif total_user_count == 1:
        lines.append('\n*One user* voted so far')

    # Notify users that poll is closed
    if poll.closed:
        lines.insert(0, '⚠️ *This poll is closed* ⚠️\n')
        lines.append('\n⚠️ *This poll is closed* ⚠️')

    return '\n'.join(lines)


def get_sorted_votes(poll, votes):
    """Sort the polls depending on the current settings."""
    def get_user_name(vote):
        """Get the name of user to sort votes."""
        return vote.user.name

    if poll.user_sorting == UserSorting.user_name.name:
        votes.sort(key=get_user_name)

    return votes


def get_sorted_options(poll, options, total_user_count):
    """Sort the polls depending on the current settings."""
    def get_option_name(option):
        """Get the name of the option."""
        return option.name

    def get_option_percentage(option):
        """Get the name of the option."""
        return calculate_percentage(option, total_user_count)

    if poll.option_sorting == OptionSorting.option_name.name:
        options.sort(key=get_option_name)

    elif poll.option_sorting == OptionSorting.option_percentage.name:
        options.sort(key=get_option_percentage, reverse=True)

    return options


def calculate_percentage(poll_option, total_user_count):
    """Calculate the percentage for this option."""
    if total_user_count == 0:
        percentage = 0
    else:
        percentage = round(len(poll_option.votes)/total_user_count * 100)

    return percentage


def get_percentage_line(poll_option, total_user_count):
    """Get the percentage line for each option."""
    percentage = calculate_percentage(poll_option, total_user_count)
    filled_slots = math.floor(percentage/10)

    line = '│ '
    line += filled_slots * '●'
    line += (10-filled_slots) * '○'
    line += f' ({percentage}%)'

    return ''.join(line)


def get_poll_management_text(session, poll):
    """Create the management interface for a poll."""
    poll_text = get_poll_text(session, poll)

    # Poll is closed, the options are not important any longer
    if poll.closed:
        return poll_text

    management_text = 'Manage your poll:\n\n'
    management_text += poll_text

    return management_text


def get_options_text(poll):
    """Compile the options text for this poll."""
    text = f"""*General settings:*
Vote type: {VoteTypeTranslation[poll.vote_type]}
Anonymity: {'Names are not visible' if poll.anonymous else 'Names are visible'}

*Sorting:*
"""

    # Sorting of user names
    if not poll.anonymous:
        text += f"User: {SortOptionTranslation[poll.user_sorting]}\n"

    text += f'Option: {SortOptionTranslation[poll.option_sorting]}'

    return text
