import unittest.mock
import pytest

import speechmatics.config


@unittest.mock.patch('builtins.open', side_effect=FileNotFoundError)
def test_load_config_with_no_argument_expect_not_fail(mock):
    # with pytest.raises(FileNotFoundError):
    speechmatics.config.load_config()


@unittest.mock.patch('builtins.open', side_effect=FileNotFoundError)
def test_load_config_with_explicit_default_argument_fails(mock):
    with pytest.raises(FileNotFoundError):
        speechmatics.config.load_config(speechmatics.config.DEFAULT_CONFIG_PATH)


@unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="")
def test_load_config_content_is_empty(mock):
    config = speechmatics.config.load_config("/random/non/existing/file")
    assert config == {}


@unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="url: ws://localhost:9000/v2")
def test_load_config_content_is_dict(mock):
    config = speechmatics.config.load_config("/random/non/existing/file")
    assert config == {"url": "ws://localhost:9000/v2"}


@unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="abc")
def test_load_config_content_is_invalid_yaml(mock):
    with pytest.raises(speechmatics.config.ConfigurationFormatError):
        speechmatics.config.load_config("/random/non/existing/file")


@unittest.mock.patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="- a")
def test_load_config_content_is_array(mock):
    with pytest.raises(speechmatics.config.ConfigurationFormatError):
        speechmatics.config.load_config("/random/non/existing/file")


def test_merge_update_with_empty_dict():
    result = speechmatics.config.merge_configs({"a": "b"}, {})
    assert result == {"a": "b"}


def test_merge_union():
    orig = {"a": "b"}
    result = speechmatics.config.merge_configs(orig, {"b": "c"})
    assert orig == {"a": "b"}
    assert result == {"a": "b", "b": "c"}


def test_merge_overlapping():
    orig = {"a": "b"}
    result = speechmatics.config.merge_configs(orig, {"a": "c"})
    assert orig == {"a": "b"}
    assert result == {"a": "c"}


def test_merge_overlapping_none_in_update():
    result = speechmatics.config.merge_configs({"a": "b"}, {"a": None})
    assert result == {"a": "b"}


def test_merge_overlapping_none_in_orig():
    result = speechmatics.config.merge_configs({"a": None}, {"a": "b"})
    assert result == {"a": "b"}
