package merge

import (
	"fmt"

	"github.com/pocketbase/dbx"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/pocketbase/pocketbase/core"
)

type Service struct {
	App     core.App
	Library library.Service
}

type Result struct {
	BookmarksMerged int  `json:"bookmarksMerged"`
	ReadingMerged   bool `json:"readingMerged"`
}

func (s Service) MergeGuestIntoUser(guestID, userID string) (Result, error) {
	var res Result
	err := s.App.RunInTransaction(func(txApp core.App) error {
		guest, err := txApp.FindRecordById("guest_sessions", guestID)
		if err != nil {
			return fmt.Errorf("guest not found")
		}
		if guest.GetString("status") != "active" {
			return fmt.Errorf("guest already merged or revoked")
		}
		lib := library.Service{App: txApp}
		gOwner := authz.Owner{Kind: authz.KindGuest, ID: guestID}
		uOwner := authz.Owner{Kind: authz.KindUser, ID: userID}

		bms, reading, err := lib.ExportForMerge(gOwner)
		if err != nil {
			return err
		}
		for _, bm := range bms {
			if err := lib.UpsertBookmark(uOwner, bm.EntryID, bm.Note); err != nil {
				return err
			}
			res.BookmarksMerged++
		}
		if reading.Chapter != "" {
			if err := lib.PutReading(uOwner, reading.Chapter, reading.Offset); err != nil {
				return err
			}
			res.ReadingMerged = true
		}

		// Re-home useful votes voterKeys stay salted; also copy owner fields for audit
		votes, err := txApp.FindRecordsByFilter("useful_votes",
			"ownerKind = 'guest' && ownerId = {:i}", "", 0, 0,
			dbx.Params{"i": guestID},
		)
		if err != nil {
			return err
		}
		for _, v := range votes {
			v.Set("ownerKind", "user")
			v.Set("ownerId", userID)
			if err := txApp.Save(v); err != nil {
				return err
			}
		}

		guest.Set("status", "merged")
		guest.Set("mergedToUserId", userID)
		return txApp.Save(guest)
	})
	return res, err
}
