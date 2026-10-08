package migrations

import (
	"github.com/pocketbase/pocketbase/core"
)

func init() {
	core.AppMigrations.Register(upHTLBCollections, downHTLBCollections, "1760000001_htlb_collections.go")
}

func denyAll(c *core.Collection) {
	c.ListRule = nil
	c.ViewRule = nil
	c.CreateRule = nil
	c.UpdateRule = nil
	c.DeleteRule = nil
}

func upHTLBCollections(app core.App) error {
	if err := createGuestSessions(app); err != nil {
		return err
	}
	if err := createGuestClaims(app); err != nil {
		return err
	}
	if err := createUsefulVotes(app); err != nil {
		return err
	}
	if err := createBookmarks(app); err != nil {
		return err
	}
	if err := createReadingPositions(app); err != nil {
		return err
	}
	return lockUsers(app)
}

func downHTLBCollections(app core.App) error {
	for _, name := range []string{
		"reading_positions", "bookmarks", "useful_votes", "guest_claims", "guest_sessions",
	} {
		col, err := app.FindCollectionByNameOrId(name)
		if err != nil {
			continue
		}
		if err := app.Delete(col); err != nil {
			return err
		}
	}
	return nil
}

func createGuestSessions(app core.App) error {
	c := core.NewBaseCollection("guest_sessions")
	denyAll(c)
	c.Fields.Add(
		&core.TextField{Name: "tokenHash", Required: true, Max: 128},
		&core.SelectField{
			Name: "status", Required: true, MaxSelect: 1,
			Values: []string{"active", "merged", "revoked"},
		},
		&core.DateField{Name: "expiresAt", Required: true},
		&core.TextField{Name: "mergedToUserId", Max: 50},
	)
	c.AddIndex("idx_guest_sessions_tokenHash", true, "tokenHash", "")
	return app.Save(c)
}

func createGuestClaims(app core.App) error {
	c := core.NewBaseCollection("guest_claims")
	denyAll(c)
	c.Fields.Add(
		&core.TextField{Name: "codeHash", Required: true, Max: 128},
		&core.TextField{Name: "guestId", Required: true, Max: 50},
		&core.SelectField{
			Name: "status", Required: true, MaxSelect: 1,
			Values: []string{"pending", "used"},
		},
		&core.DateField{Name: "expiresAt", Required: true},
	)
	c.AddIndex("idx_guest_claims_codeHash", true, "codeHash", "")
	return app.Save(c)
}

func createUsefulVotes(app core.App) error {
	c := core.NewBaseCollection("useful_votes")
	denyAll(c)
	c.Fields.Add(
		&core.TextField{Name: "entryId", Required: true, Max: 120},
		&core.TextField{Name: "voterKey", Required: true, Max: 128},
		&core.BoolField{Name: "useful"},
		&core.SelectField{
			Name: "ownerKind", Required: true, MaxSelect: 1,
			Values: []string{"guest", "user"},
		},
		&core.TextField{Name: "ownerId", Required: true, Max: 50},
	)
	c.AddIndex("idx_useful_votes_entry_voter", true, "entryId, voterKey", "")
	c.AddIndex("idx_useful_votes_entry", false, "entryId", "")
	return app.Save(c)
}

func createBookmarks(app core.App) error {
	c := core.NewBaseCollection("bookmarks")
	denyAll(c)
	c.Fields.Add(
		&core.SelectField{
			Name: "ownerKind", Required: true, MaxSelect: 1,
			Values: []string{"guest", "user"},
		},
		&core.TextField{Name: "ownerId", Required: true, Max: 50},
		&core.TextField{Name: "entryId", Required: true, Max: 120},
		&core.TextField{Name: "note", Max: 500},
	)
	c.AddIndex("idx_bookmarks_owner_entry", true, "ownerKind, ownerId, entryId", "")
	return app.Save(c)
}

func createReadingPositions(app core.App) error {
	c := core.NewBaseCollection("reading_positions")
	denyAll(c)
	c.Fields.Add(
		&core.SelectField{
			Name: "ownerKind", Required: true, MaxSelect: 1,
			Values: []string{"guest", "user"},
		},
		&core.TextField{Name: "ownerId", Required: true, Max: 50},
		&core.TextField{Name: "chapter", Required: true, Max: 80},
		&core.NumberField{Name: "offset"},
	)
	c.AddIndex("idx_reading_owner", true, "ownerKind, ownerId", "")
	return app.Save(c)
}

func lockUsers(app core.App) error {
	users, err := app.FindCollectionByNameOrId("users")
	if err != nil {
		return err
	}
	denyAll(users)
	users.PasswordAuth.Enabled = false
	// OAuth providers are enabled at runtime when client credentials exist.
	users.OAuth2.Enabled = false
	users.OAuth2.Providers = []core.OAuth2ProviderConfig{
		{Name: "google"},
		{Name: "github"},
	}
	users.ManageRule = nil
	return app.Save(users)
}
