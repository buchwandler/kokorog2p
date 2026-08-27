from experiments.de_lexicon_compression.lexlab.composition import choose_segmentation


def test_ranking_prefers_fewer_then_longer_leftmost():
    atoms = {"A": ("a",), "AB": ("ab",), "B": ("b",), "BC": ("bc",), "C": ("c",)}
    assert choose_segmentation("ABC", atoms, mode="exact-multipart").components == (
        "AB",
        "C",
    )


def test_two_part_rejects_three_components():
    atoms = {"A": ("a",), "B": ("b",), "C": ("c",)}
    assert choose_segmentation("ABC", atoms, mode="exact-two-part") is None
