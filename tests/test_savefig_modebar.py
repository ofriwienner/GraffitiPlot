import matplotlib

# Ensure headless rendering in CI.
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt


def test_savefig_hides_modebar_buttons(monkeypatch, tmp_path):
    import graffiti_plot
    from graffiti_plot import core

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])

    assert hasattr(fig, "_graffiti_buttons_refs")
    assert fig._graffiti_buttons_refs, "Expected modebar buttons to be installed"

    called = {"value": False}

    def stub_savefig(self, *args, **kwargs):
        called["value"] = True
        assert getattr(self, "_graffiti_modebar_hidden_for_save", False) is True
        for btn in self._graffiti_buttons_refs.values():
            assert btn.get_visible() is False
        # No-op: we only test the hide/restore behavior.
        return None

    # Patch the "original" savefig function that our wrapper calls into.
    monkeypatch.setattr(core, "_original_savefig", stub_savefig)

    out_file = tmp_path / "out.png"
    fig.savefig(out_file)

    assert called["value"] is True
    assert getattr(fig, "_graffiti_modebar_hidden_for_save", False) is False
    for btn in fig._graffiti_buttons_refs.values():
        assert btn.get_visible() is True

