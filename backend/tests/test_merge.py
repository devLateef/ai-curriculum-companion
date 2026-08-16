"""Merge and prefilter, on synthetic payloads. No model, no corpus, no network."""

from src.merge import Unit, build_units, merge_items, prefilter
from src.schema import Item

BODY_H = 10.0
HEAD_H = 18.0


def line(id_: str, text: str, y: float, x: float = 50.0, h: float = BODY_H) -> Item:
    return Item(id=id_, text=text, location=[x, y, 400.0, h])


def test_joins_lines_until_terminal_punctuation():
    items = [
        line("a", "La puberte est marquee par une", 100),
        line("b", "augmentation de la taille", 110),
        line("c", "pouvant atteindre dix centimetres.", 120),
    ]
    units = merge_items(items)
    assert len(units) == 1
    assert units[0].source_ids == ["a", "b", "c"]
    assert units[0].text.endswith("centimetres.")


def test_splits_on_font_size_change():
    """A heading must not be glued to the paragraph beneath it."""
    items = [
        line("h", "Le developpement de la musculature", 100, h=HEAD_H),
        line("a", "Au moment de la puberte les garcons voient leurs epaules s'elargir.", 130),
    ]
    units = merge_items(items)
    assert len(units) == 2
    assert units[0].source_ids == ["h"]


def test_splits_on_large_vertical_gap():
    items = [
        line("a", "Premier paragraphe sans ponctuation finale", 100),
        line("b", "Deuxieme bloc apres un grand espace vertical", 200),
    ]
    assert len(merge_items(items)) == 2


def test_splits_on_column_jump():
    """Joining across columns is the worst failure mode on a landscape page."""
    items = [
        line("a", "Fin de la colonne de gauche", 400, x=50.0),
        line("b", "Debut de la colonne de droite", 100, x=450.0),
    ]
    assert len(merge_items(items)) == 2


def test_merges_without_geometry():
    """Degrades to punctuation-only when the client sends no location."""
    items = [
        Item(id="a", text="Une phrase coupee en"),
        Item(id="b", text="deux morceaux."),
    ]
    units = merge_items(items)
    assert len(units) == 1
    assert units[0].source_ids == ["a", "b"]


def test_prefilter_drops_short_units():
    units = prefilter([Unit(text="Trop court.", source_ids=["a"])])
    assert units[0].dropped_reason == "too_short"


def test_prefilter_drops_apparatus_and_captions():
    cases = {
        "Chapitre 10 - La reproduction humaine chez les mammiferes": "apparatus",
        "Exercices - glossaire de fin de chapitre pour les eleves": "apparatus",
        "42": "apparatus",
        "Doc Wikimedia: photographie ancienne d'un preservatif en intestin": "apparatus",
        "Source: illustration tiree du manuel de sciences de la vie": "caption",
    }
    for text, expected in cases.items():
        unit = prefilter([Unit(text=text, source_ids=["a"])])[0]
        assert unit.dropped_reason == expected, f"{text!r} -> {unit.dropped_reason}"


def test_prefilter_drops_axis_labels():
    """Graph axis numbers extract into the body text flow on these documents."""
    unit = prefilter([Unit(text="30 24 18 12 6 0 1 5 9 13 16 20", source_ids=["a"])])[0]
    assert unit.dropped_reason == "non_prose"


def test_prefilter_keeps_a_real_claim():
    claim = (
        "Ce phenomene touche 70 % des garcons entre 13 et 16 ans et disparait "
        "en un ou deux ans."
    )
    unit = prefilter([Unit(text=claim, source_ids=["a"])])[0]
    assert unit.kept


def test_dropped_units_keep_their_ids():
    """Every original item must still receive a verdict."""
    units = build_units([line("a", "Trop court.", 100)])
    assert units[0].source_ids == ["a"]
    assert not units[0].kept


def test_every_item_id_survives_merge():
    items = [line(f"i{n}", f"Fragment numero {n} du texte", 100 + n * 10) for n in range(12)]
    units = build_units(items)
    seen = [i for u in units for i in u.source_ids]
    assert seen == [it.id for it in items]
