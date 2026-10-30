package common

import (
	"runtime"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseRedisOptionUsesCPUScaledPoolByDefault(t *testing.T) {
	t.Setenv("REDIS_CONN_STRING", "redis://localhost:6379/0")
	t.Setenv("REDIS_POOL_SIZE", "")
	t.Setenv("REDIS_MIN_IDLE_CONNS", "")

	options := ParseRedisOption()

	require.Equal(t, 10*runtime.GOMAXPROCS(0), options.PoolSize)
	require.Zero(t, options.MinIdleConns)
}

func TestParseRedisOptionUsesConfiguredPool(t *testing.T) {
	t.Setenv("REDIS_CONN_STRING", "redis://localhost:6379/0?pool_size=24&min_idle_conns=6")
	t.Setenv("REDIS_POOL_SIZE", "64")
	t.Setenv("REDIS_MIN_IDLE_CONNS", "16")

	options := ParseRedisOption()

	require.Equal(t, 64, options.PoolSize)
	require.Equal(t, 16, options.MinIdleConns)
}

func TestParseRedisOptionKeepsURLPoolSettingsForInvalidEnvironment(t *testing.T) {
	t.Setenv("REDIS_CONN_STRING", "redis://localhost:6379/0?pool_size=24&min_idle_conns=6")
	t.Setenv("REDIS_POOL_SIZE", "invalid")
	t.Setenv("REDIS_MIN_IDLE_CONNS", "-1")

	options := ParseRedisOption()

	require.Equal(t, 24, options.PoolSize)
	require.Equal(t, 6, options.MinIdleConns)
}

func TestParseRedisOptionPreservesURLPoolSettings(t *testing.T) {
	t.Setenv("REDIS_CONN_STRING", "redis://localhost:6379/0?pool_size=24&min_idle_conns=6")
	t.Setenv("REDIS_POOL_SIZE", "")
	t.Setenv("REDIS_MIN_IDLE_CONNS", "")

	options := ParseRedisOption()

	require.Equal(t, 24, options.PoolSize)
	require.Equal(t, 6, options.MinIdleConns)
}

func TestParseRedisOptionClampsMinIdleConnections(t *testing.T) {
	t.Setenv("REDIS_CONN_STRING", "redis://localhost:6379/0")
	t.Setenv("REDIS_POOL_SIZE", "32")
	t.Setenv("REDIS_MIN_IDLE_CONNS", "64")

	options := ParseRedisOption()

	require.Equal(t, 32, options.PoolSize)
	require.Equal(t, 32, options.MinIdleConns)
}
