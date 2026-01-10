#!/usr/bin/env python3
"""
Split a WSJTX ADI log file into separate files based on MY_GRIDSQUARE field.
Each output file is named <gridsquare>_wsjtx_log.adi and contains only QSOs
from that specific operating location.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def parse_adi_header(content: str) -> tuple[str, str]:
    """Extract header and records portion of ADI file."""
    # Find end of header marker (case insensitive)
    match = re.search(r'<EOH>', content, re.IGNORECASE)
    if match:
        header = content[:match.end()]
        records = content[match.end():]
        return header, records
    # No header found, entire file is records
    return "", content


def extract_records(records_text: str) -> list[str]:
    """Extract individual QSO records from the records portion."""
    # Split on <EOR> (case insensitive) and keep the delimiter
    parts = re.split(r'(<EOR>)', records_text, flags=re.IGNORECASE)

    records = []
    current = ""
    for part in parts:
        current += part
        if re.match(r'<EOR>', part, re.IGNORECASE):
            # Strip leading/trailing whitespace but preserve internal structure
            record = current.strip()
            if record:
                records.append(record)
            current = ""

    return records


def get_my_gridsquare(record: str) -> str | None:
    """Extract MY_GRIDSQUARE value from a record."""
    # Match <MY_GRIDSQUARE:N>VALUE where N is the length
    match = re.search(r'<MY_GRIDSQUARE:(\d+)>([^<\s]+)', record, re.IGNORECASE)
    if match:
        length = int(match.group(1))
        value = match.group(2)[:length]
        return value.upper()
    return None


def main():
    input_file = Path("wsjtx_log.adi")

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        sys.exit(1)

    # Read the input file
    content = input_file.read_text()

    # Parse header and records
    header, records_text = parse_adi_header(content)
    records = extract_records(records_text)

    print(f"Found {len(records)} QSO records")

    # Group records by MY_GRIDSQUARE
    gridsquare_records: dict[str, list[str]] = defaultdict(list)
    no_gridsquare = []

    for record in records:
        grid = get_my_gridsquare(record)
        if grid:
            gridsquare_records[grid].append(record)
        else:
            no_gridsquare.append(record)

    if no_gridsquare:
        print(f"Warning: {len(no_gridsquare)} records have no MY_GRIDSQUARE field")

    # Write output files
    for grid, grid_records in sorted(gridsquare_records.items()):
        output_file = Path(f"{grid}_wsjtx_log.adi")

        with open(output_file, 'w') as f:
            # Write header
            if header:
                f.write(header)
                f.write("\n\n")

            # Write records
            for record in grid_records:
                f.write(record)
                f.write("\n")

        print(f"Wrote {len(grid_records)} records to {output_file}")

    print(f"\nCreated {len(gridsquare_records)} output files for gridsquares: {', '.join(sorted(gridsquare_records.keys()))}")


if __name__ == "__main__":
    main()
