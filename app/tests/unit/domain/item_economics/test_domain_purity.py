from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[4] / "beyo_manager" / "domain" / "item_economics"
FINGERPRINT_TERMS = ("hashlib", "sha1", "sha256", "md5", "fingerprint", "digest")
SQL_IMPORT_TERMS = ("sqlalchemy", "models.tables")


def _domain_modules():
    return sorted(PACKAGE_ROOT.glob("*.py"))


def test_item_economics_domain_has_no_spec_identity_hashing():
    modules = _domain_modules()
    serializer = PACKAGE_ROOT / "serializers.py"
    serializer_text = serializer.read_text()
    assert serializer_text.count('"config_fingerprint": scenario["config_fingerprint"]') == 1

    for module in modules:
        source = module.read_text()
        if module == serializer:
            source = source.replace("config_fingerprint", "")
        assert not any(term in source for term in FINGERPRINT_TERMS), module


def test_item_economics_domain_has_no_sqlalchemy_or_model_table_imports():
    for module in _domain_modules():
        source = module.read_text()
        assert not any(term in source for term in SQL_IMPORT_TERMS), module
