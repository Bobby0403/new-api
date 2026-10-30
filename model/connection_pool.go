package model

import (
	"database/sql"
	"time"

	"github.com/QuantumNous/new-api/common"
)

const (
	defaultSQLMaxIdleConns = 20
	defaultSQLMaxOpenConns = 50
	defaultSQLMaxLifetime  = 10 * time.Minute
	defaultSQLMaxIdleTime  = 5 * time.Minute
)

type sqlConnectionPoolConfig struct {
	maxIdleConns    int
	maxOpenConns    int
	connMaxLifetime time.Duration
	connMaxIdleTime time.Duration
}

func loadSQLConnectionPoolConfig() sqlConnectionPoolConfig {
	return loadSQLConnectionPoolConfigFromEnv("SQL", sqlConnectionPoolConfig{
		maxIdleConns:    defaultSQLMaxIdleConns,
		maxOpenConns:    defaultSQLMaxOpenConns,
		connMaxLifetime: defaultSQLMaxLifetime,
		connMaxIdleTime: defaultSQLMaxIdleTime,
	})
}

func loadLogSQLConnectionPoolConfig() sqlConnectionPoolConfig {
	return loadSQLConnectionPoolConfigFromEnv("LOG_SQL", loadSQLConnectionPoolConfig())
}

func loadSQLConnectionPoolConfigFromEnv(prefix string, defaults sqlConnectionPoolConfig) sqlConnectionPoolConfig {
	maxOpenConns := positiveEnvOrDefault(prefix+"_MAX_OPEN_CONNS", defaults.maxOpenConns)
	maxIdleConns := positiveEnvOrDefault(prefix+"_MAX_IDLE_CONNS", defaults.maxIdleConns)
	if maxOpenConns > 0 && maxIdleConns > maxOpenConns {
		maxIdleConns = maxOpenConns
	}
	maxLifetimeSeconds := positiveEnvOrDefault(prefix+"_MAX_LIFETIME", int(defaults.connMaxLifetime/time.Second))
	maxIdleTimeSeconds := positiveEnvOrDefault(prefix+"_MAX_IDLE_TIME", int(defaults.connMaxIdleTime/time.Second))

	return sqlConnectionPoolConfig{
		maxIdleConns:    maxIdleConns,
		maxOpenConns:    maxOpenConns,
		connMaxLifetime: time.Duration(maxLifetimeSeconds) * time.Second,
		connMaxIdleTime: time.Duration(maxIdleTimeSeconds) * time.Second,
	}
}

func positiveEnvOrDefault(name string, defaultValue int) int {
	value := common.GetEnvOrDefault(name, defaultValue)
	if value > 0 {
		return value
	}
	common.SysError(common.LogText("%s must be positive, using default value: %d", name, defaultValue))
	return defaultValue
}

func configureSQLConnectionPool(sqlDB *sql.DB, name string, config sqlConnectionPoolConfig) {
	sqlDB.SetMaxOpenConns(config.maxOpenConns)
	sqlDB.SetMaxIdleConns(config.maxIdleConns)
	sqlDB.SetConnMaxLifetime(config.connMaxLifetime)
	sqlDB.SetConnMaxIdleTime(config.connMaxIdleTime)
	common.SysLog(common.LogText("%s database pool configured: max_open=%d max_idle=%d max_lifetime=%s max_idle_time=%s", name, config.maxOpenConns, config.maxIdleConns, config.connMaxLifetime, config.connMaxIdleTime))
}
