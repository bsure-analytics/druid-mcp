import csv
import io
from typing import Any


def json_table_to_csv(
    data: list[dict[str, Any]],
) -> str:
    """Convert JSON table data to CSV format for better LLM readability.

    This function handles various JSON formats and converts them to clean CSV strings
    that are easier for LLMs to parse and understand.

    Args:
        data: JSON data in one of the following formats:
            - JSON string containing array of objects
            - List of dictionaries (rows)
            - Dictionary with 'rows' or 'data' key containing list
        max_rows: Optional limit on number of rows to include (useful for large datasets)
        exclude_null_columns: If True, exclude columns where all values are None/null

    Returns:
        CSV-formatted string with proper escaping and quoting

    Examples:
        >>> data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        >>> print(json_table_to_csv(data))
        name,age
        Alice,30
        Bob,25

        >>> data = [{"id": 1, "value": "test", "empty": None}]
        >>> print(json_table_to_csv(data, exclude_null_columns=True))
        id,value
        1,test
    """
    if isinstance(data, str):
        return data
    columns = list(data[0].keys())
    # Write to CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")

    writer.writeheader()
    writer.writerows(data)

    csv_content = output.getvalue()

    return csv_content
