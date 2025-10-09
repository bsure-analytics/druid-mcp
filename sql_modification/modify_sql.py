import sqlglot


def add_filters_to_query(
    query: str, tenancy_id: str, channel_id: str, read_dialect: str = "druid", write_dialect: str = "druid"
) -> str:
    """Add tenancy_id and channel_id filters to all SELECT statements in a SQL query

    Args:
        query: SQL query string to modify
        tenancy_id: Tenant identifier value to filter by
        channel_id: Channel identifier value to filter by
        read_dialect: SQL dialect for parsing (default: "druid")
        write_dialect: SQL dialect for output (default: "druid")

    Returns:
        Modified SQL query with filters added to all SELECT statements

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

                # Collect all non-tenancy/channel conditions to preserve
                preserved_conditions = []

                if where:
                    # Helper function to check if a condition is a tenancy_id or channel_id filter
                    def is_tenancy_or_channel_filter(condition):
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
                            return column_name in ("TENANCY_ID", "CHANNEL_ID")
                        return False

                    # Walk through WHERE clause and collect non-tenancy/channel conditions
                    def collect_conditions(node, conditions_list):
                        if isinstance(node, sqlglot.exp.And):
                            # Recursively process both sides
                            collect_conditions(node.left, conditions_list)
                            collect_conditions(node.right, conditions_list)
                        elif not is_tenancy_or_channel_filter(node):
                            # Keep this condition
                            conditions_list.append(node)

                    collect_conditions(where.this, preserved_conditions)

                # Build new WHERE clause with preserved conditions + correct filters
                tenancy_filter = sqlglot.condition(f"tenancy_id = '{tenancy_id}'", dialect=write_dialect)
                channel_filter = sqlglot.condition(f"channel_id = '{channel_id}'", dialect=write_dialect)

                # Combine all conditions
                all_conditions = preserved_conditions + [tenancy_filter, channel_filter]

                if all_conditions:
                    combined = all_conditions[0]
                    for condition in all_conditions[1:]:
                        combined = sqlglot.and_(combined, condition)
                    select.set("where", sqlglot.exp.Where(this=combined))

        # Convert back to SQL string
        return parsed[0].sql(dialect=write_dialect, pretty=True)

    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Failed to parse SQL query: {e}")


query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE status = 'active'
        )
        SELECT * FROM temp WHERE amount > 100
        """
print(add_filters_to_query(query=query, tenancy_id=1, channel_id=1, read_dialect="druid"))
