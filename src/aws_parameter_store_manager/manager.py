from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal

import boto3

from aws_parameter_store_manager.exceptions import ParameterAlreadyExists
from aws_parameter_store_manager.validation import AWSTag


class ParameterStoreManager:
    def __init__(self, region: str, group: Optional[str] = None):
        """
        Initialize the ParameterStoreManager. You can set a group that will be used as parameter prefix.
        This is useful for separating Environment Variables into groups like different environments
        (e.g. development|staging|production). The AWS Parameter Store uses hierarchical pathlike naming
        conventions, so you can use pathlike strings to group environment variables in such a structure.
        If doing so, you can group many environment variables into one group.

        project_name
        |_PROJECT_VAR_1
        |_customer_a
        | |_ENV_VAR_1 = "This is an env var for customer_a"
        | |_staging
        | | |_STG_VAR_1 = "This is an env var for customer_a's staging environment"
        | |_production
        |   |_PROD_VAR_1 = "This is an env var for customer_a's production environment"
        |_customer_b
          |_staging
          | |_STG_VAR_1 = "This is an env var for customer_b's staging environment"
          |_production
            |_PROD_VAR_1 = "This is an env var for customer_b's production environment"

        This hierarchy translates into the following group paths:

        project_name
        - PROJECT_VAR_1
        project_name/customer_a
        - ENV_VAR_1
        project_name/customer_a/staging
        - STG_VAR_1
        project_name/customer_a/production
        - PROD_VAR_1
        project_name/customer_b/staging
        - STG_VAR_1
        project_name/customer_b/production
        - PROD_VAR_1

        :param region: AWS region where to store or fetch the parameters
        :param group: (optional) Pathlike string to store or get the parameters from
        """
        self.group = ""
        group = group if group is not None else ""
        self.set_group(group)
        self.client = boto3.client("ssm", region_name=region)

    def set_group(self, group: str) -> str:
        """
        Switch to a different group

        :param group: Pathlike string
        :return: The valid group name
        """
        if group is None:
            raise ValueError("group cannot be None")

        if group == "":
            self.group = group
            return self.group

        group = self._format_group(group)

        self.group = group

        return self.group

    def get_parameter(self, parameter: str) -> str | None:
        """
        Get a parameter from the set group.

        AWS Docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm/client/get_parameter.html

        :param parameter: Parameter Name
        :return: The Value of the parameter of set group if exists, else None
        """
        self._validate_string(parameter)
        try:
            response = self.client.get_parameter(
                Name=self._build_path(parameter), WithDecryption=True
            )
        except self.client.exceptions.ParameterNotFound:
            return None

        return response["Parameter"]["Value"]

    def create_parameter(
        self,
        parameter: str,
        value: str,
        parameter_type: Literal["String", "StringList", "SecureString"] = "String",
        tier: Literal["Standard", "Advanced"] = "Standard",
        description: Optional[str] = None,
        encryption_key_id: Optional[str] = None,
        tags: Optional[list[AWSTag]] = None,
    ) -> dict[str, str]:
        """
        Create a parameter in AWS in the set group.

        AWS Docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm/client/put_parameter.html

        :param parameter: The Manager will store the value under the set group and parameter, if a group is set upon initialization. Allowed characters: a-zA-Z0-9_.-
        :param value: The value that should be stored. Standard parameters have a value limit of 4 KB. Advanced parameters have a value limit of 8 KB.
        :param parameter_type: Set the parameter type. Options: "String" | "StringList" | "SecureString", default = "String"
        :param tier: Set the tier option for the parameter. Options: "Standard" | "Advanced", default = "Standard"
        :param description: (optional)
        :param encryption_key_id: (optional) Set the KMS id if using parameter_type "SecureString". If not set, the default key is used.
        :param tags: (optional) Set optional AWS tags. Use a list with dicts in the format of AWSTag {"Key": ..., "Value": ...}.
        :return:
        """
        self._validate_string(parameter)
        request_params: dict[str, bool | str | list[AWSTag]] = {
            "Overwrite": False,
            "Name": self._build_path(parameter),
            "Value": value,
            "Type": parameter_type,
            "Tier": tier,
        }
        if description:
            request_params["Description"] = description
        if tags:
            request_params["Tags"] = tags
        if encryption_key_id:
            request_params["KeyId"] = encryption_key_id

        try:
            self.client.put_parameter(**request_params)
        except self.client.exceptions.ParameterAlreadyExists:
            raise ParameterAlreadyExists(parameter, self.group)

        return {parameter: value}

    def get_group_parameters(self) -> dict:
        """
        Get all parameters of the specific group.

        :return: A dict with the parameter names as key and the values as value.
        """
        response = self.client.get_parameters_by_path(
            Path=self.group, Recursive=False, WithDecryption=True
        )
        results = []

        for param in response["Parameters"]:
            results.append({"key": param["Name"], "value": param["Value"]})

        return self._parse_group_parameters(results)

    def _build_path(self, parameter) -> str:
        """Build a valid pathlike string compatible with AWS parameter storage"""
        base = Path(self.group)
        combined_path = base / parameter
        return str(combined_path)

    def _parse_group_parameters(self, ssm_response: list[dict[str, str]]) -> dict:
        """
        Parse the ssm client response of get_parameters_by_path into a dict with the parameter names as key and the values as value.

        :param ssm_response: The response of the get_parameters_by_path
        :return: A dict with the parameter names as key and the values as value.
        """
        parameter_dict = {}

        for param in ssm_response:
            key = param["key"].replace(self.group, "")
            if key.startswith("/"):
                key = key[1:]
            parameter_dict[key] = param["value"]

        return parameter_dict

    def _format_group(self, group: str) -> str:
        """
        Format and validate the group string into a pathlike string compatible with AWS parameter storage.

        :param group: The pathlike string of the group
        :return: A valid group string
        """
        p = Path(group)
        if not p.is_absolute():
            p = Path(f"/{group}")
        for part in p.parts:
            if part == "/":
                continue
            self._validate_string(part)
        return str(p)

    @staticmethod
    def _validate_string(string: str, raises: bool = True) -> bool:
        """
        Validate a string to check, if it can be stored as a parameter key in AWS. Allowed characters are a-zA-Z0-9_.-

        :param string: The string to validate
        :param raises: If set to True, the method will raise a ValueError with the invalid characters marked in the error message.
        :return: True if valid, False if invalid and raises is False
        """
        allowed_group_symbols = ["-", "_", "."]
        error_str = ""

        for char in string:
            if char.isalnum() or char in allowed_group_symbols:
                error_str += " "
            else:
                error_str += "^"

        if "^" in error_str and raises:
            raise ValueError(
                f"Illegal characters:\n"
                f"{string}\n"
                f"{error_str}\n"
                f"Allowed characters: {' '.join(allowed_group_symbols)}"
            )

        return "^" not in error_str
