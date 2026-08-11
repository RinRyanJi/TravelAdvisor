"""Human-readable rendering of itineraries for the CLI and logs."""

from __future__ import annotations

from .models import Itinerary, ItemType

_ICON = {
    ItemType.ACTIVITY: "◉",  # ◉
    ItemType.MEAL: "\U0001f374",  # 🍴
    ItemType.TRANSFER: "✈",  # ✈
    ItemType.FREE: "•",  # •
}


def render_itinerary(itinerary: Itinerary) -> str:
    """Return a multi-line, terminal-friendly view of a plan."""
    req = itinerary.request
    lines: list[str] = []
    header = f"Trip to {req.destination} — {req.num_days} day(s), {req.pace.value} pace"
    lines.append(header)
    lines.append("=" * len(header))
    if itinerary.revision:
        lines.append(f"(revision {itinerary.revision})")

    for day in itinerary.days:
        lines.append("")
        weather = ""
        if day.weather is not None and day.weather.condition.value != "unknown":
            w = day.weather
            temp = f", {w.temp_min_c:.0f}–{w.temp_max_c:.0f}°C" if w.temp_max_c is not None else ""
            weather = f"  [{w.condition.value}{temp}]"
        lines.append(f"{day.date.strftime('%a %Y-%m-%d')}{weather}")
        lines.append("-" * 32)
        if not day.items:
            note = f"  (no activities{' — ' + day.notes if day.notes else ''})"
            lines.append(note)
            continue
        for item in day.items:
            icon = _ICON.get(item.type, "•")
            when = f"{item.start.strftime('%H:%M')}–{item.end.strftime('%H:%M')}"
            travel = f"  (→ {item.travel_from_prev_minutes} min)" if item.travel_from_prev_minutes else ""
            cost = f"  ${item.cost:.0f}" if item.cost else ""
            lines.append(f"  {when} {icon} {item.title}{travel}{cost}")
        lines.append(f"  Day cost: ${day.total_cost:.0f}")

    lines.append("")
    lines.append(f"Estimated total: ${itinerary.total_cost:.0f} for {req.party_size} traveller(s)")
    return "\n".join(lines)
