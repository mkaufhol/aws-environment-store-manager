class ParameterAlreadyExists(Exception):
    """Raised when a parameter already exists in the AWS Parameter Store for that group."""

    def __init__(self, parameter_name, group=None):
        self.parameter_name = parameter_name
        self.group = group

        if group:
            message = f"Parameter '{parameter_name}' already exists in group '{group}'."
        else:
            message = f"Parameter '{parameter_name}' already exists."
        message += " Use update_parameter to update or delete_parameter to delete."

        super().__init__(message)


class ParameterNotFoundError(Exception):
    """Raised when a parameter is not found in AWS Parameter Store."""

    def __init__(self, parameter_name, group=None):
        self.parameter_name = parameter_name
        self.group = group

        if group:
            message = f"Parameter '{parameter_name}' not found in group '{group}'."
        else:
            message = f"Parameter '{parameter_name}' not found."

        super().__init__(message)
