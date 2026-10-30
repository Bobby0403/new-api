package model

import (
	"testing"
	"time"

	"github.com/glebarez/sqlite"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

func TestLoadSQLConnectionPoolConfigDefaults(t *testing.T) {
	t.Setenv("SQL_MAX_IDLE_CONNS", "")
	t.Setenv("SQL_MAX_OPEN_CONNS", "")
	t.Setenv("SQL_MAX_LIFETIME", "")
	t.Setenv("SQL_MAX_IDLE_TIME", "")

	config := loadSQLConnectionPoolConfig()

	require.Equal(t, 20, config.maxIdleConns)
	require.Equal(t, 50, config.maxOpenConns)
	require.Equal(t, 10*time.Minute, config.connMaxLifetime)
	require.Equal(t, 5*time.Minute, config.connMaxIdleTime)
}

func TestLoadSQLConnectionPoolConfigRejectsUnboundedValues(t *testing.T) {
	t.Setenv("SQL_MAX_IDLE_CONNS", "0")
	t.Setenv("SQL_MAX_OPEN_CONNS", "-1")
	t.Setenv("SQL_MAX_LIFETIME", "0")
	t.Setenv("SQL_MAX_IDLE_TIME", "-1")

	config := loadSQLConnectionPoolConfig()

	require.Equal(t, 20, config.maxIdleConns)
	require.Equal(t, 50, config.maxOpenConns)
	require.Equal(t, 10*time.Minute, config.connMaxLifetime)
	require.Equal(t, 5*time.Minute, config.connMaxIdleTime)
}

func TestLoadLogSQLConnectionPoolConfigUsesIndependentOverrides(t *testing.T) {
	t.Setenv("SQL_MAX_IDLE_CONNS", "20")
	t.Setenv("SQL_MAX_OPEN_CONNS", "50")
	t.Setenv("LOG_SQL_MAX_IDLE_CONNS", "8")
	t.Setenv("LOG_SQL_MAX_OPEN_CONNS", "20")
	t.Setenv("LOG_SQL_MAX_LIFETIME", "300")
	t.Setenv("LOG_SQL_MAX_IDLE_TIME", "120")

	config := loadLogSQLConnectionPoolConfig()

	require.Equal(t, 8, config.maxIdleConns)
	require.Equal(t, 20, config.maxOpenConns)
	require.Equal(t, 5*time.Minute, config.connMaxLifetime)
	require.Equal(t, 2*time.Minute, config.connMaxIdleTime)
}

func TestConfigureSQLConnectionPoolAppliesOpenLimit(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	require.NoError(t, err)
	sqlDB, err := db.DB()
	require.NoError(t, err)
	t.Cleanup(func() { _ = sqlDB.Close() })

	config := loadSQLConnectionPoolConfig()
	configureSQLConnectionPool(sqlDB, "test", config)

	require.Equal(t, 50, sqlDB.Stats().MaxOpenConnections)
}

func TestLoadSQLConnectionPoolConfigUsesEnvironment(t *testing.T) {
	t.Setenv("SQL_MAX_IDLE_CONNS", "16")
	t.Setenv("SQL_MAX_OPEN_CONNS", "64")
	t.Setenv("SQL_MAX_LIFETIME", "900")
	t.Setenv("SQL_MAX_IDLE_TIME", "240")

	config := loadSQLConnectionPoolConfig()

	require.Equal(t, 16, config.maxIdleConns)
	require.Equal(t, 64, config.maxOpenConns)
	require.Equal(t, 15*time.Minute, config.connMaxLifetime)
	require.Equal(t, 4*time.Minute, config.connMaxIdleTime)
}

func TestLoadSQLConnectionPoolConfigClampsIdleConnections(t *testing.T) {
	t.Setenv("SQL_MAX_IDLE_CONNS", "80")
	t.Setenv("SQL_MAX_OPEN_CONNS", "40")

	config := loadSQLConnectionPoolConfig()

	require.Equal(t, 40, config.maxIdleConns)
	require.Equal(t, 40, config.maxOpenConns)
}
