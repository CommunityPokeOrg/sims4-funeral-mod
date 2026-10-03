# Copyright (c) CommunityPoke contributors.
"""Pure-Python helpers for the debugging/devtool commands.

Nothing in this module imports game modules, so the unit tests can exercise
every line the cheat-console commands print.
"""


def format_money(amount):
    """'§764', or '§?' when the balance could not be read."""
    if amount is None:
        return '§?'
    try:
        return '§{}'.format(int(amount))
    except (TypeError, ValueError):
        return '§?'


class DebitRecord:
    """One attempted household debit with observed funds before/after.

    ``money_before``/``money_after`` are None when the game would not let us
    read the balance — in that case the debit is only as trustworthy as the
    ``success`` flag returned by ``FamilyFunds.try_remove``.
    """

    __slots__ = ('sim_id', 'zone_id', 'role', 'amount', 'money_before',
                 'money_after', 'success', 'note')

    def __init__(self, sim_id, role, amount, money_before, money_after,
                 success, note='', zone_id=None):
        self.sim_id = sim_id
        self.zone_id = zone_id
        self.role = role
        self.amount = amount
        self.money_before = money_before
        self.money_after = money_after
        self.success = bool(success)
        self.note = note

    @property
    def observed_delta(self):
        """Simoleons the household actually lost, or None if unobservable."""
        if self.money_before is None or self.money_after is None:
            return None
        try:
            return int(self.money_before) - int(self.money_after)
        except (TypeError, ValueError):
            return None

    @property
    def verified(self):
        """True when the observed balance dropped by exactly ``amount``."""
        return self.observed_delta == self.amount

    def line(self):
        status = 'ok' if self.success else 'FAILED'
        delta = self.observed_delta
        if delta is not None:
            status += ' verified' if self.verified else ' delta=-§{}'.format(delta)
        parts = [
            'sim={}'.format(self.sim_id),
            'role={}'.format(self.role),
            'want={}'.format(format_money(self.amount)),
            'funds={}->{}'.format(format_money(self.money_before),
                                  format_money(self.money_after)),
            status,
        ]
        if self.note:
            parts.append(self.note)
        return 'debit ' + ' '.join(parts)


def summarize_debits(records):
    """Roll a list of DebitRecords up into a one-line summary."""
    records = list(records)
    observed = [r.observed_delta for r in records if r.observed_delta is not None]
    return {
        'attempted': len(records),
        'succeeded': sum(1 for r in records if r.success),
        'verified': sum(1 for r in records if r.verified),
        'observed_total': sum(observed),
        'expected_total': sum(r.amount for r in records if r.success),
    }


def format_debit_summary(records):
    s = summarize_debits(records)
    if s['attempted'] == 0:
        return 'debits: none recorded yet'
    return (
        'debits: {attempted} attempted, {succeeded} ok, {verified} verified by '
        'balance, observed -{observed} (expected -{expected})'.format(
            attempted=s['attempted'],
            succeeded=s['succeeded'],
            verified=s['verified'],
            observed=format_money(s['observed_total']),
            expected=format_money(s['expected_total']),
        )
    )


def describe_event(ev):
    """Multi-line dump of an active FuneralEvent (or a stand-in object)."""
    if ev is None:
        return ['funeral: none active']
    lines = [
        'funeral: zone={} host={} deceased={} urnstone={}'.format(
            getattr(ev, 'zone_id', None),
            getattr(ev, 'host_sim_id', None),
            getattr(ev, 'deceased_sim_id', None),
            getattr(ev, 'urnstone_id', None),
        ),
        '  attendees={} paid={} eulogies={} host_fee={} attendee_fee={}'.format(
            len(getattr(ev, 'attendee_ids', ()) or ()),
            len(getattr(ev, 'paid_attendee_ids', ()) or ()),
            getattr(ev, 'eulogies', 0),
            format_money(getattr(ev, 'host_fee', None)),
            format_money(getattr(ev, 'attendee_fee', None)),
        ),
        '  attendee_ids={} paid_ids={}'.format(
            list(getattr(ev, 'attendee_ids', ()) or ()),
            sorted(getattr(ev, 'paid_attendee_ids', ()) or ()),
        ),
    ]
    return lines


def format_object_check(name, affordance_report):
    """One line per injected tuned object, e.g.
    ``urnstone_ground: PlanFuneralInteraction=OK GiveEulogyInteraction=MISSING``."""
    if not affordance_report:
        return '{}: no affordances recorded'.format(name)
    parts = ['{}={}'.format(aff, 'OK' if present else 'MISSING')
             for aff, present in sorted(affordance_report.items())]
    return '{}: {}'.format(name, ' '.join(parts))


def format_funds_row(label, sim_id, money, affordable=None):
    """``attendee Jane Doe (42): §1000 affordable`` (+`` TOO EXPENSIVE``)."""
    row = '{} ({}): {}'.format(label, sim_id, format_money(money))
    if affordable is not None:
        row += ' {}'.format('affordable' if affordable else 'TOO EXPENSIVE')
    return row
