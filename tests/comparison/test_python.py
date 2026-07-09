#!/usr/bin/env python3
"""Test hysplit package imports and basic functionality."""

import pytest

from hysplit import (
    hysplit_trajectory,
    create_trajectory_model,
    set_config,
    set_ascdata,
)


def test_package_imports():
    """Test that main package exports are importable."""
    import hysplit

    assert hasattr(hysplit, "__version__")
    assert hasattr(hysplit, "hysplit_trajectory")
    assert hasattr(hysplit, "create_trajectory_model")
    assert hasattr(hysplit, "set_config")
    assert hasattr(hysplit, "set_ascdata")


def test_version_string():
    """Test that version string is properly formatted."""
    import hysplit

    version = hysplit.__version__
    assert isinstance(version, str)
    assert len(version.split(".")) >= 2  # At least major.minor


def test_create_trajectory_model():
    """Test that trajectory model can be created."""
    model = create_trajectory_model()

    assert model is not None
    assert hasattr(model, "add_trajectory_params")
    assert hasattr(model, "run")


def test_set_config_defaults():
    """Test that set_config returns valid defaults."""
    config = set_config()

    assert config.tratio == 0.75
    assert config.numpar == 2500
    assert config.maxpar == 10000


def test_set_config_custom_values():
    """Test that set_config accepts custom values."""
    config = set_config(numpar=5000, maxpar=20000)

    assert config.numpar == 5000
    assert config.maxpar == 20000


def test_set_ascdata():
    """Test that set_ascdata returns valid configuration."""
    ascdata = set_ascdata()

    assert ascdata is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
