package migrations

import (
	"strings"

	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/dbutils"
)

func init() {
	core.AppMigrations.Register(upUsefulVoterIndex, downUsefulVoterIndex, "1760000002_useful_voter_index.go")
}

func upUsefulVoterIndex(app core.App) error {
	col, err := app.FindCollectionByNameOrId("useful_votes")
	if err != nil {
		return err
	}
	for _, idx := range col.Indexes {
		if strings.EqualFold(dbutils.ParseIndex(idx).IndexName, "idx_useful_votes_voter") {
			return nil
		}
	}
	col.AddIndex("idx_useful_votes_voter", false, "voterKey", "")
	return app.Save(col)
}

func downUsefulVoterIndex(app core.App) error {
	col, err := app.FindCollectionByNameOrId("useful_votes")
	if err != nil {
		return err
	}
	col.RemoveIndex("idx_useful_votes_voter")
	return app.Save(col)
}
