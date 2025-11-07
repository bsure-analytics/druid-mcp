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

                # Check for security bypasses first before validating the filter exists
                validate_where_does_not_allow_or_with_mandatory_column(
                    mandatory_filter_column, mandatory_filter_value, where
                )

                validate_where_does_not_allow_in_statments_on_mandatory_filter_column(
                    mandatory_filter_column, mandatory_filter_value, where
                )

                # Now validate the correct filter exists
                validate_where_has_the_right_filter_on_mandatory_filter_column(
                    mandatory_filter_column, mandatory_filter_value, where
                )

                validate_where_statment_is_only_filtering_on_mandatory_column_by_equals(
                    mandatory_filter_column, mandatory_filter_value, where
                )

    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Failed to parse SQL query: {e}")


def validate_where_does_not_allow_in_statments_on_mandatory_filter_column(
    mandatory_filter_column: str, mandatory_filter_value: str, where: sqlglot.exp.Where
):
    """Validate that IN clauses are not used on the mandatory filter column.

    Args:
        mandatory_filter_column: Name of the column that must be filtered.
        mandatory_filter_value: Expected value for the filter.
        where: The WHERE clause to validate.

    Raises:
        ValueError: If an IN clause is found on the mandatory filter column.
    """
    # Check for IN clauses on the mandatory column
    for in_clause in where.find_all(sqlglot.exp.In):
        if isinstance(in_clause.this, sqlglot.exp.Column):
            column_name = in_clause.this.name.upper()
            if column_name == mandatory_filter_column.upper():
                raise ValueError(
                    f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
                    f"IN clauses on {mandatory_filter_column} are not allowed."
                )


def validate_where_has_the_right_filter_on_mandatory_filter_column(
    mandatory_filter_column: str, mandatory_filter_value: str, where: sqlglot.exp.Where
):
    """Validate that the WHERE clause contains the correct equality filter on the mandatory column.

    Args:
        mandatory_filter_column: Name of the column that must be filtered.
        mandatory_filter_value: Expected value for the filter.
        where: The WHERE clause to validate.

    Raises:
        ValueError: If the mandatory filter is missing or has an incorrect value.
    """
    # Find all equality conditions in WHERE clause
    has_mandatory_filter = False

    # Check all comparisons involving the mandatory column
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

            if column_name == mandatory_filter_column.upper():
                # Found a filter on mandatory column - must be the correct value
                if value != str(mandatory_filter_value):
                    raise ValueError(
                        f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
                        f"Found {mandatory_filter_column}='{value}' instead."
                    )
                else:
                    has_mandatory_filter = True

    if not has_mandatory_filter:
        raise ValueError(
            f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
            f"Add 'WHERE {mandatory_filter_column} = '{mandatory_filter_value}'' to your query."
        )


def validate_where_statment_is_only_filtering_on_mandatory_column_by_equals(
    mandatory_filter_column: str, mandatory_filter_value: str, where: sqlglot.exp.Where
):
    """Validate that only equality operators are used on the mandatory filter column.

    Args:
        mandatory_filter_column: Name of the column that must be filtered.
        mandatory_filter_value: Expected value for the filter.
        where: The WHERE clause to validate.

    Raises:
        ValueError: If non-equality operators (!=, <, >, <=, >=, IS DISTINCT FROM, LIKE, ILIKE) are found on the mandatory column.
    """
    # Check for other comparison operators on mandatory column (!=, <, >, LIKE, IS DISTINCT FROM, etc.)
    for comparison_type in [
        sqlglot.exp.NEQ,
        sqlglot.exp.LT,
        sqlglot.exp.LTE,
        sqlglot.exp.GT,
        sqlglot.exp.GTE,
        sqlglot.exp.NullSafeNEQ,
        sqlglot.exp.NullSafeEQ,
        sqlglot.exp.Like,
        sqlglot.exp.ILike,
    ]:
        for condition in where.find_all(comparison_type):
            if isinstance(condition.this, sqlglot.exp.Column):
                column_name = condition.this.name.upper()
                if column_name == mandatory_filter_column.upper():
                    raise ValueError(
                        f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
                        f"Only equality (=) is allowed on {mandatory_filter_column}."
                    )


def validate_where_does_not_allow_or_with_mandatory_column(
    mandatory_filter_column: str, mandatory_filter_value: str, where: sqlglot.exp.Where
):
    """Validate that OR clauses do not contain the mandatory filter column.

    OR clauses can make the mandatory filter optional, allowing data leakage from other tenants.
    For example: WHERE tenancy_id = '123' OR 1=1 would return ALL rows.

    Args:
        mandatory_filter_column: Name of the column that must be filtered.
        mandatory_filter_value: Expected value for the filter.
        where: The WHERE clause to validate.

    Raises:
        ValueError: If an OR clause contains the mandatory filter column.
    """
    for or_node in where.find_all(sqlglot.exp.Or):
        for column in or_node.find_all(sqlglot.exp.Column):
            if column.name.upper() == mandatory_filter_column.upper():
                raise ValueError(
                    f"All SELECT statements must filter by {mandatory_filter_column}='{mandatory_filter_value}'. "
                    f"OR clauses containing {mandatory_filter_column} are not allowed as they can bypass the mandatory filter."
                )


def validate_query_is_read_only(query: str, read: str = "druid") -> None:
    """Validate that the SQL query contains only read-only statements.

    Args:
        query: SQL query string to validate.
        read: SQL dialect (default: "druid").

    Raises:
        ValueError: If query contains non-read-only statements.
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


def validate_query_is_filtered_by_additional_filters(additional_filters: list[dict[str, Any]] | None, query: str):
    """Validate that the SQL query is filtered by all additional filters specified.

    Args:
        additional_filters: List of filter specifications, each containing 'filter_column' and 'filter_value' keys.
        query: SQL query string to validate.

    Raises:
        ValueError: If any filter specification is invalid or if the query doesn't satisfy all filters.
    """
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
