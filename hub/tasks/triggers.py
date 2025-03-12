from typing import List

from hub.api.v1.registry import EntryInformation, list_entries_inner


def _query_agent_triggers(trigger_clause) -> List[EntryInformation]:
    res = list_entries_inner(
        category="agent",
        custom_where=trigger_clause,
        show_hidden=False,
        show_latest_version=True,
    )
    return res


def agents_with_event_triggers() -> List[EntryInformation]:
    """Returns latest version of agents that track events."""
    trigger_clause = "details::triggers::events IS NOT NULL"
    return _query_agent_triggers(trigger_clause)


def agents_with_webhook_triggers() -> List[EntryInformation]:
    """Returns latest version of agents that are triggered by webhooks."""
    trigger_clause = "details::triggers::webhook IS NOT NULL"
    return _query_agent_triggers(trigger_clause)


def agents_with_x_accounts_to_track() -> List[EntryInformation]:
    """Returns latest version of agents that track x_accounts."""
    res = list_entries_inner(
        category="agent",
        custom_where="details::triggers::events::x_mentions IS NOT NULL",
        show_hidden=False,
        show_latest_version=True,
    )
    return res
