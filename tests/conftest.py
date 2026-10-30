"""Let pytest-homeassistant-custom-component load custom_components/."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in every test."""
    return
