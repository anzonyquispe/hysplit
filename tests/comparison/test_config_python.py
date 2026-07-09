#!/usr/bin/env python3
"""Test configuration file generation in Python."""

import tempfile
from pathlib import Path

import pytest

from hysplit.core.config import set_config, set_ascdata


def test_set_config_creates_valid_config():
    """Test that set_config creates a valid configuration object."""
    config = set_config(numpar=2500, maxpar=10000)

    assert config.numpar == 2500
    assert config.maxpar == 10000
    assert config.tratio == 0.75  # default value


def test_set_config_writes_setup_cfg():
    """Test that config.to_file writes a valid SETUP.CFG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        config = set_config(numpar=2500, maxpar=10000, tm_pres=1, tm_tamb=1)
        config.to_file(test_dir)

        setup_cfg = test_dir / "SETUP.CFG"
        assert setup_cfg.exists()

        content = setup_cfg.read_text()
        assert "&SETUP" in content
        assert "numpar = 2500" in content
        assert "maxpar = 10000" in content


def test_set_ascdata_creates_valid_config():
    """Test that set_ascdata creates a valid configuration object."""
    ascdata = set_ascdata()

    assert ascdata is not None


def test_set_ascdata_writes_ascdata_cfg():
    """Test that ascdata.to_file writes a valid ASCDATA.CFG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        ascdata = set_ascdata()
        ascdata.to_file(test_dir)

        ascdata_cfg = test_dir / "ASCDATA.CFG"
        assert ascdata_cfg.exists()

        content = ascdata_cfg.read_text()
        assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
