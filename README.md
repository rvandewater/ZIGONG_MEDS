# Zigong MEDS ETL

Configuration-only [MEDS-Extract](https://github.com/mmcdermott/MEDS_extract) ETL for the
[Zigong Fourth People's Hospital ICU infection database v1.1](https://physionet.org/content/icu-infection-zigong-fourth/1.1/).

## Run

Obtain access to the PhysioNet release, then export its credentials:

```bash
export DATASET_DOWNLOAD_USERNAME="$PHYSIONET_USERNAME"
export DATASET_DOWNLOAD_PASSWORD="$PHYSIONET_PASSWORD"
meds-extract-run spec=Zigong output_dir="$MEDS_OUTPUT_DIR"
```

To use files already downloaded from PhysioNet:

```bash
meds-extract-run spec=Zigong output_dir="$MEDS_OUTPUT_DIR" \
	do_download=false input_dir="$RAW_ZIGONG_DIR"
```

The input directory must contain the release's `dtBaseline.csv`, `dtDrugs.csv`, `dtICD.csv`,
`dtLab.csv`, `dtNursingChart.csv`, `dtOutCome.csv`, and `dtTransfer.csv` files.

## Mapping

`src/Zigong_MEDS/event_configs.yaml` converts the documented hour offsets from hospital admission
to MEDS pseudotime using `1970-01-01` as a shared anchor. It maps demographics, admissions,
transfers, diagnoses, laboratory results, prescriptions, nursing observations, death, and follow-up
SF-36 responses. No external terminology mapping is claimed where the source does not document one.

For a reusable mapping checklist, see [docs/MEDS_ETL_MAPPING.md](docs/MEDS_ETL_MAPPING.md).

## Data caveats

**Nursing chart timestamps are coarse.** In v1.1, `dtNursingChart` has about 1 million rows with a
usable `ChartTime` but only about 23,000 distinct (patient, `ChartTime`) pairs. A typical timestamp
covers 26 source rows, and the largest covers 266. This comes from the source release, not the ETL.
In the MEDS output, one timestamp therefore holds many readings of the same measurement, on average
about 15 `NURSING//HEART_RATE` values, and similarly for blood pressure, SpO2, and other vitals. The
order of events within a timestamp carries no clinical meaning.

When defining tasks or features on this dataset:

- Do not rely on order within a timestamp, such as "last value before X", minute-level features, or
    sequence models that treat event order as real time order.
- Choose prediction times that do not fall inside a timestamp's group of events, and aggregate values
    within a timestamp (for example mean, min, or max) rather than picking one.

About 314,000 nursing rows (23%) have `ChartTime = NA` in the source and are dropped.

## Synthetic validation

```bash
uv pip install git+https://github.com/rvandewater/MESSY_synth.git
MESSY-synth src/Zigong_MEDS/event_configs.yaml -o raw_synthetic/
meds-extract-run spec=Zigong output_dir=zigong_meds_synth/ \
	do_download=false input_dir=raw_synthetic/
```

The CI workflow runs this smoke test without accessing real data.
