from sql_modification.modify_sql import add_filters_to_query
from validation.validate_sql_queries import validate_query_is_filtered_by_mandatory_filter_column


class TestAddingFiltersToQuery:
    """Test that filters are properly added/replaced in SQL queries"""

    def test_add_filter_to_query_without_where(self):
        """Query without WHERE clause should get filter added"""
        query = "SELECT * FROM sumup"
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify filter is present in output
        assert "tenancy_id = '123'" in result

    def test_add_filter_to_query_with_existing_conditions(self):
        """Query with WHERE clause but no mandatory filter should get filter added"""
        query = "SELECT * FROM sumup WHERE status = 'active' AND amount > 100"
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify original conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result

        # Verify new filter is added
        assert "tenancy_id = '123'" in result

    def test_replace_wrong_filter_value(self):
        """Query with wrong filter value should get it replaced"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '999'"
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify wrong value is replaced
        assert "tenancy_id = '999'" not in result
        assert "tenancy_id = '123'" in result

    def test_keep_correct_filter_unchanged(self):
        """Query with correct filter should keep it"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123'"
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify correct filter is present
        assert "tenancy_id = '123'" in result

    def test_replace_filter_preserve_other_conditions(self):
        """Query with wrong filter and other conditions should preserve other conditions"""
        query = """
        SELECT * FROM sumup
        WHERE tenancy_id = '999'
        AND status = 'active'
        AND amount > 100
        AND created_at > '2024-01-01'
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify other conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result
        assert "created_at > '2024-01-01'" in result

        # Verify filter is correct
        assert "tenancy_id = '999'" not in result
        assert "tenancy_id = '123'" in result

    def test_cte_with_missing_filter(self):
        """Query with CTE missing filter should get filter added to all SELECT statements"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE status = 'active'
        )
        SELECT * FROM temp WHERE amount > 100
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

    def test_cte_with_wrong_filter(self):
        """Query with CTE having wrong filter should get it replaced in all SELECT statements"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE tenancy_id = '999'
        )
        SELECT * FROM temp WHERE tenancy_id = '999'
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify wrong value is not present
        assert "tenancy_id = '999'" not in result

    def test_subquery_with_missing_filter(self):
        """Query with subquery missing filter should get filter added"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE status = 'active'
        ) AS t
        WHERE amount > 100
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

    def test_subquery_with_wrong_filter(self):
        """Query with subquery having wrong filter should get it replaced"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE tenancy_id = '999'
        ) AS t
        WHERE tenancy_id = '999'
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify wrong value is not present
        assert "tenancy_id = '999'" not in result

    def test_join_with_missing_filter(self):
        """Query with JOIN missing filter should get filter added"""
        query = """
        SELECT a.*, b.status
        FROM sumup a
        JOIN channels b ON a.channel_id = b.id
        WHERE a.amount > 100
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify original condition is preserved
        assert "amount > 100" in result

    def test_complex_cte_with_mixed_filters(self):
        """Complex query with multiple CTEs having mixed correct/wrong/missing filters"""
        query = """
        WITH stats AS (
            SELECT tenancy_id, channel_id, COUNT(*) as cnt
            FROM sumup
            WHERE tenancy_id = '999' AND status = 'active'
            GROUP BY tenancy_id, channel_id
        ),
        filtered AS (
            SELECT * FROM sumup
            WHERE amount > 100
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        """
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify other conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result

        # Verify wrong value is not present
        assert "tenancy_id = '999'" not in result

    def test_numeric_id(self):
        """Query with numeric ID should work correctly"""
        query = "SELECT * FROM sumup WHERE status = 'active'"
        result = add_filters_to_query(query, "tenancy_id", "456")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "456")

        # Verify filter is present
        assert "tenancy_id = '456'" in result

    def test_alphanumeric_id(self):
        """Query with alphanumeric ID should work correctly"""
        query = "SELECT * FROM sumup"
        result = add_filters_to_query(query, "tenancy_id", "tenant-123-abc")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "tenant-123-abc")

        # Verify filter is present
        assert "tenancy_id = 'tenant-123-abc'" in result

    def test_different_column_name(self):
        """Should work with different column names"""
        query = "SELECT * FROM users WHERE status = 'active'"
        result = add_filters_to_query(query, "customer_id", "CUST123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "customer_id", "CUST123")

        # Verify filter is present
        assert "customer_id = 'CUST123'" in result

    def test_preserve_other_filters(self):
        """Query with filter on different column should preserve it"""
        query = "SELECT * FROM sumup WHERE channel_id = 'ABC' AND status = 'active'"
        result = add_filters_to_query(query, "tenancy_id", "123")

        # Verify the result passes validation
        validate_query_is_filtered_by_mandatory_filter_column(result, "tenancy_id", "123")

        # Verify tenancy_id is added
        assert "tenancy_id = '123'" in result

        # Verify other filters are preserved
        assert "channel_id = 'ABC'" in result
        assert "status = 'active'" in result
