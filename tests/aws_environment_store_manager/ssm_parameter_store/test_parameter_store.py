"""
Test suite for ParameterStore class.

This module demonstrates best practices for testing AWS wrapper classes using moto
to mock AWS Systems Manager Parameter Store operations.
"""

import pytest
from moto import mock_aws

from aws_environment_store_manager.ssm_parameter_store import ParameterStore
from aws_environment_store_manager.ssm_parameter_store.models import ParameterResponse


@pytest.fixture
def aws_credentials(monkeypatch):
    """
    Set up fake AWS credentials for moto.

    This fixture ensures that boto3 doesn't try to use real AWS credentials
    during testing. Moto will intercept AWS API calls regardless of credentials,
    but setting this prevents any accidental real AWS calls if moto fails.
    """
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def parameter_store(aws_credentials):
    """
    Create a ParameterStore instance with mocked AWS SSM service.

    This fixture uses moto's mock_aws decorator as a context manager to mock
    the AWS Systems Manager service. The mock is active for the duration of
    each test that uses this fixture.

    Returns:
        ParameterStore: A ParameterStore instance configured for testing
    """
    with mock_aws():
        store = ParameterStore(region="us-east-1", clean_string=True)
        yield store


class TestParameterStoreInitialization:
    """Test suite for ParameterStore initialization."""

    def test_initialization_with_valid_region(self, aws_credentials):
        """Test that ParameterStore initializes with a valid region."""
        with mock_aws():
            store = ParameterStore(region="us-east-1")
        assert store.client.meta.region_name == "us-east-1"

    def test_initialization_with_empty_region(self, aws_credentials):
        """Test that ParameterStore raises ValueError with an invalid region."""
        with pytest.raises(ValueError):
            with mock_aws():
                ParameterStore(region="")

    def test_initialization_with_invalid_region(self, aws_credentials):
        """Test that ParameterStore raises ValueError with an invalid region."""
        with pytest.raises(KeyError):
            with mock_aws():
                store = ParameterStore(region="invalid-region")
                store.client.describe_parameters()

    def test_initialization_with_clean_string_false(self, aws_credentials):
        """Test that ParameterStore initializes with clean_string=False."""
        with mock_aws():
            store = ParameterStore(region="us-east-1", clean_string=False)
        assert store.clean_string is False

    def test_initialization_with_clean_string_true(self, aws_credentials):
        """Test that ParameterStore initializes with clean_string=True."""
        with mock_aws():
            store = ParameterStore(region="us-east-1", clean_string=True)
        assert store.clean_string is True

    def test_initialization_with_clean_string_default(self, aws_credentials):
        """Test that ParameterStore initializes with clean_string=True as default."""
        with mock_aws():
            store = ParameterStore(region="us-east-1")
        assert store.clean_string is True


class TestParameterStoreReadOperations:
    """Test suite for ParameterStore read operations."""

    def test_get_parameter_returns_parameter_dict_when_parameter_exists(self, parameter_store):
        """
        Test that get_parameter returns the correct parameter dict when the parameter exists.

        This test demonstrates:
        - How to create a parameter in the mocked Parameter Store
        - How to retrieve and verify the parameter dict
        - Basic read operation testing pattern
        """
        # Arrange: Create a parameter in the mocked Parameter Store
        parameter_name = "/test/database/HOST"
        expected_value = "localhost"
        parameter_store.create_parameter(parameter=parameter_name, value=expected_value)

        # Act: Retrieve the parameter
        parameter_dict = parameter_store.get_parameter(parameter_name)

        # Assert: Verify the retrieved parameter matches what was stored
        assert parameter_dict is not None
        assert isinstance(parameter_dict, ParameterResponse)
        assert parameter_dict.Parameter.Value == expected_value
        assert parameter_dict.Parameter.Name == parameter_name
        assert parameter_dict.Parameter.Type == "String"
        assert parameter_dict.Parameter.Version == 1
        assert parameter_dict.Parameter.DataType == "text"

    def test_get_parameter_value_returns_value_when_parameter_exists(self, parameter_store):
        """
        Test that get_parameter_value returns the correct value for an existing parameter.

        This test demonstrates:
        - How to create a parameter in the mocked Parameter Store
        - How to retrieve and verify the parameter value
        - Basic read operation testing pattern
        """
        # Arrange: Create a parameter in the mocked Parameter Store
        parameter_name = "/test/database/host"
        expected_value = "localhost"
        parameter_store.create_parameter(parameter=parameter_name, value=expected_value)

        # Act: Retrieve the parameter value
        actual_value = parameter_store.get_parameter_value(parameter_name)

        # Assert: Verify the retrieved value matches what was stored
        assert actual_value == expected_value

    def test_get_parameter_returns_none_when_parameter_does_not_exist(self, parameter_store):
        """
        Test that get_parameter returns None for a non-existent parameter.

        This test demonstrates:
        - How the wrapper handles missing parameters gracefully
        - Testing error handling without raising exceptions
        """
        # Act: Try to retrieve a parameter that doesn't exist
        result = parameter_store.get_parameter("/nonexistent/parameter")

        # Assert: Verify that None is returned
        assert result is None


class TestParameterStoreWriteOperations:
    """Test suite for ParameterStore write operations."""

    def test_create_parameter_stores_value_successfully(self, parameter_store):
        """
        Test that create_parameter successfully stores a parameter.

        This test demonstrates:
        - How to test write operations
        - How to verify the operation by reading back the value
        - Testing the complete write-read cycle
        """
        # Arrange: Define parameter details
        parameter_name = "/test/api/key"
        parameter_value = "secret-api-key-12345"

        # Act: Create the parameter
        result = parameter_store.create_parameter(
            parameter=parameter_name, value=parameter_value
        )

        # Assert: Verify the return value
        assert result == {parameter_name: parameter_value}

        # Assert: Verify the parameter was actually stored by reading it back
        stored_value = parameter_store.get_parameter_value(parameter_name)
        assert stored_value == parameter_value

    def test_update_or_create_parameter_creates_new_parameter(self, parameter_store):
        """
        Test that update_or_create_parameter creates a parameter when it doesn't exist.

        This test demonstrates:
        - Testing upsert operations (create path)
        - Verifying parameter creation through read-back
        """
        # Arrange: Define parameter details for a new parameter
        parameter_name = "/test/config/timeout"
        parameter_value = "30"

        # Act: Call update_or_create on a non-existent parameter
        result = parameter_store.update_or_create_parameter(
            parameter=parameter_name, value=parameter_value
        )

        # Assert: Verify the return value
        assert result == {parameter_name: parameter_value}

        # Assert: Verify the parameter was created
        stored_value = parameter_store.get_parameter_value(parameter_name)
        assert stored_value == parameter_value

    def test_update_or_create_parameter_updates_existing_parameter(self, parameter_store):
        """
        Test that update_or_create_parameter updates an existing parameter.

        This test demonstrates:
        - Testing upsert operations (update path)
        - Verifying parameter updates by comparing old and new values
        - Testing state changes in the mocked service
        """
        # Arrange: Create an initial parameter
        parameter_name = "/test/config/max_retries"
        initial_value = "3"
        updated_value = "5"

        parameter_store.create_parameter(parameter=parameter_name, value=initial_value)

        # Act: Update the parameter using update_or_create
        result = parameter_store.update_or_create_parameter(
            parameter=parameter_name, value=updated_value
        )

        # Assert: Verify the return value
        assert result == {parameter_name: updated_value}

        # Assert: Verify the parameter was updated
        stored_value = parameter_store.get_parameter_value(parameter_name)
        assert stored_value == updated_value
        assert stored_value != initial_value
