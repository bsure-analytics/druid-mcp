import pytest

from validation.validate_sql_queries import validate_query_is_read_only


class TestQueryValidation:
    """Test that only SELECT queries are allowed"""

    def test_select_query_is_allowed(self):
        """SELECT queries should be accepted"""
        query = "SELECT * FROM wikipedia"
        validate_query_is_read_only(query)

    def test_select_with_cte_is_allowed(self):
        """SELECT queries with CTEs should be accepted"""
        query = """
        WITH temp AS (
            SELECT channel, COUNT(*) as cnt
            FROM wikipedia
            GROUP BY channel
        )
        SELECT * FROM temp
        """
        validate_query_is_read_only(query)

    def test_multiple_select_queries_allowed(self):
        """Multiple SELECT queries should be accepted"""
        query = "SELECT * FROM wikipedia; SELECT COUNT(*) FROM wikipedia"
        validate_query_is_read_only(query)

    def test_describe_query_is_allowed(self):
        """DESCRIBE queries should be accepted"""
        query = "DESCRIBE wikipedia"
        validate_query_is_read_only(query)

    def test_insert_query_rejected(self):
        """INSERT queries should be rejected"""
        query = "INSERT INTO wikipedia (channel, user) VALUES ('test', 'user')"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Insert"):
            validate_query_is_read_only(query)

    def test_update_query_rejected(self):
        """UPDATE queries should be rejected"""
        query = "UPDATE wikipedia SET channel = 'new' WHERE user = 'test'"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Update"):
            validate_query_is_read_only(query)

    def test_complex_update_with_cte_and_join_rejected(self):
        """Complex UPDATE with CTEs and JOINs should be rejected"""
        query = """
        WITH channel_stats AS (
            SELECT channel, AVG(delta) as avg_delta
            FROM wikipedia
            GROUP BY channel
        ),
        target_channels AS (
            SELECT DISTINCT channel
            FROM wikipedia
            WHERE countryName = 'United States'
        )
        UPDATE wikipedia w
        SET delta = cs.avg_delta
        FROM channel_stats cs
        JOIN target_channels tc ON cs.channel = tc.channel
        WHERE w.channel = cs.channel
        AND w.delta IS NULL
        """
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Update"):
            validate_query_is_read_only(query)

    def test_delete_query_rejected(self):
        """DELETE queries should be rejected"""
        query = "DELETE FROM wikipedia WHERE channel = 'test'"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Delete"):
            validate_query_is_read_only(query)

    def test_complex_delete_with_subquery_rejected(self):
        """Complex DELETE with subqueries and JOINs should be rejected"""
        query = """
        DELETE FROM wikipedia
        WHERE channel IN (
            SELECT w1.channel
            FROM wikipedia w1
            JOIN (
                SELECT channel, COUNT(*) as cnt
                FROM wikipedia
                WHERE isRobot = true
                GROUP BY channel
                HAVING COUNT(*) > 100
            ) bot_channels ON w1.channel = bot_channels.channel
            WHERE w1.delta < 0
        )
        AND __time < TIMESTAMP '2016-06-27 00:00:00'
        """
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Delete"):
            validate_query_is_read_only(query)

    def test_drop_query_rejected(self):
        """DROP queries should be rejected"""
        query = "DROP TABLE wikipedia"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Drop"):
            validate_query_is_read_only(query)

    def test_drop_with_cascade_rejected(self):
        """DROP TABLE with CASCADE should be rejected"""
        query = "DROP TABLE IF EXISTS wikipedia CASCADE"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Drop"):
            validate_query_is_read_only(query)

    def test_drop_view_rejected(self):
        """DROP VIEW should be rejected"""
        query = "DROP VIEW IF EXISTS wikipedia_view"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Drop"):
            validate_query_is_read_only(query)

    def test_create_table_query_rejected(self):
        """CREATE TABLE queries should be rejected"""
        query = "CREATE TABLE test (id INT, name VARCHAR(100))"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Create"):
            validate_query_is_read_only(query)

    def test_alter_query_rejected(self):
        """ALTER queries should be rejected"""
        query = "ALTER TABLE wikipedia ADD COLUMN new_col VARCHAR(100)"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Alter"):
            validate_query_is_read_only(query)

    def test_truncate_query_rejected(self):
        """TRUNCATE queries should be rejected"""
        query = "TRUNCATE TABLE wikipedia"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Truncate"):
            validate_query_is_read_only(query)

    def test_merge_query_rejected(self):
        """MERGE queries should be rejected"""
        query = """
        MERGE INTO wikipedia t
        USING (SELECT 'test' as channel) s
        ON t.channel = s.channel
        WHEN MATCHED THEN UPDATE SET user = 'updated'
        """
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Merge"):
            validate_query_is_read_only(query)

    def test_insert_with_select_rejected(self):
        """INSERT with SELECT should be rejected"""
        query = "INSERT INTO wikipedia SELECT * FROM other_table"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Insert"):
            validate_query_is_read_only(query)

    def test_create_view_rejected(self):
        """CREATE VIEW queries should be rejected"""
        query = "CREATE VIEW test_view AS SELECT * FROM wikipedia"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Create"):
            validate_query_is_read_only(query)

    def test_grant_query_rejected(self):
        """GRANT queries should be rejected"""
        query = "GRANT SELECT ON wikipedia TO user"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Grant"):
            validate_query_is_read_only(query)

    def test_revoke_query_rejected(self):
        """REVOKE queries should be rejected"""
        query = "REVOKE SELECT ON wikipedia FROM user"
        with pytest.raises(ValueError, match=r"Only SELECT queries are allowed.*Revoke"):
            validate_query_is_read_only(query)
