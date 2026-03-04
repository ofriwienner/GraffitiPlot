import numpy as np

# This empty dictionary will be automatically filled by the decorator
STANDARD_MODELS = {}

def register_fit(name, param_names, default_guesses, equation_string):
    """
    Decorator to automatically register a new mathematical model into the Fit UI.
    """
    def decorator(func):
        STANDARD_MODELS[name] = (func, param_names, default_guesses, equation_string)
        return func
    return decorator


# ---------------------------------------------------------
# PHYSICS & MATH LIBRARY
# ---------------------------------------------------------

@register_fit(
    name='Gaussian', 
    param_names=['a', 'mu', 'sigma'], 
    default_guesses=[1.0, 0.0, 1.0], 
    equation_string="a * np.exp(-(x - mu)**2 / (2 * sigma**2))"
)
def gaussian(x, a, mu, sigma):
    return a * np.exp(-(x - mu)**2 / (2 * sigma**2))


@register_fit(
    name='Lorentzian', 
    param_names=['a', 'x0', 'gamma'], 
    default_guesses=[1.0, 0.0, 1.0], 
    equation_string="a / (1 + ((x - x0) / gamma)**2)"
)
def lorentzian(x, a, x0, gamma):
    return a / (1 + ((x - x0) / gamma)**2)


@register_fit(
    name='Linear', 
    param_names=['m', 'b'], 
    default_guesses=[1.0, 0.0], 
    equation_string="m * x + b"
)
def linear(x, m, b):
    return m * x + b


@register_fit(
    name='Exponential', 
    param_names=['a', 'b', 'c'], 
    default_guesses=[1.0, 1.0, 0.0], 
    equation_string="a * np.exp(b * x) + c"
)
def exponential(x, a, b, c):
    return a * np.exp(b * x) + c


@register_fit(
    name='Sine', 
    param_names=['a', 'b', 'c', 'd'], 
    default_guesses=[1.0, 1.0, 0.0, 0.0], 
    equation_string="a * np.sin(b * x + c) + d"
)
def sine(x, a, b, c, d):
    return a * np.sin(b * x + c) + d


@register_fit(
    name='Polynomial (2nd)', 
    param_names=['a', 'b', 'c'], 
    default_guesses=[1.0, 1.0, 0.0], 
    equation_string="a * x**2 + b * x + c"
)
def polynomial_2(x, a, b, c):
    return a * x**2 + b * x + c
