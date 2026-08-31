"""
NP2 -- Build the UsageProcessor Class
=======================================
Phase 1, Lab 2. Turns the NP1 one-off exploration into a reusable,
testable processing class.

Method order matters and mirrors the lab's separation of concerns:
    load_data() -> clean_data() -> derive_time_features()
    -> aggregate_to_grid_time() -> derive_activity_features()
    -> compute_kpis() -> export_summary()

Grain discipline (Core Dataset Contract):
    raw/canonical grain      = timestamp + grid_id + country_code
    aggregate_to_grid_time() = timestamp + grid_id   (country_code summed away)
KPIs are computed AFTER the grain transition, never before it.
"""

import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("NP2.UsageProcessor")

RAW_TO_CANONICAL = {
    "datetime": "timestamp",
    "CellID": "grid_id",
    "countrycode": "country_code",
    "smsin": "sms_in",
    "smsout": "sms_out",
    "callin": "call_in",
    "callout": "call_out",
    "internet": "internet_activity",
}

REQUIRED_CANONICAL_COLS = [
    "timestamp", "grid_id", "country_code",
    "sms_in", "sms_out", "call_in", "call_out", "internet_activity",
]

ACTIVITY_COLS = ["sms_in", "sms_out", "call_in", "call_out", "internet_activity"]


