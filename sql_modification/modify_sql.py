from typing import Any

import sqlglot


def add_filters_to_query(
    query: str,
    mandatory_filter_column: str,
    mandatory_filter_value: str,
    read_dialect: str = "druid",
    write_dialect: str = "druid",
) -> str:
    """Add mandatory filter to all SELECT statements in a SQL query

    Args:
        query: SQL query string to modify
        mandatory_filter_column: Column name to filter by
        mandatory_filter_value: Value to filter by
        read_dialect: SQL dialect for parsing (default: "druid")
        write_dialect: SQL dialect for output (default: "druid")

    Returns:
        Modified SQL query with filter added to all SELECT statements

    Raises:
        ValueError: If query cannot be parsed
    """
    try:
        parsed = sqlglot.parse(query, read=read_dialect)

        for statement in parsed:
            if statement is None:
                continue

            # Find all SELECT statements (including nested ones in CTEs, subqueries, etc.)
            select_statements = list(statement.find_all(sqlglot.exp.Select))

            for select in select_statements:
                where = select.find(sqlglot.exp.Where)

                # Collect all non-mandatory-filter conditions to preserve
                preserved_conditions = []

                if where:
                    # Helper function to check if a condition is the mandatory filter
                    def is_mandatory_filter(condition):
                        if not isinstance(condition, sqlglot.exp.EQ):
                            return False

                        left = condition.left
                        right = condition.right

                        # Determine which side is column
                        column = None
                        if isinstance(left, sqlglot.exp.Column):
                            column = left
                        elif isinstance(right, sqlglot.exp.Column):
                            column = right

                        if column:
                            column_name = column.name.upper()
                            return column_name == mandatory_filter_column.upper()
                        return False

                    # Walk through WHERE clause and collect non-mandatory-filter conditions
                    def collect_conditions(node, conditions_list):
                        if isinstance(node, sqlglot.exp.And):
                            # Recursively process both sides
                            collect_conditions(node.left, conditions_list)
                            collect_conditions(node.right, conditions_list)
                        elif not is_mandatory_filter(node):
                            # Keep this condition
                            conditions_list.append(node)

                    collect_conditions(where.this, preserved_conditions)

                # Build new WHERE clause with preserved conditions + correct filter
                mandatory_filter = sqlglot.condition(
                    f"{mandatory_filter_column} = '{mandatory_filter_value}'", dialect=write_dialect
                )

                # Combine all conditions
                all_conditions = preserved_conditions + [mandatory_filter]

                if all_conditions:
                    combined = all_conditions[0]
                    for condition in all_conditions[1:]:
                        combined = sqlglot.and_(combined, condition)
                    select.set("where", sqlglot.exp.Where(this=combined))

        # Convert back to SQL string
        return parsed[0].sql(dialect=write_dialect, pretty=True)

    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Failed to parse SQL query: {e}")


def add_additional_filters_to_query(additional_filters: list[dict[str, Any]] | None, new_query: str) -> str:
    if additional_filters:
        for filter_spec in additional_filters:
            if "filter_column" not in filter_spec:
                raise ValueError("Each additional filter must have 'filter_column' key")
            if "filter_value" not in filter_spec:
                raise ValueError("Each additional filter must have 'filter_value' key")

            filter_column = filter_spec["filter_column"]
            filter_value = str(filter_spec["filter_value"])

            # Validate that the query filters by this column with this value
            new_query = add_filters_to_query(new_query, filter_column, filter_value)
    return new_query
