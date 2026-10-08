package library_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
)

func TestBookmarksIsolation(t *testing.T) {
	app := testutil.NewApp(t)
	_, a := testutil.MakeGuest(t, app)
	_, b := testutil.MakeGuest(t, app)
	svc := library.Service{App: app}
	if err := svc.UpsertBookmark(a, "e1", "note"); err != nil {
		t.Fatal(err)
	}
	items, err := svc.ListBookmarks(b)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 0 {
		t.Fatalf("leak: %+v", items)
	}
	items, err = svc.ListBookmarks(a)
	if err != nil || len(items) != 1 || items[0].EntryID != "e1" {
		t.Fatalf("%v %+v", err, items)
	}
}

func TestReadingUpsert(t *testing.T) {
	app := testutil.NewApp(t)
	_, o := testutil.MakeGuest(t, app)
	svc := library.Service{App: app}
	if err := svc.PutReading(o, "02", 0.5); err != nil {
		t.Fatal(err)
	}
	r, err := svc.GetReading(o)
	if err != nil || r.Chapter != "02" || r.Offset != 0.5 {
		t.Fatalf("%v %+v", err, r)
	}
}