class UsageProcessor:
    """Reusable cleaning / grain-transition / KPI pipeline for one
    telecom activity file (or an in-memory DataFrame of the same shape).
    """

    def __init__(self, source):
        """
        Parameters
        ----------
        source : str | pandas.DataFrame
            A file path to a raw sms-call-internet-mi-*.csv, or an
            already-loaded raw DataFrame with the original raw column names.
        """
        self.source = source
        self.raw_df = None          # exactly as loaded, never mutated further
        self.clean_df = None        # canonical names, quarantined rows removed, nulls handled
        self.grid_time_df = None    # one row per grid_id + timestamp (country_code summed away)
        self.daily_summary = None
        self.grid_summary = None

        # Counters for the four-number log line required by NP2's acceptance criteria
        self._counts = {
            "input_rows": 0,
            "rejected_rows": 0,
            "nulls_handled": 0,
            "output_rows": 0,
        }

    # ------------------------------------------------------------------
    # load_data
    # ------------------------------------------------------------------
    def load_data(self) -> pd.DataFrame:
        """Load the raw file (or accept an already-loaded raw DataFrame).
        Does not rename, clean or reject anything -- that's clean_data()'s job.
        """
        if isinstance(self.source, pd.DataFrame):
            self.raw_df = self.source.copy()
        else:
            self.raw_df = pd.read_csv(self.source)

        self._counts["input_rows"] = len(self.raw_df)
        log.info("load_data: loaded %d raw rows", self._counts["input_rows"])
        return self.raw_df

    # ------------------------------------------------------------------
    # clean_data
    # ------------------------------------------------------------------
    def clean_data(self) -> pd.DataFrame:
        """Rename to canonical schema, quarantine invalid rows, apply the
        documented curated-layer null-to-zero rule for ACTIVITY MEASURES ONLY.

        Quarantined (dropped from the curated layer, counted, never silently
        kept): missing grid_id, missing timestamp, negative activity values.
        Missing grid_id/timestamp is a data-quality failure -- it is never
        defaulted. Blank activity values are NOT a quarantine reason; they
        are null-to-zero'd here and the count is recorded.
        """
        if self.raw_df is None:
            raise RuntimeError("Call load_data() before clean_data().")

        df = self.raw_df.rename(columns=RAW_TO_CANONICAL).copy()

        missing_required = [c for c in REQUIRED_CANONICAL_COLS if c not in df.columns]
        if missing_required:
            raise ValueError(f"Missing required columns after mapping: {missing_required}")

        n_before = len(df)

        # Quarantine: missing grid_id or timestamp -- never defaulted
        mask_missing_keys = df["grid_id"].isna() | df["timestamp"].isna()

        # Quarantine: negative activity values in ANY activity column
        mask_negative = pd.Series(False, index=df.index)
        for col in ACTIVITY_COLS:
            mask_negative = mask_negative | (df[col] < 0)

        mask_reject = mask_missing_keys | mask_negative
        rejected = df[mask_reject]
        df = df[~mask_reject].copy()

        self._counts["rejected_rows"] = len(rejected)
        if len(rejected):
            log.warning(
                "clean_data: quarantined %d rows (missing key=%d, negative activity=%d)",
                len(rejected), int(mask_missing_keys.sum()), int(mask_negative.sum()),
            )

        # Curated-layer null-to-zero rule -- ACTIVITY MEASURES ONLY, after quarantine
        nulls_before = int(df[ACTIVITY_COLS].isna().sum().sum())
        df[ACTIVITY_COLS] = df[ACTIVITY_COLS].fillna(0)
        self._counts["nulls_handled"] = nulls_before
        log.info(
            "clean_data: %d input rows -> %d rejected, %d activity-nulls set to 0, %d rows remain",
            n_before, len(rejected), nulls_before, len(df),
        )

        self.clean_df = df
        return self.clean_df

    # ------------------------------------------------------------------
    # derive_time_features
    # ------------------------------------------------------------------
    def derive_time_features(self) -> pd.DataFrame:
        """date, hour, day_of_week from timestamp."""
        if self.clean_df is None:
            raise RuntimeError("Call clean_data() before derive_time_features().")

        df = self.clean_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.day_name()
        self.clean_df = df
        log.info("derive_time_features: date/hour/day_of_week added")
        return self.clean_df

    # ------------------------------------------------------------------
    # aggregate_to_grid_time  -- THE GRAIN TRANSITION
    # ------------------------------------------------------------------
    def aggregate_to_grid_time(self) -> pd.DataFrame:
        """Collapse country_code rows to exactly one row per grid_id + timestamp
        by SUMMING the five activity measures. country_code is NOT carried
        into the output -- it belongs to the raw/canonical layer only.

        This is a separate, named, testable step precisely so it can be
        ported unchanged into Spark at SP3.
        """
        if self.clean_df is None:
            raise RuntimeError("Call derive_time_features() before aggregate_to_grid_time().")

        n_before = len(self.clean_df)

        grouped = (
            self.clean_df
            .groupby(["grid_id", "timestamp", "date", "hour", "day_of_week"], as_index=False)[ACTIVITY_COLS]
            .sum()
        )

        # Grain assertion -- fail loudly rather than silently downstream
        dup_count = grouped.duplicated(subset=["grid_id", "timestamp"]).sum()
        if dup_count > 0:
            raise AssertionError(
                f"aggregate_to_grid_time produced {dup_count} duplicate (grid_id, timestamp) rows"
            )
        assert "country_code" not in grouped.columns, "country_code leaked into grid/hour analytics grain"

        self._counts["output_rows"] = len(grouped)
        log.info(
            "aggregate_to_grid_time: %d rows -> %d rows (grid/hour grain), 0 duplicates confirmed",
            n_before, len(grouped),
        )

        self.grid_time_df = grouped
        return self.grid_time_df

    # ------------------------------------------------------------------
    # derive_activity_features
    # ------------------------------------------------------------------
    def derive_activity_features(self) -> pd.DataFrame:
        """total_sms, total_calls, total_activity on the grid/hour grain."""
        if self.grid_time_df is None:
            raise RuntimeError("Call aggregate_to_grid_time() before derive_activity_features().")

        df = self.grid_time_df.copy()
        df["total_sms"] = df["sms_in"] + df["sms_out"]
        df["total_calls"] = df["call_in"] + df["call_out"]
        # project-defined composite indicator -- not an official telecom KPI
        df["total_activity"] = df["total_sms"] + df["total_calls"] + df["internet_activity"]

        self.grid_time_df = df
        log.info("derive_activity_features: total_sms/total_calls/total_activity added")
        return self.grid_time_df

    # ------------------------------------------------------------------
    # compute_kpis
    # ------------------------------------------------------------------
    def compute_kpis(self):
        """Daily summary (per date) and grid summary (per grid_id),
        computed strictly on the grid/hour grain -- never the country-code grain.
        """
        if self.grid_time_df is None or "total_activity" not in self.grid_time_df.columns:
            raise RuntimeError("Call derive_activity_features() before compute_kpis().")

        df = self.grid_time_df

        self.daily_summary = (
            df.groupby("date", as_index=False)
              .agg(
                  total_activity=("total_activity", "sum"),
                  total_sms=("total_sms", "sum"),
                  total_calls=("total_calls", "sum"),
                  total_internet=("internet_activity", "sum"),
                  active_grids=("grid_id", "nunique"),
              )
        )

        self.grid_summary = (
            df.groupby("grid_id", as_index=False)
              .agg(
                  total_activity=("total_activity", "sum"),
                  peak_hour_activity=("total_activity", "max"),
                  active_hours=("hour", "nunique"),
              )
              .sort_values("total_activity", ascending=False)
        )

        log.info(
            "compute_kpis: daily_summary=%d rows, grid_summary=%d rows",
            len(self.daily_summary), len(self.grid_summary),
        )
        return self.daily_summary, self.grid_summary

    # ------------------------------------------------------------------
    # export_summary
    # ------------------------------------------------------------------
    def export_summary(self, output_dir: str = ".") -> dict:
        """Write daily_summary.csv and grid_summary.csv, log the four
        required numbers, and return them for the caller / tests.
        """
        if self.daily_summary is None or self.grid_summary is None:
            raise RuntimeError("Call compute_kpis() before export_summary().")

        daily_path = f"{output_dir}/daily_summary.csv"
        grid_path = f"{output_dir}/grid_summary.csv"
        self.daily_summary.to_csv(daily_path, index=False)
        self.grid_summary.to_csv(grid_path, index=False)

        log.info(
            "export_summary: input_rows=%d rejected_rows=%d nulls_handled=%d output_rows=%d",
            self._counts["input_rows"], self._counts["rejected_rows"],
            self._counts["nulls_handled"], self._counts["output_rows"],
        )
        log.info("export_summary: wrote %s and %s", daily_path, grid_path)

        return {
            "daily_summary_path": daily_path,
            "grid_summary_path": grid_path,
            "counts": dict(self._counts),
        }

    # ------------------------------------------------------------------
    # convenience: run the whole pipeline in order
    # ------------------------------------------------------------------
    def run(self, output_dir: str = ".") -> dict:
        self.load_data()
        self.clean_data()
        self.derive_time_features()
        self.aggregate_to_grid_time()
        self.derive_activity_features()
        self.compute_kpis()
        return self.export_summary(output_dir)


