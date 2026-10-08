package config_test

import (
	"os"
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/config"
)

func TestLoadDefaults(t *testing.T) {
	os.Unsetenv("HTLB_CORS_ORIGINS")
	os.Unsetenv("HTLB_VOTE_SALT")
	cfg, err := config.Load()
	if err != nil {
		t.Fatal(err)
	}
	if len(cfg.CORSOrigins) == 0 || cfg.VoteSalt == "" {
		t.Fatalf("%+v", cfg)
	}
}
