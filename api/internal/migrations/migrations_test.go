package migrations_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
)

func TestCollectionsLocked(t *testing.T) {
	app := testutil.NewApp(t)
	for _, name := range []string{
		"guest_sessions", "guest_claims", "useful_votes", "bookmarks", "reading_positions",
	} {
		col, err := app.FindCollectionByNameOrId(name)
		if err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		if col.ListRule != nil || col.CreateRule != nil || col.UpdateRule != nil || col.DeleteRule != nil || col.ViewRule != nil {
			t.Fatalf("%s rules not fully locked", name)
		}
	}
	users, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		t.Fatal(err)
	}
	if users.PasswordAuth.Enabled {
		t.Fatal("password auth should be disabled")
	}
	if users.ListRule != nil || users.ViewRule != nil || users.UpdateRule != nil || users.DeleteRule != nil || users.ManageRule != nil {
		t.Fatal("users non-create rules should be locked")
	}
	want := `@request.context = "oauth2"`
	if users.CreateRule == nil || *users.CreateRule != want {
		t.Fatalf("users CreateRule want %q, got %#v", want, users.CreateRule)
	}
}

func TestReApplyMigrations(t *testing.T) {
	app := testutil.NewApp(t)
	if err := app.RunAllMigrations(); err != nil {
		t.Fatal(err)
	}
}
