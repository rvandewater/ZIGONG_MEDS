"""The Zigong ICU infection database MEDS ETL — a configuration package, not a library.

This distribution ships no code. Its entire content is ``Zigong_MEDS/event_configs.yaml``, a MESSY
(MEDS-Extract Specification Syntax YAML) document declaring where the raw Zigong data comes from and
how every event is extracted from it. ``pyproject.toml`` registers that file with MEDS-Extract's
``MEDS_extract.pipelines`` entry-point group under the name ``Zigong``, so the ETL runs as::

    meds-extract-run spec=Zigong output_dir=$MEDS_OUTPUT_DIR

This package exists so the YAML is addressable as package data —
``importlib.resources.files("Zigong_MEDS")`` — from an installed wheel. Nothing here is importable API.
"""