# ----------------------------------------------------------------------
# One small validation per method -- required by NP2's acceptance criteria.
# Run this file directly to execute them against a real CSV.
# ----------------------------------------------------------------------
def validate(path: str):
    proc = UsageProcessor(path)

    raw = proc.load_data()
    assert len(raw) > 0, "load_data: expected at least one row"

    clean = proc.clean_data()
    assert clean["grid_id"].isna().sum() == 0, "clean_data: grid_id nulls should be quarantined"
    assert clean["timestamp"].isna().sum() == 0, "clean_data: timestamp nulls should be quarantined"
    for col in ACTIVITY_COLS:
        assert (clean[col] < 0).sum() == 0, f"clean_data: negative values remain in {col}"

    proc.derive_time_features()
    assert {"date", "hour", "day_of_week"}.issubset(proc.clean_df.columns), \
        "derive_time_features: expected columns missing"

    grid_time = proc.aggregate_to_grid_time()
    assert grid_time.duplicated(subset=["grid_id", "timestamp"]).sum() == 0, \
        "aggregate_to_grid_time: duplicates on (grid_id, timestamp)"
    assert len(grid_time) < len(clean), \
        "aggregate_to_grid_time: expected strictly fewer rows than input"
    assert "country_code" not in grid_time.columns, \
        "aggregate_to_grid_time: country_code must not appear in analytics output"

    features = proc.derive_activity_features()
    assert {"total_sms", "total_calls", "total_activity"}.issubset(features.columns), \
        "derive_activity_features: expected derived columns missing"

    daily, grid = proc.compute_kpis()
    assert len(daily) > 0 and len(grid) > 0, "compute_kpis: expected non-empty summaries"

    result = proc.export_summary(output_dir=".")
    counts = result["counts"]
    assert counts["output_rows"] < counts["input_rows"], \
        "export_summary: output_rows should be less than input_rows after aggregation"

    log.info("ALL NP2 VALIDATIONS PASSED: %s", counts)
    return proc


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python usage_processor.py <path_to_daily_csv>")
        sys.exit(1)
    validate(sys.argv[1])