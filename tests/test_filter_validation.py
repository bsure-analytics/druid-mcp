import pytest

from validation.validate_sql_queries import validate_query_is_filtered_by_tenancy_and_channel


class TestFilterValidation:
    """Test that queries are properly filtered by tenancy_id and channel_id"""

    def test_simple_query_with_correct_filters(self):
        """Query with correct tenancy_id and channel_id filters should be accepted"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_reversed_filter_order(self):
        """Query with filters in reversed order should be accepted"""
        query = "SELECT * FROM sumup WHERE channel_id = 'ABC' AND tenancy_id = '123'"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_literal_first(self):
        """Query with literal = column pattern should be accepted"""
        query = "SELECT * FROM sumup WHERE '123' = tenancy_id AND 'ABC' = channel_id"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_mixed_patterns(self):
        """Query with mixed column = literal and literal = column patterns should be accepted"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND 'ABC' = channel_id"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_additional_filters(self):
        """Query with additional filters beyond tenancy_id and channel_id should be accepted"""
        query = """
        SELECT * FROM sumup
        WHERE tenancy_id = '123'
        AND channel_id = 'ABC'
        AND status = 'active'
        AND amount > 100
        """
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_cte_all_filtered(self):
        """Query with CTE where all SELECT statements have correct filters should be accepted"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'
        )
        SELECT * FROM temp WHERE tenancy_id = '123' AND channel_id = 'ABC'
        """
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_missing_tenancy_id_rejected(self):
        """Query missing tenancy_id filter should be rejected"""
        query = "SELECT * FROM sumup WHERE channel_id = 'ABC'"
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_missing_channel_id_rejected(self):
        """Query missing channel_id filter should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123'"
        with pytest.raises(ValueError, match=r"must filter by channel_id='ABC'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_wrong_tenancy_id_rejected(self):
        """Query with wrong tenancy_id value should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '456' AND channel_id = 'ABC'"
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_with_wrong_channel_id_rejected(self):
        """Query with wrong channel_id value should be rejected"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'XYZ'"
        with pytest.raises(ValueError, match=r"must filter by channel_id='ABC'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_query_without_where_clause_rejected(self):
        """Query without WHERE clause should be rejected"""
        query = "SELECT * FROM sumup"
        with pytest.raises(ValueError, match=r"must include WHERE clause"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_multiple_selects_all_must_have_filters(self):
        """All SELECT statements must have correct filters"""
        query = """
        SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC';
        SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'
        """
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_multiple_selects_one_missing_filter_rejected(self):
        """If one SELECT is missing filters, query should be rejected"""
        query = """
        SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC';
        SELECT * FROM sumup WHERE tenancy_id = '123'
        """
        with pytest.raises(ValueError, match=r"must filter by channel_id='ABC'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_nested_subquery_all_filtered(self):
        """Nested subqueries where all have filters should be accepted"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'
        ) WHERE tenancy_id = '123' AND channel_id = 'ABC'
        """
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_nested_subquery_one_missing_filter_rejected(self):
        """Nested subqueries where one is missing filters should be rejected"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE tenancy_id = '123'
        ) WHERE tenancy_id = '123' AND channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by channel_id='ABC'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_numeric_ids(self):
        """Query with numeric IDs should work"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = '456'"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "456")

    def test_case_insensitive_column_names(self):
        """Column names should be case insensitive"""
        query = "SELECT * FROM sumup WHERE TENANCY_ID = '123' AND CHANNEL_ID = 'ABC'"
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_complex_query_with_joins_and_ctes(self):
        """Complex query with multiple CTEs and joins should be validated"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123' AND channel_id = 'ABC'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE tenancy_id = '123' AND channel_id = 'ABC' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.tenancy_id = '123' AND s.channel_id = 'ABC'
        """
        validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_complex_query_with_cte_missing_filter_rejected(self):
        """Complex query where one CTE is missing channel_id filter should be rejected"""
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
            WHERE tenancy_id = '123' AND channel_id = 'ABC' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.tenancy_id = '123' AND s.channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by channel_id='ABC'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_complex_query_with_main_select_missing_filter_rejected(self):
        """Complex query where CTEs have filters but main SELECT is missing tenancy_id should be rejected"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123' AND channel_id = 'ABC'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT *
            FROM sumup
            WHERE tenancy_id = '123' AND channel_id = 'ABC' AND status = 'active'
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        WHERE s.channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")

    def test_complex_query_with_second_cte_missing_filter_rejected(self):
        """Complex query where first CTE has filters but second CTE is missing tenancy_id should be rejected"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '123' AND channel_id = 'ABC'
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
        WHERE s.tenancy_id = '123' AND s.channel_id = 'ABC'
        """
        with pytest.raises(ValueError, match=r"must filter by tenancy_id='123'"):
            validate_query_is_filtered_by_tenancy_and_channel(query, "123", "ABC")
