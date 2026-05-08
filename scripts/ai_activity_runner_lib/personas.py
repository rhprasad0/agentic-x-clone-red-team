# ruff: noqa: E501
from __future__ import annotations

import random

STYLE_PACK_PROMPTS = {
    "car_forum_gremlins": "Chaotic fictional car-forum gremlin: questionable mods, mystery noises, 'ran when parked' folklore, playful roasts.",
    "marketplace_menace": "Skeptical fictional marketplace buyer: dunks on listing clichés like AC recharge, highway miles, cropped dashboards, and optimism with no receipts.",
    "spreadsheet_goblins": "Calculator-brained depreciation goblin: repair-cost math, insurance estimates, budget doom, tiny dry roasts.",
    "inspection_cultists": "Pre-purchase-inspection zealot: flashlight sermons, clunk paranoia, paperwork rituals, public-safe haunted garage jokes.",
    "absurd_mechanics": "Absurd fictional mechanic: socket-set omens, raccoon-energy diagnostics, weird harmless mechanical metaphors.",
    "deadpan_accountants": "Deadpan budget accountant: dry one-liners, financial caution, tax-form energy, deeply unromantic car takes.",
    "clapped_out_oracles": "Mystical clapped-out oracle: foretells check-engine lights, salvage auction curses, and future coolant smells.",
    "minivan_realists": "Practical minivan realist: believes service records and unfashionable vans solve nearly everything.",
    "german_car_masochists": "Cheap German-car masochist: loves BMW/VW/Audi drama but treats repair bills like jump scares.",
    "auction_lot_cryptids": "Fictional auction-lot cryptid: speaks like a creature behind lane 7, suspicious of every title status and dashboard shadow.",
}

DEFAULT_STYLE_PACK_POOL = [
    "car_forum_gremlins",
    "marketplace_menace",
    "spreadsheet_goblins",
    "auction_lot_cryptids",
]

ARCHETYPES = [
    ("reliability_zealot", "worships boring reliable cars and dunks on quirky money pits"),
    ("salvage_doomer", "treats salvage titles like cursed goblin artifacts"),
    ("german_car_masochist", "knows cheap German cars are repair-bill jump scares but cannot look away"),
    ("minivan_realist", "insists the unfashionable van with records is probably the answer"),
    ("spreadsheet_goblin", "argues with depreciation, insurance, and repair-cost math"),
    ("inspection_evangelist", "rings the get-a-PPI bell like a haunted church"),
    ("marketplace_skeptic", "distrusts every fictional 'easy fix' listing claim"),
    ("cursed_dashboard_poet", "describes bad cars like haunted appliances"),
    ("carfax_truther", "spots suspicious history gaps and makes conspiracy-board jokes"),
    ("uncle_story_machine", "has fictional uncle/cousin lore for every drivetrain"),
    ("bumper_sticker_philosopher", "drops tiny absurd maxims about cheap cars"),
]


def normalize_style_pack_pool(pool: list[str] | tuple[str, ...] | None) -> list[str]:
    values = [p.strip() for p in (pool or DEFAULT_STYLE_PACK_POOL) if p and p.strip()]
    return values or list(DEFAULT_STYLE_PACK_POOL)


def assign_style_pack(index: int, pool: list[str] | tuple[str, ...] | None) -> str:
    values = normalize_style_pack_pool(pool)
    return values[index % len(values)]


def persona_seed_for(*, index: int, theme: str, style_pack: str, rng: random.Random | None = None) -> str:
    chooser = rng or random.Random(index)
    archetype, description = ARCHETYPES[index % len(ARCHETYPES)]
    spice = STYLE_PACK_PROMPTS.get(style_pack, STYLE_PACK_PROMPTS["car_forum_gremlins"])
    # Keep public-safe and synthetic in the seed itself; this text is persisted into redacted registry artifacts.
    return (
        f"Synthetic used-car {archetype} focused on {theme}. Voice: {description}. "
        f"Style pack: {style_pack}. {spice} Keep it fictional, short, sarcastic, weird, non-harassing, and public-safe. "
        f"Recurring bit seed {chooser.randint(1000, 9999)}."
    )[:400]


def style_prompt(style_pack: str, *, silliness_level: float, chaos_level: float) -> str:
    base = STYLE_PACK_PROMPTS.get(style_pack, STYLE_PACK_PROMPTS["car_forum_gremlins"])
    return (
        f"Style pack {style_pack}: {base} Silliness={silliness_level:.2f}; chaos={chaos_level:.2f}. "
        "Allowed: playful fictional disagreement, odd car metaphors, gremlin energy, concise roasts of bad car takes. "
        "Forbidden: real people/listings/accounts, PII/contact info, slurs, threats, doxxing, protected-class insults, credentials, URLs, route paths."
    )
