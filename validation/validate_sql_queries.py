import sqlglot


def validate_query_is_filtered_by_tenancy_and_channel(
    query: str, tenancy_id: str, channel_id: str, read: str = "druid"
) -> None:
    """Validate that the SQL query filters by tenancy_id and channel_id

    Args:
        query: SQL query string to validate
        tenancy_id: Expected tenant identifier value
        channel_id: Expected channel identifier value
        read: SQL dialect (default: "druid")

    Raises:
        ValueError: If query doesn't filter by both tenancy_id and channel_id with correct values
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
                        f"tenancy_id='{tenancy_id}' and channel_id='{channel_id}'"
                    )

                # Find all equality conditions in WHERE clause
                has_tenancy_filter = False
                has_channel_filter = False

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

                        if column_name == "TENANCY_ID" and value == str(tenancy_id):
                            has_tenancy_filter = True
                        elif column_name == "CHANNEL_ID" and value == str(channel_id):
                            has_channel_filter = True

                if not has_tenancy_filter:
                    raise ValueError(
                        f"All SELECT statements must filter by tenancy_id='{tenancy_id}'. "
                        f"Add 'WHERE tenancy_id = '{tenancy_id}'' to your query."
                    )

                if not has_channel_filter:
                    raise ValueError(
                        f"All SELECT statements must filter by channel_id='{channel_id}'. "
                        f"Add 'AND channel_id = '{channel_id}'' to your query."
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
