package merge

import (
	"fmt"

	"github.com/pocketbase/dbx"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
	"github.com/pocketbase/pocketbase/core"
)

type Service struct {
	App     core.App
	Library library.Service
	Salt    string
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

		// Re-home useful votes: rehash voterKey to the user identity and collapse
		// duplicates so guest+user votes on the same entry do not double-count.
		votes, err := txApp.FindRecordsByFilter("useful_votes",
			"ownerKind = 'guest' && ownerId = {:i}", "", 0, 0,
			dbx.Params{"i": guestID},
		)
		if err != nil {
			return err
		}
		newVK := useful.VoterKey(uOwner, s.Salt)
		for _, v := range votes {
			entryID := v.GetString("entryId")
			existing, findErr := txApp.FindFirstRecordByFilter(
				"useful_votes",
				"entryId = {:e} && voterKey = {:v}",
				dbx.Params{"e": entryID, "v": newVK},
			)
			if findErr == nil && existing.Id != v.Id {
				if v.GetBool("useful") || existing.GetBool("useful") {
					existing.Set("useful", true)
					if err := txApp.Save(existing); err != nil {
						return err
					}
				}
				if err := txApp.Delete(v); err != nil {
					return err
				}
				continue
			}
			v.Set("ownerKind", "user")
			v.Set("ownerId", userID)
			v.Set("voterKey", newVK)
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
