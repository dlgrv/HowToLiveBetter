package testutil

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/guest"
	_ "github.com/dlgrv/HowToLiveBetter/api/internal/migrations"
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	_ "github.com/pocketbase/pocketbase/migrations"
	"github.com/pocketbase/pocketbase/tools/types"
)

// NewApp boots an empty PocketBase app with HTLB migrations applied.
func NewApp(t *testing.T) core.App {
	t.Helper()
	dir := t.TempDir()
	app := core.NewBaseApp(core.BaseAppConfig{
		DataDir:       dir,
		EncryptionEnv: "htlb_test_encryption",
	})
	// 32+ chars secret for encryption env if used
	_ = os.Setenv("htlb_test_encryption", "0123456789abcdef0123456789abcdef")
	if err := app.Bootstrap(); err != nil {
		t.Fatalf("bootstrap: %v", err)
	}
	if err := app.RunAllMigrations(); err != nil {
		t.Fatalf("migrations: %v", err)
	}
	t.Cleanup(func() {
		_ = app.ResetBootstrapState()
		_ = os.RemoveAll(dir)
	})
	return app
}

// MakeGuest creates an active guest session and returns raw token + owner.
func MakeGuest(t *testing.T, app core.App) (token string, owner authz.Owner) {
	t.Helper()
	svc := guest.Service{App: app, GuestTTL: 24 * time.Hour, ClaimTTL: 10 * time.Minute}
	tok, _, err := svc.CreateSession()
	if err != nil {
		t.Fatalf("guest session: %v", err)
	}
	hash := authz.HashToken(tok)
	rec, err := app.FindFirstRecordByFilter("guest_sessions", "tokenHash = {:h}", dbx.Params{"h": hash})
	if err != nil {
		t.Fatalf("find guest: %v", err)
	}
	return tok, authz.Owner{Kind: authz.KindGuest, ID: rec.Id}
}

// MakeUser creates a users auth record (password path for tests only).
func MakeUser(t *testing.T, app core.App, email string) *core.Record {
	t.Helper()
	col, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		t.Fatalf("users: %v", err)
	}
	// Temporarily allow password for seed
	col.PasswordAuth.Enabled = true
	col.PasswordAuth.IdentityFields = []string{"email"}
	if err := app.Save(col); err != nil {
		t.Fatalf("enable password: %v", err)
	}
	rec := core.NewRecord(col)
	rec.SetEmail(email)
	rec.SetPassword("test-password-long")
	rec.SetVerified(true)
	if err := app.Save(rec); err != nil {
		t.Fatalf("save user: %v", err)
	}
	col.PasswordAuth.Enabled = false
	_ = app.Save(col)
	return rec
}

// ExpireGuest sets expiresAt in the past.
func ExpireGuest(t *testing.T, app core.App, guestID string) {
	t.Helper()
	rec, err := app.FindRecordById("guest_sessions", guestID)
	if err != nil {
		t.Fatal(err)
	}
	dt, _ := types.ParseDateTime(time.Now().Add(-time.Hour))
	rec.Set("expiresAt", dt)
	if err := app.Save(rec); err != nil {
		t.Fatal(err)
	}
}

// DataDir returns the app data directory path for smoke tests.
func DataDir(app core.App) string {
	return filepath.Clean(app.DataDir())
}
