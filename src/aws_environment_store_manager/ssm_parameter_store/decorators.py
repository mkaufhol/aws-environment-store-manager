import inspect
from functools import wraps

from .validation import make_string_parameter_store_compatible, validate_string


def clean_and_validate_string(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        should_clean = False

        if "self" in bound_args.arguments:
            class_instance = bound_args.arguments["self"]
            should_clean = getattr(class_instance, "clean_string", False)

        params_to_clean = [
            "parameter",
            "path",
        ]

        for func_param in params_to_clean:
            if func_param in bound_args.arguments:
                param_value = bound_args.arguments[func_param]
                if isinstance(param_value, str) and should_clean:
                    bound_args.arguments[func_param] = make_string_parameter_store_compatible(
                        param_value
                    )

                validate_string(bound_args.arguments[func_param])

        return func(*bound_args.args, **bound_args.kwargs)

    return wrapper
