package useful

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"

	"github.com/pocketbase/dbx"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
)

type Service struct {
	App  core.App
	Salt string
}

type VoteResult struct {
	EntryID string `json:"entryId"`
	Useful  bool   `json:"useful"`
	Count   int    `json:"count"`
}

// VoterKey is the salted hash used as the unique voter identity per entry.
func VoterKey(owner authz.Owner, salt string) string {
	raw := string(owner.Kind) + ":" + owner.ID + ":" + salt
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}

func (s Service) Count(entryID string) (int, error) {
	records, err := s.App.FindRecordsByFilter("useful_votes",
		"entryId = {:e} && useful = true", "", 0, 0,
		dbx.Params{"e": entryID},
	)
	if err != nil {
		return 0, err
	}
	return len(records), nil
}

func (s Service) Get(owner authz.Owner, entryID string) (VoteResult, error) {
	vk := VoterKey(owner, s.Salt)
	rec, err := s.App.FindFirstRecordByFilter(
		"useful_votes",
		"entryId = {:e} && voterKey = {:v}",
		dbx.Params{"e": entryID, "v": vk},
	)
	useful := false
	if err == nil {
		useful = rec.GetBool("useful")
	}
	n, err := s.Count(entryID)
	if err != nil {
		return VoteResult{}, err
	}
	return VoteResult{EntryID: entryID, Useful: useful, Count: n}, nil
}

func (s Service) Toggle(owner authz.Owner, entryID string, useful bool) (VoteResult, error) {
	entryID = strings.TrimSpace(entryID)
	if entryID == "" {
		return VoteResult{}, fmt.Errorf("entryId required")
	}
	vk := VoterKey(owner, s.Salt)
	col, err := s.App.FindCollectionByNameOrId("useful_votes")
	if err != nil {
		return VoteResult{}, err
	}
	err = s.App.RunInTransaction(func(txApp core.App) error {
		return upsertVote(txApp, col, owner, entryID, vk, useful)
	})
	if err != nil {
		// Concurrent first-insert: unique (entryId,voterKey) — retry as update.
		if !isUniqueConflict(err) {
			return VoteResult{}, err
		}
		err = s.App.RunInTransaction(func(txApp core.App) error {
			return upsertVote(txApp, col, owner, entryID, vk, useful)
		})
		if err != nil {
			return VoteResult{}, err
		}
	}
	return s.Get(owner, entryID)
}

func upsertVote(txApp core.App, col *core.Collection, owner authz.Owner, entryID, vk string, useful bool) error {
	rec, err := txApp.FindFirstRecordByFilter(
		"useful_votes",
		"entryId = {:e} && voterKey = {:v}",
		dbx.Params{"e": entryID, "v": vk},
	)
	if err != nil {
		rec = core.NewRecord(col)
		rec.Set("entryId", entryID)
		rec.Set("voterKey", vk)
		rec.Set("ownerKind", string(owner.Kind))
		rec.Set("ownerId", owner.ID)
	} else if rec.GetBool("useful") == useful {
		return nil // already at desired state — no write, count unchanged
	}
	rec.Set("useful", useful)
	return txApp.Save(rec)
}

func isUniqueConflict(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "unique constraint") ||
		strings.Contains(msg, "constraint failed")
}

func (s Service) Counts(entryIDs []string) (map[string]int, error) {
	out := make(map[string]int, len(entryIDs))
	for _, id := range entryIDs {
		n, err := s.Count(id)
		if err != nil {
			return nil, err
		}
		out[id] = n
	}
	return out, nil
}

// ListMine returns entryIds the owner marked useful=true, sorted by entryId.
func (s Service) ListMine(owner authz.Owner) ([]string, error) {
	vk := VoterKey(owner, s.Salt)
	records, err := s.App.FindRecordsByFilter(
		"useful_votes",
		"voterKey = {:v} && useful = true",
		"entryId",
		0, 0,
		dbx.Params{"v": vk},
	)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(records))
	for _, rec := range records {
		id := strings.TrimSpace(rec.GetString("entryId"))
		if id != "" {
			out = append(out, id)
		}
	}
	return out, nil
}
