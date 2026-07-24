# MTGO automation — reconnaissance scripts

Windows-only. Requires `pywinauto` (in `agent/requirements.txt`) and the
real MTGO client running and logged in on this machine.

These are **exploration scripts**, not a finished automation module —
each one was written to answer one question about how the MTGO client's
UI Automation tree behaves (does UI Automation work at all? how do you
open a trade? how do binders work?). They're kept because the exact
`automation_id`s and click sequences they encode are expensive to
re-derive.

- `inspect_windows.py` — list top-level windows, dump the MTGO window's
  full descendant tree if found. Starting point for any new
  reconnaissance.
- `click_and_inspect.py` / `double_click_and_inspect.py` /
  `right_click_and_inspect.py` — find an element by `automation_id` (or
  exact `window_text()`), click/double-click/right-click it, dump the
  resulting tree. Generic tools for iterative exploration.
- `open_trade_with_buddy.py` — right-click a buddy, select "Trade" from
  the context menu, dump the result. The context menu is transient so
  this has to happen in one process run.
- `trade_add_card.py` — search for a card by name in a trade window and
  double-click it to add it. Only works for the *counterparty's*
  binder (see below) — you cannot add your own cards to a trade this
  way. Targets the `<card>_<numericId>_CardQuantityControl` element
  rather than the `Collection-CardStack-<card>` image, since the
  latter can carry a stale "ghost" automation peer for a previously
  searched card (see memory for details).
- `import_binder.py` — **the real way to populate a binder.** Writes a
  `.dek` XML file (card names only, `CatID="0"` is fine — MTGO resolves
  by name) to a local `lists/` folder (gitignored) and drives the
  binder-creation dialog's "Import" flow to load it in one shot. Use
  this instead of hand-filling a binder by search+click — see below.
- `stress_fill_binder.py` — **kept only as a cautionary reference.**
  Fills a binder by searching + double-clicking each card one at a
  time, with retry/verification against the binder's live card count.
  Measured at ~11s/card and only ~88% success even with active polling
  (MTGO's own search rendering is slow and variable, not a bug in this
  script). Do not use this for real sessions — see `import_binder.py`.

## The mechanic these scripts proved out

Full write-up in memory (`mtgo_automation_mechanics` — durable,
cross-session knowledge, not duplicated here). Short version: neither
side can push their own cards into a trade. The **receiver** always
selects what they get from the **giver's exposed Trade Binder**. So
distributing loan cards means: create one MTGO binder per
(session, player), populate it with that player's assigned cards, open
a trade with them, and pick that specific binder in the trade request's
binder selector — the player then picks their cards from it and
submits, and the owner submits + confirms to close the loop. Verified
end to end against two real MTGO accounts on 2026-07-24.

Retrieving cards (the return leg) is the mirror of this, with one
inversion: since the bot is the one browsing the player's binder and
adding cards, the **bot** must click Submit (not the player). Validated
end to end on 2026-07-24.

**Populate binders via import, not search+click.** MTGO can import a
binder from a `.dek` file (a trivial XML format — card `Name` alone is
enough, no card-ID lookup needed) in a few seconds regardless of card
count, with 100% reliability. Searching and double-clicking each card
individually is 10x+ slower and meaningfully unreliable at MTGO's own
search-rendering speed. See `import_binder.py` and the memory write-up
for the full dialog-automation details.

## Not yet built
A real `agent/mtgo/client.py`-style module wrapping this into reusable,
tested functions (create_or_get_binder, add_card_to_binder,
request_trade_with_binder, wait_for_trade_window,
confirm_and_submit, ...) driven by the loan session state machine. The
scripts here are the reconnaissance that module will be built from.
