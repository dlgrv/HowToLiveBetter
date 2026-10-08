package merge_test

import (
	"testing"

	"github.com/dlgrv/HowToLiveBetter/api/internal/authz"
	"github.com/dlgrv/HowToLiveBetter/api/internal/library"
	"github.com/dlgrv/HowToLiveBetter/api/internal/merge"
	"github.com/dlgrv/HowToLiveBetter/api/internal/testutil"
	"github.com/dlgrv/HowToLiveBetter/api/internal/useful"
)

func TestMergeGuestIntoUser(t *testing.T) {
	app := testutil.NewApp(t)
	_, gOwner := testutil.MakeGuest(t, app)
	user := testutil.MakeUser(t, app, "merge@example.com")
	lib := library.Service{App: app}
	_ = lib.UpsertBookmark(gOwner, "bm1", "")
	_ = lib.PutReading(gOwner, "03", 0.2)
	uSvc := useful.Service{App: app, Salt: "s"}
	_, _ = uSvc.Toggle(gOwner, "e1", true)

	svc := merge.Service{App: app, Library: lib}
	res, err := svc.MergeGuestIntoUser(gOwner.ID, user.Id)
	if err != nil {
		t.Fatal(err)
	}
	if res.BookmarksMerged != 1 || !res.ReadingMerged {
		t.Fatalf("%+v", res)
	}
	uOwner := authz.Owner{Kind: authz.KindUser, ID: user.Id}
	items, _ := lib.ListBookmarks(uOwner)
	if len(items) != 1 {
		t.Fatalf("bookmarks %+v", items)
	}
	rec, err := app.FindRecordById("guest_sessions", gOwner.ID)
	if err != nil || rec.GetString("status") != "merged" {
		t.Fatalf("status %v %v", err, rec)
	}
	_, err = svc.MergeGuestIntoUser(gOwner.ID, user.Id)
	if err == nil {
		t.Fatal("expected second merge to fail")
	}
}
