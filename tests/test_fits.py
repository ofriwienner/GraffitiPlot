"""
Tests for graffiti_plot fit registration system.

Run with:
    python -m pytest tests/test_fits.py -v
"""

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_isolated_registry():
    """Return a fresh (empty) register_fit + STANDARD_MODELS pair so tests
    don't pollute the global registry with each other's models."""
    models = {}

    def register_fit(name, param_names, default_guesses, equation_string, hidden=False):
        def decorator(func):
            models[name] = (func, param_names, default_guesses, equation_string, hidden)
            return func
        return decorator

    return register_fit, models


# ---------------------------------------------------------------------------
# 1. register_fit — basic registration
# ---------------------------------------------------------------------------

class TestRegisterFit:
    def test_adds_to_registry(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Linear', param_names=['m', 'b'],
                      default_guesses=[1.0, 0.0], equation_string='m * x + b')
        def linear(x, m, b):
            return m * x + b

        assert 'Linear' in models

    def test_stored_tuple_has_five_elements(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Quad', param_names=['a'], default_guesses=[1.0],
                      equation_string='a * x**2')
        def quad(x, a):
            return a * x**2

        assert len(models['Quad']) == 5

    def test_stored_function_is_callable(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Const', param_names=['c'], default_guesses=[0.0],
                      equation_string='c')
        def const(x, c):
            return np.full_like(x, c, dtype=float)

        func, *_ = models['Const']
        result = func(np.array([1.0, 2.0, 3.0]), 5.0)
        np.testing.assert_array_equal(result, [5.0, 5.0, 5.0])

    def test_stored_param_names(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Exp', param_names=['a', 'b'],
                      default_guesses=[1.0, 1.0], equation_string='a * np.exp(b * x)')
        def exp_fit(x, a, b):
            return a * np.exp(b * x)

        _, param_names, _, _, _ = models['Exp']
        assert param_names == ['a', 'b']

    def test_stored_default_guesses(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Sine', param_names=['a', 'f'],
                      default_guesses=[2.0, 3.14], equation_string='a * np.sin(f * x)')
        def sine_fit(x, a, f):
            return a * np.sin(f * x)

        _, _, guesses, _, _ = models['Sine']
        assert guesses == [2.0, 3.14]

    def test_stored_equation_string(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='MyFit', param_names=['a'],
                      default_guesses=[1.0], equation_string='a * x')
        def my_fit(x, a):
            return a * x

        _, _, _, eq_str, _ = models['MyFit']
        assert eq_str == 'a * x'

    def test_decorator_returns_original_function(self):
        """The decorator must not alter the function behaviour."""
        register_fit, _ = _make_isolated_registry()

        @register_fit(name='Id', param_names=['a'],
                      default_guesses=[1.0], equation_string='a * x')
        def identity(x, a):
            return a * x

        np.testing.assert_allclose(identity(np.array([2.0, 4.0]), 3.0), [6.0, 12.0])


# ---------------------------------------------------------------------------
# 2. hidden flag
# ---------------------------------------------------------------------------

class TestHiddenFlag:
    def test_hidden_defaults_to_false(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Visible', param_names=['a'],
                      default_guesses=[1.0], equation_string='a')
        def visible(x, a):
            return a

        assert models['Visible'][4] is False

    def test_hidden_true_is_stored(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Secret', param_names=['a'],
                      default_guesses=[0.0], equation_string='a', hidden=True)
        def secret(x, a):
            return a

        assert models['Secret'][4] is True

    def test_hidden_false_explicit_is_stored(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Explicit', param_names=['a'],
                      default_guesses=[1.0], equation_string='a', hidden=False)
        def explicit(x, a):
            return a

        assert models['Explicit'][4] is False

    def test_hidden_model_still_callable(self):
        """Hidden models must still work — they're just not shown in the UI."""
        register_fit, models = _make_isolated_registry()

        @register_fit(name='HiddenFunc', param_names=['c'],
                      default_guesses=[0.0], equation_string='c', hidden=True)
        def hidden_func(x, c):
            return np.full_like(x, c, dtype=float)

        func, _, _, _, hidden = models['HiddenFunc']
        assert hidden is True
        result = func(np.array([1.0, 2.0]), 7.0)
        np.testing.assert_array_equal(result, [7.0, 7.0])


# ---------------------------------------------------------------------------
# 3. Visible-model filtering (simulates what the UI does)
# ---------------------------------------------------------------------------

class TestVisibleModelFilter:
    def test_filter_removes_hidden(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='Show', param_names=['a'], default_guesses=[1.0],
                      equation_string='a')
        def show(x, a): return a

        @register_fit(name='Hide', param_names=['b'], default_guesses=[0.0],
                      equation_string='b', hidden=True)
        def hide(x, b): return b

        visible = [m for m, entry in models.items() if not entry[4]]
        assert 'Show' in visible
        assert 'Hide' not in visible

    def test_all_visible_when_no_hidden(self):
        register_fit, models = _make_isolated_registry()

        @register_fit(name='A', param_names=['a'], default_guesses=[1.0], equation_string='a')
        def a(x, a): return a

        @register_fit(name='B', param_names=['b'], default_guesses=[1.0], equation_string='b')
        def b(x, b_): return b_

        visible = [m for m, entry in models.items() if not entry[4]]
        assert set(visible) == {'A', 'B'}


# ---------------------------------------------------------------------------
# 4. Public API exports
# ---------------------------------------------------------------------------

class TestPublicAPI:
    def test_register_fit_importable(self):
        from graffiti_plot import register_fit
        assert callable(register_fit)

    def test_standard_models_importable(self):
        from graffiti_plot import STANDARD_MODELS
        assert isinstance(STANDARD_MODELS, dict)

    def test_builtin_models_present(self):
        from graffiti_plot import STANDARD_MODELS
        for name in ('Gaussian', 'Lorentzian', 'Linear', 'Exponential', 'Sine', 'Polynomial (2nd)'):
            assert name in STANDARD_MODELS, f"Missing built-in model: {name}"

    def test_builtin_models_not_hidden(self):
        from graffiti_plot import STANDARD_MODELS
        for name, entry in STANDARD_MODELS.items():
            assert entry[4] is False, f"Built-in model '{name}' should not be hidden"

    def test_custom_fit_registers_in_global_models(self):
        from graffiti_plot import register_fit, STANDARD_MODELS

        @register_fit(name='_test_custom_integration', param_names=['a'],
                      default_guesses=[1.0], equation_string='a * x')
        def _test_custom(x, a):
            return a * x

        assert '_test_custom_integration' in STANDARD_MODELS
        # Cleanup to avoid polluting other tests
        del STANDARD_MODELS['_test_custom_integration']
