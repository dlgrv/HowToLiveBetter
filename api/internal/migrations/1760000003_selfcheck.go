package migrations

import (
	"github.com/pocketbase/pocketbase/core"
)

func init() {
	core.AppMigrations.Register(upSelfcheck, downSelfcheck, "1760000003_selfcheck.go")
}

func upSelfcheck(app core.App) error {
	c := core.NewBaseCollection("selfcheck_answers")
	denyAll(c)
	c.Fields.Add(
		&core.SelectField{
			Name: "ownerKind", Required: true, MaxSelect: 1,
			Values: []string{"guest", "user"},
		},
		&core.TextField{Name: "ownerId", Required: true, Max: 50},
		// JSON object {"<entryId>": 0|1}; TextField keeps Get/Set predictable.
		&core.TextField{Name: "answers", Required: true, Max: 200_000},
	)
	c.AddIndex("idx_selfcheck_owner", true, "ownerKind, ownerId", "")
	return app.Save(c)
}

func downSelfcheck(app core.App) error {
	col, err := app.FindCollectionByNameOrId("selfcheck_answers")
	if err != nil {
		return nil
	}
	return app.Delete(col)
}
