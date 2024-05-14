import pandas as pd
import pandera as pa

columns = {
    "NOM": pa.Column(str),
    "CLASSE": pa.Column(str, required=False, nullable=True),
    r"E\d": pa.Column(float,  regex=True),
    "PAP": pa.Column(float, required=False, nullable=True),
    "REMARQUES": pa.Column(str, required=False, nullable=True)
}


def points_row_labeled(df: pd.DataFrame):
    # admissible_labels = ("Barême", "Bareme", "Points")
    admissible_labels = ("Barême", "Bareme", "Points")[0]
    return "NOM" in df.columns and df.NOM[0].capitalize() in admissible_labels


def points_present(df: pd.DataFrame):
    points_label = df.NOM[0]
    points = df[df.NOM == points_label]
    return points.isna().sum() <= 1


def nonzero_total(df: pd.DataFrame):
    points_label = df.NOM[0]
    points = pd.to_numeric(df[df.NOM == points_label].iloc[0], errors="coerce")
    is_total_nonzero = points.sum() > 0
    return is_total_nonzero


schema = pa.DataFrameSchema(
    columns, checks=[
        pa.Check(points_row_labeled, title="Points row is labeled",
                 name="labeled_points_row", ignore_na=False),
        pa.Check(points_present, title="All points are given", ignore_na=False),
        pa.Check(nonzero_total, title="Point total isn't zero",  ignore_na=False),
    ], ordered=True)
