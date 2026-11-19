"""Rules that hold across the gate rows of the gated units.

Each cell of a gate row says what the run does at that gate in one mode. The test sorts each cell into a class by its
opening words: the run stops for the user, the run goes on, or the row leaves its gates to another text. Then it checks
the order of the classes across the modes. A swap of two cells of different classes breaks the order.
"""
import re
import unittest

from test_work_modes_text import HEADER, PLUGIN, TABLE_UNITS, autonomy, read

STOP, GO, OWN = "stop", "go", "own gates"
# The opening words of a cell for each class. A cell must start with the words of exactly one class.
OPENERS = {
    STOP: re.compile(r"Stop(?! that)\b|Ask\b|Wait for\b|Pause\b|Approval prompt\b|A separate yes\b|The OK of the user\b"
                     r"|Only (?:with|after)\b|Never, unless\b|List it, and act only after the yes\b|List its contents, and ask\b"
                     r"|Propose (?:it|the path), and ask\b|Post it at\b"),
    GO: re.compile(r"No stop\b|No question\b|Continue\b|Report\b|Decide\b|Take\b|Use\b|Keep\b|Skip\b|Show\b|Update\b"
                   r"|Infer\b|Put\b|Announce\b|Add\b|State\b|Move\b|Name it\b|Find it\b|Post it now\b|Create the branch\b"
                   r"|Run one round with no stop\b|Approve the recommended\b|List them, and write\b|Do not delete\b"
                   r"|Delete only the paths that this run made\b|The meta-plan approves\b|Stop that cleanup\b"),
    OWN: re.compile(r"Its (?:own )?gates\b|See \""),
}
# A cell with one of these words takes the cell of the partial mode.
SAME = ("Same", "Same as partial")
RANK = {GO: 0, STOP: 1}
# Rows that break the order on purpose, with the classes of their partial, interactive, and full cells.
ORDER_EXCEPTIONS = {
    # The interactive mode stops at Human Approve #1 before this post. The partial mode posts after Human Approve #2.
    ("skills/feature-pipeline/SKILL.md", "Task Comment #1"): (STOP, GO, GO),
    # In the interactive mode, the reply of Phase 5 approves these writes.
    ("skills/promote-conventions/SKILL.md", "Phase 9a: the `stub` writes"): (STOP, GO, GO),
}


def gate_rows(rel):
    """The rows of the gate table of a unit, each as a tuple of its cells."""
    lines = autonomy(read(PLUGIN / rel)).splitlines()
    rows = []
    for line in lines[lines.index(HEADER) + 2:]:
        if not line.startswith("|"):
            break
        rows.append(tuple(cell.strip() for cell in line.strip().strip("|").split("|")))
    return rows


def classify(cell):
    found = [name for name, pattern in OPENERS.items() if pattern.match(cell)]
    if len(found) != 1:
        raise AssertionError(f"The cell {cell!r} starts with the words of {found or 'no class'}. "
                             "Start it with the words of one class in OPENERS, or add its words to one class.")
    return found[0]


def classes(row):
    """The classes of the partial, interactive, and full cells of a row."""
    gate, partial, interactive, full = row
    if partial in SAME:
        raise AssertionError(f"The partial cell of {gate!r} is {partial!r}, which names no action.")
    if full == "Same" and interactive != "Same":
        raise AssertionError(f"The full cell of {gate!r} is 'Same', and the interactive cell differs. Write 'Same as partial'.")
    return tuple(classify(partial if cell in SAME else cell) for cell in (partial, interactive, full))


class GateRowTests(unittest.TestCase):
    def test_no_mode_stops_where_a_mode_with_more_stops_goes_on(self):
        for rel in TABLE_UNITS:
            rows = gate_rows(rel)
            self.assertTrue(rows, f"{rel} has no gate rows below its header.")
            for row in rows:
                with self.subTest(unit=rel, gate=row[0]):
                    self.assertEqual(len(row), 4, f"The row needs a gate and three cells: {row}")
                    found = classes(row)
                    if (rel, row[0]) in ORDER_EXCEPTIONS:
                        self.assertEqual(found, ORDER_EXCEPTIONS[rel, row[0]])
                    elif OWN in found:
                        self.assertEqual(set(found), {OWN}, "A row that leaves its gates to another text does so in each mode.")
                    else:
                        partial, interactive, full = (RANK[name] for name in found)
                        self.assertGreaterEqual(interactive, partial, "The interactive mode goes on where the partial mode stops.")
                        self.assertGreaterEqual(partial, full, "The full mode stops where the partial mode goes on.")


if __name__ == "__main__":
    unittest.main()
