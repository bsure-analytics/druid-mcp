import pytest

from validation.validate_sql_queries import validate_query_is_filtered_by_mandatory_filter_column


class TestFilterValidation:
    """Test that queries are properly filtered by a mandatory column"""

    def test_simple_query_with_correct_filter(self):
        """Query with correct mandatory filter should be accepted"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123'"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_with_additional_column(self):
        """Query with mandatory filter and additional column should be accepted"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_with_literal_first(self):
        """Query with literal = column pattern should be accepted"""
        query = "SELECT * FROM sumup WHERE '123' = tenancy_id"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_with_additional_filters(self):
        """Query with additional filters beyond mandatory column should be accepted"""
        query = """
        SELECT * FROM sumup
        WHERE tenancy_id = '123'
        AND status = 'active'
        AND amount > 100
        """
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_with_cte_all_filtered(self):
        """Query with CTE where all SELECT statements have correct filter should be accepted"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE tenancy_id = '123'
        )
        SELECT * FROM temp WHERE tenancy_id = '123'
        """
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_missing_filter_rejected(self):
        """Query missing mandatory filter should be rejected"""
        query = "SELECT * FROM sumup WHERE channel_id = 'ABC'"
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_with_wrong_value_rejected(self):
        """Query with wrong filter value should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '456'"
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_query_without_where_clause_rejected(self):
        """Query without WHERE clause should be rejected"""
        query = "SELECT * FROM sumup"
        with pytest.raises(ValueError, match=r"must include WHERE clause"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_multiple_selects_all_must_have_filter(self):
        """All SELECT statements must have correct filter"""
        query = """
        SELECT * FROM sumup WHERE tenancy_id = '123';
        SELECT * FROM sumup WHERE tenancy_id = '123'
        """
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_multiple_selects_one_missing_filter_rejected(self):
        """If one SELECT is missing filter, query should be rejected"""
        query = """
        SELECT * FROM sumup WHERE tenancy_id = '123';
        SELECT * FROM sumup WHERE channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_nested_subquery_all_filtered(self):
        """Nested subqueries where all have filter should be accepted"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE tenancy_id = '123'
        ) WHERE tenancy_id = '123'
        """
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_nested_subquery_one_missing_filter_rejected(self):
        """Nested subqueries where one is missing filter should be rejected"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE status = 'active'
        ) WHERE tenancy_id = '123'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_numeric_id(self):
        """Query with numeric ID should work"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '456'"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "456")

    def test_case_insensitive_column_names(self):
        """Column names should be case insensitive"""
        query = "SELECT * FROM sumup WHERE TENANCY_ID = '123'"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_different_column_name(self):
        """Should work with different mandatory column names"""
        query = "SELECT * FROM users WHERE customer_id = 'CUST123'"
        validate_query_is_filtered_by_mandatory_filter_column(query, "customer_id", "CUST123")

    def test_complex_query_with_joins_and_ctes(self):
        """Complex query with multiple CTEs and joins should be validated"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE tenancy_id = '123' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.tenancy_id = '123'
        """
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_complex_query_with_cte_missing_filter_rejected(self):
        """Complex query where one CTE is missing filter should be rejected"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE status = 'active'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE tenancy_id = '123'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.tenancy_id = '123'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_complex_query_with_main_select_missing_filter_rejected(self):
        """Complex query where CTEs have filter but main SELECT is missing it should be rejected"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE tenancy_id = '123' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_complex_query_with_second_cte_missing_filter_rejected(self):
        """Complex query where first CTE has filter but second CTE is missing it should be rejected"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE channel_id = 'ABC' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.tenancy_id = '123'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_condition_with_mandatory_column_rejected(self):
        """Query with OR condition where mandatory column has different value should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' OR tenancy_id = '456'"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_condition_with_other_columns_allowed(self):
        """Query with OR between other columns (not mandatory column) should be allowed"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND (channel_id = 'ABC' OR status = 'active')"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_in_clause_with_multiple_values_rejected(self):
        """Query with IN clause containing mandatory value and others should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id IN ('123', '456')"
        with pytest.raises(ValueError, match=r"IN clauses on tenancy_id are not allowed"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_not_equals_mandatory_column_rejected(self):
        """Query with != on mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id != '456' AND tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"Only equality \(=\) is allowed on tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_tenancy_id_in_list_of_not_allowed_ids(self):
        """Query with IN clause in OR condition should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' OR tenancy_id IN ('123', '456')"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_with_always_true_condition_rejected(self):
        """Query with OR and always-true condition should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' OR 1=1"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_with_other_filter_on_mandatory_column_rejected(self):
        """Query with OR on other condition with mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' OR amount > 0"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_or_in_parentheses_with_mandatory_column_rejected(self):
        """Query with OR in parentheses containing mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE (tenancy_id = '123' OR status = 'active')"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_is_null_with_or_rejected(self):
        """Query with IS NULL in OR clause should be rejected (caught by OR validator)"""
        query = "SELECT * FROM sumup WHERE tenancy_id IS NULL OR tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"OR.*tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_is_null_on_other_column_allowed(self):
        """Query with IS NULL on non-mandatory column should be allowed"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND status IS NULL"
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_case_without_mandatory_column_allowed(self):
        """Query with CASE expression not referencing mandatory column should be allowed"""
        query = """SELECT * FROM sumup WHERE tenancy_id = '123' AND
                   CASE WHEN status = 'active' THEN 1 ELSE 0 END = 1"""
        validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_is_distinct_from_rejected(self):
        """Query with IS DISTINCT FROM on mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id IS DISTINCT FROM '456' AND tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"Only equality \(=\) is allowed on tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_like_operator_rejected(self):
        """Query with LIKE on mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id LIKE '12%' AND tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"Only equality \(=\) is allowed on tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")

    def test_ilike_operator_rejected(self):
        """Query with ILIKE on mandatory column should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id ILIKE '12%' AND tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"Only equality \(=\) is allowed on tenancy_id"):
            validate_query_is_filtered_by_mandatory_filter_column(query, "tenancy_id", "123")
