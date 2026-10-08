package library

import (
	"fmt"
	"strings"

	"github.com/pocketbase/dbx"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/pocketbase/pocketbase/core"
)

type Service struct {
	App core.App
}

type Bookmark struct {
	EntryID string `json:"entryId"`
	Note    string `json:"note,omitempty"`
}

type Reading struct {
	Chapter string  `json:"chapter"`
	Offset  float64 `json:"offset"`
}

func ownerFilter(owner authz.Owner) (string, dbx.Params) {
	return "ownerKind = {:k} && ownerId = {:i}", dbx.Params{
		"k": string(owner.Kind),
		"i": owner.ID,
	}
}

func (s Service) ListBookmarks(owner authz.Owner) ([]Bookmark, error) {
	f, p := ownerFilter(owner)
	recs, err := s.App.FindRecordsByFilter("bookmarks", f, "", 0, 0, p)
	if err != nil {
		return nil, err
	}
	out := make([]Bookmark, 0, len(recs))
	for _, r := range recs {
		out = append(out, Bookmark{
			EntryID: r.GetString("entryId"),
			Note:    r.GetString("note"),
		})
	}
	return out, nil
}

func (s Service) UpsertBookmark(owner authz.Owner, entryID, note string) error {
	entryID = strings.TrimSpace(entryID)
	if entryID == "" {
		return fmt.Errorf("entryId required")
	}
	col, err := s.App.FindCollectionByNameOrId("bookmarks")
	if err != nil {
		return err
	}
	f, p := ownerFilter(owner)
	p["e"] = entryID
	rec, err := s.App.FindFirstRecordByFilter("bookmarks", f+" && entryId = {:e}", p)
	if err != nil {
		rec = core.NewRecord(col)
		rec.Set("ownerKind", string(owner.Kind))
		rec.Set("ownerId", owner.ID)
		rec.Set("entryId", entryID)
	}
	rec.Set("note", note)
	return s.App.Save(rec)
}

func (s Service) DeleteBookmark(owner authz.Owner, entryID string) error {
	f, p := ownerFilter(owner)
	p["e"] = entryID
	rec, err := s.App.FindFirstRecordByFilter("bookmarks", f+" && entryId = {:e}", p)
	if err != nil {
		return nil
	}
	return s.App.Delete(rec)
}

func (s Service) GetReading(owner authz.Owner) (Reading, error) {
	f, p := ownerFilter(owner)
	rec, err := s.App.FindFirstRecordByFilter("reading_positions", f, p)
	if err != nil {
		return Reading{}, nil
	}
	return Reading{
		Chapter: rec.GetString("chapter"),
		Offset:  rec.GetFloat("offset"),
	}, nil
}

func (s Service) PutReading(owner authz.Owner, chapter string, offset float64) error {
	chapter = strings.TrimSpace(chapter)
	if chapter == "" {
		return fmt.Errorf("chapter required")
	}
	col, err := s.App.FindCollectionByNameOrId("reading_positions")
	if err != nil {
		return err
	}
	f, p := ownerFilter(owner)
	rec, err := s.App.FindFirstRecordByFilter("reading_positions", f, p)
	if err != nil {
		rec = core.NewRecord(col)
		rec.Set("ownerKind", string(owner.Kind))
		rec.Set("ownerId", owner.ID)
	}
	rec.Set("chapter", chapter)
	rec.Set("offset", offset)
	return s.App.Save(rec)
}

// ExportForMerge returns guest data for merge into a user.
func (s Service) ExportForMerge(owner authz.Owner) (bookmarks []Bookmark, reading Reading, err error) {
	bookmarks, err = s.ListBookmarks(owner)
	if err != nil {
		return nil, Reading{}, err
	}
	reading, err = s.GetReading(owner)
	return bookmarks, reading, err
}
