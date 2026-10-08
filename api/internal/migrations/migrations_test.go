package migrations_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
)

func TestCollectionsLocked(t *testing.T) {
	app := testutil.NewApp(t)
	for _, name := range []string{
		"guest_sessions", "guest_claims", "useful_votes", "bookmarks", "reading_positions", "users",
	} {
		col, err := app.FindCollectionByNameOrId(name)
		if err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		if col.ListRule != nil || col.CreateRule != nil || col.UpdateRule != nil || col.DeleteRule != nil || col.ViewRule != nil {
			t.Fatalf("%s rules not fully locked", name)
		}
	}
	users, _ := app.FindCollectionByNameOrId("users")
	if users.PasswordAuth.Enabled {
		t.Fatal("password auth should be disabled")
	}
}

func TestReApplyMigrations(t *testing.T) {
	app := testutil.NewApp(t)
	if err := app.RunAllMigrations(); err != nil {
		t.Fatal(err)
	}
}
