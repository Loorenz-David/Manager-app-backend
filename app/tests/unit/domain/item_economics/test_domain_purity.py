from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).parents[4] / "beyo_manager" / "domain" / "item_economics"
FINGERPRINT_TERMS = ("hashlib", "sha1", "sha256", "md5", "fingerprint", "digest")
SQL_IMPORT_TERMS = ("sqlalchemy", "models.tables")


def _domain_modules():
    modules = sorted(PACKAGE_ROOT.rglob("*.py"))
    assert modules
    return modules


def test_item_economics_domain_has_no_spec_identity_hashing():
    modules = _domain_modules()
    serializer = PACKAGE_ROOT / "serializers.py"
    serializer_text = serializer.read_text()
    assert serializer_text.count('"config_fingerprint": scenario["config_fingerprint"]') == 1

    for module in modules:
        source = module.read_text()
        if module == serializer:
            source = source.replace('"config_fingerprint": scenario["config_fingerprint"]', "", 1)
        assert not any(term in source for term in FINGERPRINT_TERMS), module


def test_item_economics_domain_walk_is_recursive(monkeypatch, tmp_path):
    monkeypatch.setitem(globals(), "PACKAGE_ROOT", tmp_path)
    nested = tmp_path / "nested" / "module.py"
    nested.parent.mkdir()
    nested.write_text("# controlled recursive-walk probe\n")
    modules = _domain_modules()
    assert modules
    assert nested in modules


def test_item_economics_domain_walk_requires_a_nonempty_package(monkeypatch, tmp_path):
    monkeypatch.setitem(globals(), "PACKAGE_ROOT", tmp_path / "missing")
    with pytest.raises(AssertionError):
        _domain_modules()


def test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports():
    for module in _domain_modules():
        source = module.read_text()
        assert not any(term in source for term in SQL_IMPORT_TERMS), module
