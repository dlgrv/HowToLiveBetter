package main

import (
	"log"
	"os"

	internalapp "github.com/dlgrv/HowToLiveBetter/api/internal/app"
	"github.com/dlgrv/HowToLiveBetter/api/internal/config"
	_ "github.com/dlgrv/HowToLiveBetter/api/internal/migrations"
	"github.com/pocketbase/pocketbase"
	_ "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"
)

// Version is overridden via -ldflags at release build time.
var Version = "dev"

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatal(err)
	}
	if cfg.Version == "dev" && Version != "dev" {
		cfg.Version = Version
	}

	pbCfg := pocketbase.Config{
		DefaultDev: os.Getenv("HTLB_DEV") == "1",
	}
	if cfg.DataDir != "" {
		pbCfg.DefaultDataDir = cfg.DataDir
	}
	if enc := os.Getenv("HTLB_ENCRYPTION_ENV"); enc != "" {
		pbCfg.DefaultEncryptionEnv = enc
	}

	app := pocketbase.NewWithConfig(pbCfg)

	migrateDir := cfg.MigrationsDir
	if migrateDir == "" {
		migrateDir = "internal/migrations"
	}
	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: false,
		Dir:         migrateDir,
	})

	internalapp.Bind(app, cfg)

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
