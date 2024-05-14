#!/usr/bin/python3
"""Translate teacher's marking spreadsheet into student-readable reports."""

import argparse
from contextlib import redirect_stdout
from pathlib import Path
import io
from textwrap import wrap

import pandas as pd
import pandera as pa
from validation import schema
import pdfkit
from tqdm import tqdm


class Evaluation:
    """Expected input data structure :
    - excel-like file : uses pd.read_excel
    - Expected labels are case sensitive and positions are assumed so:
    |NOM   |CLASSE|EX.Y.Z|others|
    |Barême|...
    |......|...
    ANCHOR[id=glob]
    """

    styles = [
        {
            "selector": "td,tr,th",
            "props": [
                ("border-right", "1px solid black"),
                ("border-collapse", "collapse"),
                ("text-align", "center"),
            ],
        }
    ]

    def __init__(self, data_file: str, glob_total: float):
        """Load data into a pandas df. Do checks on data structure.
        Requires odfpy for ods files.

        Args:
            data_file (str): Path to spreadsheet file
            glob_total (float): final point total

        Raises:
            ValueError: if no name column
            ValueError: if first row is mislabeled
        """
        self.file_name = Path(data_file).stem
        self.glob_total = glob_total
        self.df = pd.read_excel(data_file)
        self.df.rename(columns=lambda col: col.upper(), inplace=True)

        # if "NOM" not in self.df.columns:
        #     raise ValueError(
        #         "Missing 'NOM' as first column. Possibly mislabeled.")
        # if not self.df.at[0, "NOM"].capitalize() in ["Barême", "Bareme"]:
        #     raise ValueError(
        #         "Missing 'Barême' as first row. Possibly mislabeled.")

        # Data format checks
        try:
            schema.validate(self.df.replace("ABS", 0), lazy=True)
        except pa.errors.SchemaError as exc:
            print(exc)

        # Grab and remove absents
        self.absent = (
            self.df.set_index(["NOM"])[lambda df: df.isin(["ABS"])]
            .dropna(how="all")
            .index
        )
        self.df.replace("ABS", 0, inplace=True)

        # Grab students with individual bonuses
        self.has_pap = "PAP" in self.df.columns
        if self.has_pap:
            self.pap = self.df.set_index(
                ["NOM"])["PAP"].dropna(how="all").index[1:]
            self.pap_total = self.df.set_index(["NOM"]).at["Barême", "PAP"]
        else:
            self.pap_total = 0

        # Split and store useful column names
        # Exclude student info and PAP column
        self.all_questions = self.df.columns.difference(
            ["REMARQUES", "PAP", "CLASSE", "NOM"]
        )
        main = self.df.filter(regex="E\\d").columns
        self.other = self.all_questions.difference(main)

        # The definition of self.exos assumes elements of main are either
        # "EX" or "EX.whatever"
        def exercise_name(name):
            try:
                return name[: name.index(".")]
            except ValueError:
                return name

        self.exos = main.map(exercise_name).unique()
        self.bonuses = self.df.filter(like="BONUS").columns

        # Compute final mark
        self.df["TOTAL"] = self.df[self.all_questions].sum(axis=1)
        bonus_total = self.df[self.df.NOM ==
                              "Barême"][self.bonuses].sum(axis=1)
        self.TOTAL = float(
            (self.df[self.df.NOM == "Barême"].TOTAL - bonus_total).iloc[0]
        )
        self.TOTAL_PAP = float(self.TOTAL - self.pap_total)
        if self.glob_total < 0:
            self.glob_total = self.TOTAL
        # try:
        self.glob_coeff = self.glob_total / self.TOTAL
        # except ZeroDivisionError as e:
        #     raise ZeroDivisionError(
        #         "TOTAL is zero, did you forget to input Barême ?"
        #     ) from e

        # Compute total mark per exercise
        totals_exos = ["TOTAL " + exo for exo in self.exos]
        for exo, total in zip(self.exos, totals_exos):
            self.df[total] = self.df.filter(
                regex=rf"{exo}(\.)?(?(1)[.\dA-Za-z]*)$"
            ).sum(axis=1)

        # Once it's all computed, reshape
        self.MULTICLASSE = "CLASSE" in self.df.columns
        self.groups = ["CLASSE", "NOM"] if self.MULTICLASSE else "NOM"
        id_vars = ["NOM", "CLASSE"] if self.MULTICLASSE else ["NOM"]
        self.df_long = self.df.melt(
            id_vars=id_vars, var_name="QUESTION", value_name="NOTE"
        )

    def make_bareme(self, filtered_df):
        return (
            filtered_df.drop(columns=self.groups)
            .rename(columns={"NOTE": "BAREME"})
            .set_index("QUESTION")
        )

    def print_question(self, bareme, curr, to_pdf):
        if to_pdf:
            print(
                pd.concat([bareme, curr], axis=1)
                .T.style.format(precision=2)
                .set_table_styles(Evaluation.styles)
                .to_html()
            )
        else:
            print(pd.concat([bareme, curr], axis=1).T)

    def _individual_reports(self, to_pdf=False):
        """Print a report of detailed student marks
        ANCHOR[id=indiv]

        Args:
            to_pdf (bool, optional): Wether to print results to a PDF.
                Defaults to False.
        """
        with pd.option_context("expand_frame_repr", False):
            grouped = self.df_long.groupby(self.groups)

            for group, eleve in tqdm(grouped) if to_pdf else grouped:
                nom = group[1] if self.MULTICLASSE else group
                if nom == "Barême" or nom in self.absent:
                    continue

                # Printing starts
                if to_pdf:
                    print("<div style='page-break-inside: avoid;'>")
                line_break = "<br>" if to_pdf else "\n"

                # Student ID
                classe = f" -- {group[0]}" if self.MULTICLASSE else ""
                print(f"NOM : {nom}{classe}\n")

                # Print points
                eleve = eleve.drop(columns=self.groups).set_index("QUESTION")
                for exo in self.exos:
                    # The following regex matches if QUESTION is either
                    # - TOTAL E[number]
                    # - E[number][dot, number, letter]
                    query = rf"QUESTION.str.match('(TOTAL )?(?(1){exo}|{exo}(\\.)?(?(2)[.\\dA-Za-z]*))$')"
                    bareme = self.make_bareme(
                        self.df_long.query("(NOM == 'Barême') & " + query)
                    )
                    curr = eleve.query(query)
                    self.print_question(bareme, curr, to_pdf)
                for question in self.other:
                    query = "QUESTION == @question"
                    bareme = self.make_bareme(
                        self.df_long.query("(NOM == 'Barême') &" + query)
                    )
                    curr = eleve.query(query)
                    self.print_question(bareme, curr, to_pdf)

                # Print remarks
                width_limit = 50
                try:
                    remarque = eleve.query(
                        "QUESTION == 'REMARQUES'").NOTE.iloc[0]
                except IndexError:
                    # supposed to handle the case where there's no REMARQUES column
                    remarque = ""
                if remarque != "" and not pd.isna(remarque):
                    print(
                        f"{line_break}REMARQUE : {line_break.join(wrap(remarque, width=width_limit))}"
                    )
                # Print total
                is_pap = False
                if self.has_pap:
                    is_pap = nom in self.pap
                coeff_pap = self.TOTAL / self.TOTAL_PAP if is_pap else 1.0
                coeff = coeff_pap * self.glob_coeff
                note_student = round(
                    eleve.at["TOTAL", "NOTE"] * coeff, ndigits=2)
                print(f"{line_break}NOTE FINALE : {note_student}/{self.glob_total}")
                if is_pap:
                    print(
                        f"{line_break}COEFFICIENT PAP : {round(coeff_pap, ndigits=2)}"
                    )

                print(line_break * 2, "".center(50, "="), line_break * 2)
                if to_pdf:
                    print("</div>")

            # Print absent students
            if len(self.absent) > 0:
                print(
                    f"ABSENT{'S' if len(self.absent)>1 else ''} : {list(self.absent)}"
                )

    def class_report(self):
        """Print class wide stats"""
        print(
            (
                self.df.query(
                    "NOM != 'Barême' & not NOM in @self.absent").TOTAL
            ).describe()
        )

    def done_percent(self):
        """Print the marking progress percentage"""
        n_eleves = self.df.shape[0] - 1  # enlève le barême
        n_questions = self.df[self.all_questions].columns.size
        n_empty = self.df[self.all_questions].isna().sum().sum()
        done_percent = 100 * (1 - n_empty / (n_questions * n_eleves))
        print(f"{done_percent:.2f}% done")

    def print(self, which: str, to_pdf=False):
        """Print results to stdout or pdf depending on args

        Args:
            which (str): "class" for global stats or "individual" for student cards
            to_pdf (bool, optional): Wether to print results to a PDF. Defaults to False.
        """
        options = {
            "encoding": "UTF-8",
        }
        match which:
            case "class":
                self.class_report()
            case "individual":
                if to_pdf:
                    with redirect_stdout(io.StringIO()) as f:
                        self._individual_reports(to_pdf=True)
                    output = f.getvalue()
                    pdfkit.from_string(
                        output, f"{self.file_name}_reports.pdf", options=options
                    )
                    print(f"Output file : {self.file_name}_reports.pdf")
                else:
                    self._individual_reports()
            case _:
                print("Wrong argument.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    parser.add_argument("file", help="path to spreadsheet.")
    parser.add_argument(
        "--pdf", help="print results to pdf", action="store_true")
    parser.add_argument(
        "--quiet", "-q", help="Only load file", action="store_true")
    parser.add_argument("--total", "-t", help="Desired total marks.")
    # Argument group
    group.add_argument(
        "--stats",
        "-s",
        help="Descriptive stats on all tests given in file.",
        action="store_true",
    )
    group.add_argument(
        "--done",
        "-d",
        help="Progress in percent. Excludes all other info.",
        action="store_true",
    )
    args = parser.parse_args()

    evaluation = Evaluation(args.file, float(args.total) if args.total else -1)
    if not args.quiet:
        if not args.done:
            if not args.stats:
                evaluation.print("individual", to_pdf=args.pdf)
            else:
                evaluation.print("class")
        else:
            evaluation.done_percent()
