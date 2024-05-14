<!-- LTeX: language=en-US -->
# Usage
After being given executable rights, the shebang should work fine :
`pynotes.py [-h] [--pdf] [--quiet] [--total TOTAL] [--stats | --done] file`

Translate teacher's marking spreadsheet into one of the following (incompatible) options : 
- `default` student-readable individual reports 
- `--stats, -s` Descriptive stats on all tests given in file.
- `--done, -d` Marking progress in percent.

If `--done` is omitted, adding `--pdf` will print results to `[file]_[type].pdf`, where `[type]` is either `stats` or `reports`.
If provided, `--total TOTAL` gives all final marks in individual reports on a total of `TOTAL` points.

# Input structure
See data.ods file for an idea of what the input is expected to be.

The script expects the following table template. Columns names in *italics* are optional.

NOM          | *CLASSE* | EY.X   | ... | EY.X   | *OTHER* | *BONUS QUESTION* | *PAP*         | *REMARQUES*
-------------|----------|--------|-----|--------|---------|------------------|---------------|------------
Barême       | anything | number | ... | number | number  | number           | number        | Nothing
Student name | anything | number |     | number | number  | number           | either 1 or 0 | Good job!

Precisely : 
- Hard coded names and positions : NOM, Barême, PAP and REMARKS (if present)
- EY.X type questions
    - Y can be letter or number
    - no X value needed
    - get grouped as exercises according to Y values if present
- PAP column gets treated as points to subtract from the student expected points :

$$
\text{total mark} = \frac{\text{student total}}{\text{total gainable points} - \text{PAP points}}\times(\text{total gainable points})
$$

- Any column with "BONUS" in its name is counted as a bonus question

# Output examples -- WIP
See `output` folder for an idea of what the outputs can be.

# Requirements
No promises made.

- Python 3
- See [requirements.txt](./requirements.txt) for Python deps
- only non-Python dependency is [wkhtmltopdf](https://wkhtmltopdf.org/) to export to PDF. ⚠ This is your responsibility, the software doesn't check for it at install.

# License
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.
