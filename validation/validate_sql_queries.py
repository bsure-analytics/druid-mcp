from typing import Any

import sqlglot


def validate_query_is_filtered_by_mandatory_filter_column(
    query: str, mandatory_filter_column: str, mandatory_filter_value: str, read: str = "druid"
) -> None:
    """Validate that the SQL query filters by a mandatory column

    Args:
        query: SQL query string to validate
        mandatory_filter_column: Name of the column that must be filtered
        mandatory_filter_value: Expected value for the filter
        read: SQL dialect (default: "druid")

    Raises:
        ValueError: If query doesn't filter by the mandatory column with correct value
    """
    try:
        parsed = sqlglot.parse(query, read=read)

        for statement in parsed:
            if statement is None:
                continue

            # Find all SELECT statements (including nested ones in CTEs, subqueries, etc.)
            select_statements = list(statement.find_all(sqlglot.exp.Select))

            if not select_statements:
                continue

            for select in select_statements:
                # Extract WHERE clause for this SELECT
                where = select.find(sqlglot.exp.Where)
                if not where:
                    raise ValueError(
                        f"All SELECT statements must include WHERE clause filtering by "
                        f"{mandatory_filter_column}='{mandatory_filter_value}'"
                    )

                # Find all equality conditions in WHERE clause
                has_mandatory_filter = False

                for condition in where.find_all(sqlglot.exp.EQ):
                    left = condition.left
                    right = condition.right

                    # Determine which side is column and which is literal
                    column = None
                    literal = None

                    if isinstance(left, sqlglot.exp.Column) and isinstance(right, sqlglot.exp.Literal):
                        column = left
                        literal = right
                    elif isinstance(left, sqlglot.exp.Literal) and isinstance(right, sqlglot.exp.Column):
                        column = right
                        literal = left

                    if column and literal:
                        column_name = column.name.upper()
                        value = literal.this

                        if column_name == mandatory_filter_column.upper() and value == str(mandatory_filter_value):
                            has_mandatory_filter = True

                if not has_mandatory_filter:
                    raise ValueError(
                        f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
                        f"Add 'WHERE {mandatory_filter_column} = '{mandatory_filter_value}'' to your query."
                    )

    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Failed to parse SQL query: {e}")


def validate_query_is_read_only(query: str, read: str = "druid") -> None:
    """Validate that the SQL query contains only read-only statements

    Args:
        query: SQL query string to validate

    Raises:
        ValueError: If query contains non-read-only statements
    """
    # Allowed read-only statement types
    ALLOWED_STATEMENTS = (
        sqlglot.exp.Select,
        sqlglot.exp.Describe,
    )

    try:
        parsed = sqlglot.parse(query, read=read)

        for statement in parsed:
            if statement is None:
                continue

            if not isinstance(statement, ALLOWED_STATEMENTS):
                statement_type = statement.__class__.__name__
                raise ValueError(
                    f"Only SELECT queries are allowed. Found {statement_type} statement. "
                    f"This server provides read-only access to Druid."
                )
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Failed to parse SQL query: {e}")


# validate_query_filters("select channel_id, tenancy_id from sumup where 'JTI' = channel_id and 1=tenancy_id", "1", "JI")
def validate_query_is_filtered_by_additional_filters(additional_filters: list[dict[str, Any]] | None, query: str):
    if additional_filters:
        for filter_spec in additional_filters:
            if "filter_column" not in filter_spec:
                raise ValueError("Each additional filter must have 'filter_column' key")
            if "filter_value" not in filter_spec:
                raise ValueError("Each additional filter must have 'filter_value' key")

            filter_column = filter_spec["filter_column"]
            filter_value = str(filter_spec["filter_value"])

            # Validate that the query filters by this column with this value
            validate_query_is_filtered_by_mandatory_filter_column(query, filter_column, filter_value)
