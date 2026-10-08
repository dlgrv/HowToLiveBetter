package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	CORSOrigins   []string
	GuestTTL      time.Duration
	ClaimTTL      time.Duration
	VoteSalt      string
	Listen        string
	DataDir       string
	MigrationsDir string
	Version       string
}

func Load() (Config, error) {
	cfg := Config{
		CORSOrigins:   splitCSV(env("HTLB_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")),
		GuestTTL:      hoursEnv("HTLB_GUEST_TTL_HOURS", 90*24),
		ClaimTTL:      minutesEnv("HTLB_CLAIM_TTL_MINUTES", 10),
		VoteSalt:      env("HTLB_VOTE_SALT", "dev-only-change-me"),
		Listen:        env("HTLB_LISTEN", "127.0.0.1:8090"),
		DataDir:       env("HTLB_DATA_DIR", ""),
		MigrationsDir: env("HTLB_MIGRATIONS_DIR", ""),
		Version:       env("HTLB_VERSION", "dev"),
	}
	if cfg.VoteSalt == "" {
		return cfg, fmt.Errorf("HTLB_VOTE_SALT is required")
	}
	if len(cfg.CORSOrigins) == 0 {
		return cfg, fmt.Errorf("HTLB_CORS_ORIGINS is required")
	}
	return cfg, nil
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func splitCSV(s string) []string {
	var out []string
	for _, p := range strings.Split(s, ",") {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

func hoursEnv(k string, defHours int) time.Duration {
	v := os.Getenv(k)
	if v == "" {
		return time.Duration(defHours) * time.Hour
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return time.Duration(defHours) * time.Hour
	}
	return time.Duration(n) * time.Hour
}

func minutesEnv(k string, defMin int) time.Duration {
	v := os.Getenv(k)
	if v == "" {
		return time.Duration(defMin) * time.Minute
	}
	n, err := strconv.Atoi(v)
	if err != nil || n <= 0 {
		return time.Duration(defMin) * time.Minute
	}
	return time.Duration(n) * time.Minute
}
