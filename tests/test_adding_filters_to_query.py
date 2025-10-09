from sql_modification.modify_sql import add_filters_to_query
from validation.validate_sql_queries import validate_query_is_filtered_by_tenancy_and_channel


class TestAddingFiltersToQuery:
    """Test that filters are properly added/replaced in SQL queries"""

    def test_add_filters_to_query_without_where(self):
        """Query without WHERE clause should get filters added"""
        query = "SELECT * FROM sumup"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify filters are present in output
        assert "tenancy_id = '123'" in result
        assert "channel_id = 'ABC'" in result

    def test_add_filters_to_query_with_existing_conditions(self):
        """Query with WHERE clause but no tenancy/channel filters should get filters added"""
        query = "SELECT * FROM sumup WHERE status = 'active' AND amount > 100"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify original conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result

        # Verify new filters are added
        assert "tenancy_id = '123'" in result
        assert "channel_id = 'ABC'" in result

    def test_replace_wrong_tenancy_id(self):
        """Query with wrong tenancy_id should get it replaced"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '999' AND channel_id = 'ABC'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong tenancy_id is replaced
        assert "tenancy_id = '999'" not in result
        assert "tenancy_id = '123'" in result

    def test_replace_wrong_channel_id(self):
        """Query with wrong channel_id should get it replaced"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'XYZ'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong channel_id is replaced
        assert "channel_id = 'XYZ'" not in result
        assert "channel_id = 'ABC'" in result

    def test_replace_both_wrong_filters(self):
        """Query with both wrong filters should get them replaced"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '999' AND channel_id = 'XYZ'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong filters are replaced
        assert "tenancy_id = '999'" not in result
        assert "channel_id = 'XYZ'" not in result
        assert "tenancy_id = '123'" in result
        assert "channel_id = 'ABC'" in result

    def test_keep_correct_filters_unchanged(self):
        """Query with correct filters should keep them"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND channel_id = 'ABC'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify correct filters are present
        assert "tenancy_id = '123'" in result
        assert "channel_id = 'ABC'" in result

    def test_replace_reversed_pattern_wrong_values(self):
        """Query with reversed pattern ('value' = column) and wrong values should get replaced"""
        query = "SELECT * FROM sumup WHERE '999' = tenancy_id AND 'XYZ' = channel_id"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong values are not present
        assert "'999'" not in result
        assert "'XYZ'" not in result

    def test_replace_filters_preserve_other_conditions(self):
        """Query with wrong filters and other conditions should preserve other conditions"""
        query = """
        SELECT * FROM sumup
        WHERE tenancy_id = '999'
        AND channel_id = 'XYZ'
        AND status = 'active'
        AND amount > 100
        AND created_at > '2024-01-01'
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify other conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result
        assert "created_at > '2024-01-01'" in result

        # Verify filters are correct
        assert "tenancy_id = '999'" not in result
        assert "channel_id = 'XYZ'" not in result
        assert "tenancy_id = '123'" in result
        assert "channel_id = 'ABC'" in result

    def test_cte_with_missing_filters(self):
        """Query with CTE missing filters should get filters added to all SELECT statements"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE status = 'active'
        )
        SELECT * FROM temp WHERE amount > 100
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

    def test_cte_with_wrong_filters(self):
        """Query with CTE having wrong filters should get them replaced in all SELECT statements"""
        query = """
        WITH temp AS (
            SELECT * FROM sumup WHERE tenancy_id = '999' AND channel_id = 'XYZ'
        )
        SELECT * FROM temp WHERE tenancy_id = '999' AND channel_id = 'XYZ'
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong values are not present
        assert "tenancy_id = '999'" not in result
        assert "channel_id = 'XYZ'" not in result

    def test_subquery_with_missing_filters(self):
        """Query with subquery missing filters should get filters added"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE status = 'active'
        ) AS t
        WHERE amount > 100
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

    def test_subquery_with_wrong_filters(self):
        """Query with subquery having wrong filters should get them replaced"""
        query = """
        SELECT * FROM (
            SELECT * FROM sumup WHERE tenancy_id = '999' AND channel_id = 'XYZ'
        ) AS t
        WHERE tenancy_id = '999' AND channel_id = 'XYZ'
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify wrong values are not present
        assert "tenancy_id = '999'" not in result
        assert "channel_id = 'XYZ'" not in result

    def test_join_with_missing_filters(self):
        """Query with JOIN missing filters should get filters added"""
        query = """
        SELECT a.*, b.status
        FROM sumup a
        JOIN channels b ON a.channel_id = b.id
        WHERE a.amount > 100
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

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
            WHERE channel_id = 'XYZ' AND amount > 100
        )
        SELECT s.*, f.status
        FROM stats s
        JOIN filtered f ON s.tenancy_id = f.tenancy_id
        """
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify other conditions are preserved
        assert "status = 'active'" in result
        assert "amount > 100" in result

        # Verify wrong values are not present
        assert "tenancy_id = '999'" not in result
        assert "channel_id = 'XYZ'" not in result

    def test_numeric_ids(self):
        """Query with numeric IDs should work correctly"""
        query = "SELECT * FROM sumup WHERE status = 'active'"
        result = add_filters_to_query(query, "456", "789")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "456", "789")

        # Verify filters are present
        assert "tenancy_id = '456'" in result
        assert "channel_id = '789'" in result

    def test_alphanumeric_ids(self):
        """Query with alphanumeric IDs should work correctly"""
        query = "SELECT * FROM sumup"
        result = add_filters_to_query(query, "tenant-123-abc", "channel-xyz-456")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "tenant-123-abc", "channel-xyz-456")

        # Verify filters are present
        assert "tenancy_id = 'tenant-123-abc'" in result
        assert "channel_id = 'channel-xyz-456'" in result

    def test_partial_filters_missing_tenancy(self):
        """Query with only channel_id filter should get tenancy_id added"""
        query = "SELECT * FROM sumup WHERE channel_id = 'ABC' AND status = 'active'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify tenancy_id is added
        assert "tenancy_id = '123'" in result

        # Verify channel_id and other conditions are preserved
        assert "channel_id = 'ABC'" in result
        assert "status = 'active'" in result

    def test_partial_filters_missing_channel(self):
        """Query with only tenancy_id filter should get channel_id added"""
        query = "SELECT * FROM sumup WHERE tenancy_id = '123' AND status = 'active'"
        result = add_filters_to_query(query, "123", "ABC")

        # Verify the result passes validation
        validate_query_is_filtered_by_tenancy_and_channel(result, "123", "ABC")

        # Verify channel_id is added
        assert "channel_id = 'ABC'" in result

        # Verify tenancy_id and other conditions are preserved
        assert "tenancy_id = '123'" in result
        assert "status = 'active'" in result
