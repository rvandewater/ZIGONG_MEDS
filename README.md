# Zigong MEDS Extraction ETL

<!-- Placeholders until available: the PyPI badges resolve once Zigong-MEDS is published; replace
CODECOV_TOKEN_PLACEHOLDER with the repo's Codecov badge token and zenodo.XXXXXXX with its Zenodo DOI. -->

[![PyPI - Version](https://img.shields.io/pypi/v/Zigong-MEDS)](https://pypi.org/project/Zigong-MEDS/)
[![codecov](https://codecov.io/gh/rvandewater/ZIGONG_MEDS/graph/badge.svg?token=CODECOV_TOKEN_PLACEHOLDER)](https://codecov.io/gh/rvandewater/ZIGONG_MEDS)
[![tests](https://github.com/rvandewater/ZIGONG_MEDS/actions/workflows/synthetic-etl.yaml/badge.svg)](https://github.com/rvandewater/ZIGONG_MEDS/actions/workflows/synthetic-etl.yaml)
[![code-quality](https://github.com/rvandewater/ZIGONG_MEDS/actions/workflows/code-quality-main.yaml/badge.svg)](https://github.com/rvandewater/ZIGONG_MEDS/actions/workflows/code-quality-main.yaml)
![python](https://img.shields.io/badge/python-%3E%3D3.11.4%2C%20%3C3.14-blue?logo=python&logoColor=white)
![Static Badge](https://img.shields.io/badge/MEDS-0.4.1-blue)
[![license](https://img.shields.io/badge/License-MIT-green.svg?labelColor=gray)](https://github.com/rvandewater/ZIGONG_MEDS#license)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/rvandewater/ZIGONG_MEDS/pulls)
[![contributors](https://img.shields.io/github/contributors/rvandewater/ZIGONG_MEDS.svg)](https://github.com/rvandewater/ZIGONG_MEDS/graphs/contributors)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23676570.svg)](https://doi.org/10.5281/zenodo.23676570)

This pipeline extracts the
[Zigong Fourth People's Hospital ICU infection database v1.1](https://physionet.org/content/icu-infection-zigong-fourth/1.1/)
from PhysioNet into the [MEDS format](https://medical-event-data-standard.github.io/). The release holds
2,790 ICU patients with infection, one hospital admission each, from Zigong Fourth People's Hospital in
Sichuan, China. It was built from the
[ETL_MEDS_Template](https://github.com/Medical-Event-Data-Standard/ETL_MEDS_Template) and uses the
config-only layout introduced by [MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) 0.7.

## Usage

Zigong is a credentialed dataset. You need a PhysioNet account that has signed the project's data use
agreement.

```bash
pip install git+https://github.com/rvandewater/ZIGONG_MEDS.git
export DATASET_DOWNLOAD_USERNAME=$PHYSIONET_USERNAME
export DATASET_DOWNLOAD_PASSWORD=$PHYSIONET_PASSWORD
meds-extract-run spec=Zigong output_dir=$MEDS_OUTPUT_DIR
```

When you run this, the program will:

1. Download the release (seven `dt*.csv` tables, about 840 MB) from PhysioNet into
    `$MEDS_OUTPUT_DIR/.meds_extract_run/raw_input`. Pass `download_dest_dir=$RAW_INPUT_DIR` to keep the raw
    data somewhere durable and reuse it across runs.
2. Build the MEDS cohort from those files and write it to `$MEDS_OUTPUT_DIR` (`data/` and `metadata/`).
    All transformations and joins are declared in
    [`src/Zigong_MEDS/event_configs.yaml`](src/Zigong_MEDS/event_configs.yaml).

If you already have the PhysioNet release on disk, skip the download and point `input_dir` at the
directory that contains `dtBaseline.csv`, `dtDrugs.csv`, `dtICD.csv`, `dtLab.csv`, `dtNursingChart.csv`,
`dtOutCome.csv` and `dtTransfer.csv`:

```bash
meds-extract-run spec=Zigong output_dir=$MEDS_OUTPUT_DIR \
	do_download=false input_dir=/path/to/icu-infection-zigong-fourth-1.1
```

To parallelize the stages, pass a runner file:

```bash
printf 'parallelize:\n  n_workers: 8\n  launcher: joblib\n' >runner.yaml
meds-extract-run spec=Zigong output_dir=$MEDS_OUTPUT_DIR stage_runner_fp=runner.yaml
```

Run `meds-extract-run --help` for every option.

## How this ETL is defined

The package contains no Python. The whole ETL is one MESSY (MEDS-Extract Specification Syntax YAML)
file, [`src/Zigong_MEDS/event_configs.yaml`](src/Zigong_MEDS/event_configs.yaml). It declares:

- **`sources:`**: where the raw data lives (the PhysioNet release).
- **`etl:`**: the dataset name and sharding options.
- **One block per raw table**: how each row becomes one or more MEDS events.

`pyproject.toml` registers the file with MEDS-Extract's `MEDS_extract.pipelines` entry-point group under
the name `Zigong`. That registration is what makes `spec=Zigong` work. No pre-MEDS step is needed:
tables without `PATIENT_ID` (`dtLab`, `dtNursingChart`) are joined to `dtBaseline` on `INP_NO` inside the
config.

**Times.** Every source time is an offset in hours from hospital admission. The ETL places them on a
shared pseudotime anchor, 1970-01-01 00:00 = admission, which preserves order and intervals without
claiming a real calendar date. Each patient has exactly one admission, so offsets never collide.

## Events

| Table            | Event codes                                                                                                                                       | Notes                                                                                                                                                |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dtBaseline`     | `HOSPITAL_ADMISSION`, `AGE_AT_ADMISSION`, `SEX//…`, `ADMISSION_DEPARTMENT//…`, `INFECTION_SITE//…`, `ICU_DISCHARGE`, `HOSPITAL_DISCHARGE`         | Age is the `numeric_value`.                                                                                                                          |
| `dtTransfer`     | `TRANSFER_TO//{dept}`, `TRANSFER_FROM//{dept}`                                                                                                    | The reason is kept in `transfer_reason`. See [#3](https://github.com/rvandewater/ZIGONG_MEDS/issues/3).                                              |
| `dtICD`          | `DIAGNOSIS//ICD//{code}`                                                                                                                          | Placed at hospital discharge. The clinician's description is the `text_value`; `diagnosis_sequence` and `discharge_diagnosis_status` are kept.       |
| `dtLab`          | `LAB//{category}//{item}//{unit}`                                                                                                                 | A missing unit becomes `UNK`. `reference_range` is kept.                                                                                             |
| `dtDrugs`        | `MEDICATION//{drug}`                                                                                                                              | Prescription time. `Formula` is the `text_value`.                                                                                                    |
| `dtNursingChart` | `NURSING//{MEASUREMENT}` (vitals, ventilation, consciousness, GCS components, lines and tubes, risk and pain scores, intake and output, notes, …) | One code per charted column. Vital signs carry a `unit` column. GCS components carry the score as the `numeric_value` and the charted label as text. |
| `dtOutCome`      | `MEDS_DEATH`, `FOLLOW_UP_VITAL_STATUS//…`, `SF36//{ITEM}//{answer}`, `DISCHARGE_DEPARTMENT//…`                                                    | Follow-up events are placed at `Follow_Date`; the discharge department at hospital discharge.                                                        |

Every event linked to a stay carries `inpatient_stay_id` (`INP_NO`). The R-written CSVs encode missing
values as the string `NA` or a quoted empty string; both are treated as missing, as are text entries with
no letters or digits.

## Code metadata

`metadata/codes.parquet` gives every code a `description`. The release ships no code dictionary (its
`datDictionary.csv` describes table columns, not code values), so each event block in the config has a
`_metadata: _self:` template that states what the source column records and names it, for example
`Sex: Female (dtBaseline.SEX)` or `Heart rate, /min (dtNursingChart.heart_rate)`. Department, drug,
lab, infection-site and SF-36 answer names are inserted as the release records them. The column
meanings come from the column names and the
[PhysioNet documentation](https://physionet.org/content/icu-infection-zigong-fourth/1.1/) and its
descriptor paper (Xu et al. 2022, CC BY 4.0).

| Codes                                                                                                                                   | `parent_codes`                                                   | Source                                                                                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DIAGNOSIS//ICD//{code}`                                                                                                                | `ICD10CN/{code}` for well-formed codes                           | The release documents ICD-10 codes; the code format is OMOP's ICD10CN ([OHDSI Vocabulary-v5.0 `ICD10CN/load_stage.sql`](https://github.com/OHDSI/Vocabulary-v5.0/blob/6533b8f38f01d5e9982bdcb27aa08b021430b28e/ICD10CN/load_stage.sql), Unlicense) |
| `NURSING//` `TEMPERATURE`, `HEART_RATE`, `RESPIRATORY_RATE`, `OXYGEN_SATURATION`, `SYSTOLIC_BLOOD_PRESSURE`, `DIASTOLIC_BLOOD_PRESSURE` | `LOINC/8310-5`, `8867-4`, `9279-1`, `2708-6`, `8480-6`, `8462-4` | [HL7 FHIR R4 vital-signs profile](https://hl7.org/fhir/R4/observation-vitalsigns.html) (CC0)                                                                                                                                                       |
| Everything else                                                                                                                         | none                                                             | Description only                                                                                                                                                                                                                                   |

- **Diagnosis parents.** A code is its own `ICD10CN/` parent when it has one of the Chinese-edition
    shapes (`J18.900`, `A41.900x001`, `I10.x01`) or is a morphology code (`M80000/3`), so
    vocabulary tooling can resolve its title. Two spellings are normalized to OMOP's form, which is an
    inference from the format rather than a documented rule: an upper-case extension marker `X` becomes
    `x`, and a trailing dagger `+` is dropped. Dagger and asterisk pairs and other shapes get no parent.
    Athena's ICD10CN is built from a 2016 release, so a code added later will not resolve there.
- **SF-36.** Descriptions name each item after its source column in our own words. They do not
    reproduce the questionnaire's item wording, which is licensed in some versions.
- **Fixed codes.** `_self` metadata attaches through the columns a code expression references, so
    `HOSPITAL_ADMISSION`, `ICU_DISCHARGE`, `HOSPITAL_DISCHARGE` and `MEDS_DEATH` are written as
    `"CODE" if $PATIENT_ID == $PATIENT_ID`. A row without a subject id never reaches extraction, so this
    changes no events.

## Data notes

- **Coarse nursing chart timestamps.** `dtNursingChart` has about 1 million rows with a usable
    `ChartTime` but only about 23,000 distinct (patient, `ChartTime`) pairs. A typical timestamp covers 26
    source rows, and the largest covers 266. This comes from the source release, not the ETL. In the MEDS
    output, one timestamp therefore holds many readings of the same measurement, on average about 15
    `NURSING//HEART_RATE` values, and similarly for blood pressure, SpO2 and other vitals. The order of events
    within a timestamp carries no clinical meaning. When defining tasks or features:
    - Do not rely on order within a timestamp, such as "last value before X", minute-level features, or
        sequence models that treat event order as real time order.
    - Choose prediction times that do not fall inside a timestamp's group of events, and aggregate values
        within a timestamp (for example mean, min, or max) rather than picking one.
- **Dropped nursing rows.** 313,974 nursing rows (23%) belong to 723 stays that are not in the cohort
    (`dtBaseline`), and all of them have `ChartTime = NA`; they are dropped. Rows charted more than 24 h before
    admission (9,011 rows, including some corrupt offsets) or after discharge (141) are dropped too.
- **Dropped labs.** Results timed after hospital discharge (4,415 rows, 0.3%) and placeholder values made
    only of dots or asterisks are dropped.
- **Coarse death dates.** `Death_Date` has about day precision. In-hospital deaths typically fall about 12 h
    before the recorded discharge, so a stay's last events can follow `MEDS_DEATH`. See
    [#4](https://github.com/rvandewater/ZIGONG_MEDS/issues/4).
- **Line and tube columns** (`CVC`, `PICC`, `Gastric_tube`, …) hold the length in cm, used as the
    `numeric_value`, or a status such as "removed" kept as text. The numeric values of `Endotracheal_intubation`
    duplicate `Endotracheal_intubation_Depth`, so only its statuses are emitted.
- **Bounded scores.** RASS, NRS and CPOT values outside their scales (-5..+4, 0..10, 0..8) are dropped.
    Other vitals are not range-filtered; see [#7](https://github.com/rvandewater/ZIGONG_MEDS/issues/7).
- **Unmapped columns.** Five nursing columns are NA in every row. `MAP`, `PSIPAP`, `R` and `FIO2` hold only
    unit strings. `Invasive_SBP._1` is a documented technical duplicate, and `F` is documented as having no
    clinical relevance. See [#6](https://github.com/rvandewater/ZIGONG_MEDS/issues/6).
- **Local vocabularies.** Diagnoses use the release's Chinese national extension of ICD-10. They carry
    an `ICD10CN/` parent (see [Code metadata](#code-metadata)) but no WHO ICD-10 parent yet; see
    [#1](https://github.com/rvandewater/ZIGONG_MEDS/issues/1). Labs and drugs use local names with no
    LOINC or ATC parents; see [#8](https://github.com/rvandewater/ZIGONG_MEDS/issues/8). SF-36 answers are inconsistently coded in the
    source; see [#5](https://github.com/rvandewater/ZIGONG_MEDS/issues/5).
- **No ICU admission event.** The release records ICU discharge but not ICU entry; see
    [#2](https://github.com/rvandewater/ZIGONG_MEDS/issues/2).

## Testing

Zigong has no open demo release, so there are two synthetic checks:

- `tests/e2e_synthetic_test.py` writes a few fully synthetic rows with the release's exact headers and R
    `write.csv` encoding, runs `meds-extract-run spec=Zigong` over them, and checks the events, times, values
    and missing-value handling it produces.
- The [Synthetic ETL workflow](.github/workflows/synthetic-etl.yaml) generates raw files straight from the
    config with [MESSY-synth](https://pypi.org/project/MESSY-synth/) and runs the ETL over them. It fails if
    any event block produces no events.

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run pre-commit run --all-files

# MESSY-synth needs Python >= 3.12.
uv run --with MESSY-synth==0.0.1 MESSY-synth ./src/Zigong_MEDS/event_configs.yaml -o raw_synthetic/
uv run meds-extract-run spec=Zigong output_dir=zigong_meds_synth/ \
	do_download=false input_dir=raw_synthetic/
```

For a reusable checklist on mapping a new dataset, see the
[dataset mapping checklist](https://github.com/rvandewater/ETL_MEDS_Template/blob/main/docs/MEDS_ETL_MAPPING.md)
in ETL_MEDS_Template.

## Citation

If you use this ETL, please cite the Zigong database and its descriptor paper:

```bibtex
@article{PhysioNet-icu-infection-zigong-fourth-1.1,
  author = {Xu, Ping and Chen, Lin and Zhang, Zhongheng},
  title = {{Critical care database comprising patients with infection at Zigong Fourth People's Hospital}},
  journal = {{PhysioNet}},
  year = {2022},
  month = jun,
  note = {Version 1.1},
  doi = {10.13026/xpt9-z726},
  url = {https://doi.org/10.13026/xpt9-z726}
}
@article{xuCriticalCareDatabase2022a,
  title = {Critical {{Care Database Comprising Patients With Infection}}},
  author = {Xu, Ping and Chen, Lin and Zhu, Yuanfang and Yu, Shuai and Chen, Rangui and Huang, Wenbin and Wu, Fuli and Zhang, Zhongheng},
  year = 2022,
  month = mar,
  journal = {Frontiers in Public Health},
  volume = {10},
  publisher = {Frontiers},
  issn = {2296-2565},
  doi = {10.3389/fpubh.2022.852410},
  langid = {english},
  keywords = {big data & analytics,Critical Care,database,Infections,Open access},
}
```

See also [`CITATION.cff`](CITATION.cff).
