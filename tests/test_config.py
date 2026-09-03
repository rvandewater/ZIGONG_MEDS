from MEDS_extract.config import MessyConfig


def test_zigong_config_loads_and_covers_release_tables():
    config = MessyConfig.load("Zigong")

    assert config.dataset_name == "Zigong"
    assert set(config.table_prefixes) == {
        "dtBaseline",
        "dtDrugs",
        "dtICD",
        "dtLab",
        "dtNursingChart",
        "dtOutCome",
        "dtTransfer",
    }
    assert config.raw_version_for() == "1.1"
