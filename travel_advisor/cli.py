"""Command-line interface for planning and re-planning trips.

    travel-advisor demo
        Fully offline showcase (built-in Kyoto data): plan a trip, then
        re-plan it after a rainy-day disruption.

    travel-advisor plan --destination "Kyoto, Japan" \\
        --start 2026-09-01 --end 2026-09-03 --interests history,food

        Plan a real trip using live open-data services (weather, places,
        routing). Requires outbound network access.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

from .engine import ItineraryScheduler, Rescheduler, TripPlanner
from .models import (
    Disruption,
    DisruptionType,
    Interest,
    Pace,
    TripRequest,
)
from .providers import HaversineRoutingProvider
from .render import render_itinerary
from .samples import KYOTO_BASE, KYOTO_POIS, sample_kyoto_request


def _parse_interests(raw: str | None) -> list[Interest]:
    if not raw:
        return []
    out: list[Interest] = []
    for token in raw.split(","):
        token = token.strip().lower()
        if not token:
            continue
        try:
            out.append(Interest(token))
        except ValueError:
            valid = ", ".join(i.value for i in Interest)
            raise SystemExit(f"Unknown interest '{token}'. Valid: {valid}")
    return out


def _cmd_demo(_args: argparse.Namespace) -> int:
    routing = HaversineRoutingProvider()
    request = sample_kyoto_request()

    scheduler = ItineraryScheduler(routing)
    itinerary = scheduler.build(request, KYOTO_POIS, anchor=KYOTO_BASE)

    print(render_itinerary(itinerary))
    print("\n" + "#" * 60)
    print("# Disruption: rain now forecast for day 2 — re-planning...")
    print("#" * 60 + "\n")

    used = itinerary.scheduled_poi_ids()
    spares = [p for p in KYOTO_POIS if p.id not in used]
    rescheduler = Rescheduler(routing)
    day_two = request.start_date + timedelta(days=1)
    result = rescheduler.reschedule(
        itinerary,
        Disruption(type=DisruptionType.WEATHER_RAIN, date=day_two),
        spare_pois=spares,
    )
    for change in result.changes:
        print(f"  • {change}")
    for issue in result.unresolved:
        print(f"  ! {issue}")
    print()
    print(render_itinerary(result.itinerary))
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    request = TripRequest(
        destination=args.destination,
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        party_size=args.party_size,
        interests=_parse_interests(args.interests),
        pace=Pace(args.pace),
    )
    planner = TripPlanner()
    try:
        planned = planner.plan(request)
    except Exception as exc:  # network / geocoding / API errors
        print(f"Could not plan trip: {exc}", file=sys.stderr)
        print(
            "Live planning needs outbound network access to open-data services.\n"
            "Try `travel-advisor demo` for a fully offline showcase.",
            file=sys.stderr,
        )
        return 1
    print(render_itinerary(planned.itinerary))
    if not planned.itinerary.scheduled_poi_ids():
        print(
            "\n(No places were scheduled — try widening interests or the date range.)",
            file=sys.stderr,
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="travel-advisor",
        description="Automated travel itinerary planner and re-planner.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Offline showcase using built-in data.").set_defaults(
        func=_cmd_demo
    )

    plan = sub.add_parser("plan", help="Plan a real trip using live open data.")
    plan.add_argument("--destination", required=True, help="City or place name.")
    plan.add_argument("--start", required=True, help="Start date (YYYY-MM-DD).")
    plan.add_argument("--end", required=True, help="End date (YYYY-MM-DD).")
    plan.add_argument("--party-size", type=int, default=1, help="Number of travellers.")
    plan.add_argument(
        "--interests",
        default="",
        help="Comma-separated: " + ", ".join(i.value for i in Interest),
    )
    plan.add_argument(
        "--pace",
        default=Pace.BALANCED.value,
        choices=[p.value for p in Pace],
        help="How densely to pack each day.",
    )
    plan.set_defaults(func=_cmd_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
